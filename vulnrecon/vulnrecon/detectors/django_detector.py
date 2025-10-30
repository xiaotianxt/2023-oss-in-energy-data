"""Django security vulnerability detector."""

import os
import re
from typing import List, Dict, Any

from .base import BaseDetector, Finding, Severity


class DjangoDetector(BaseDetector):
    """Detects Django security vulnerabilities and misconfigurations."""

    def detect(self, target_path: str, dependencies: List[Dict[str, Any]]) -> List[Finding]:
        """Detect Django vulnerabilities."""
        findings = []

        # Check if Django is in dependencies
        has_django = any(
            dep.get("dependency_name", "").lower() == "django"
            for dep in dependencies
        )

        if not has_django:
            return findings

        # Find settings files
        settings_files = self._find_settings_files(target_path)

        for settings_file in settings_files:
            findings.extend(self._check_debug_mode(settings_file))
            findings.extend(self._check_secret_key(settings_file))
            findings.extend(self._check_security_middleware(settings_file))
            findings.extend(self._check_allowed_hosts(settings_file))

        # Scan for SQL injection patterns
        findings.extend(self._scan_sql_injection(target_path))

        return findings

    def _find_settings_files(self, target_path: str) -> List[str]:
        """Find Django settings files."""
        settings_files = []
        patterns = self.config.get("settings_files", ["settings.py"])

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'venv', 'node_modules']]

            for file in files:
                if file == "settings.py" or "settings" in file and file.endswith('.py'):
                    settings_files.append(os.path.join(root, file))

        return settings_files

    def _check_debug_mode(self, settings_file: str) -> List[Finding]:
        """Check for DEBUG=True in settings."""
        findings = []

        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for DEBUG = True
            if re.search(r'DEBUG\s*=\s*True', content, re.IGNORECASE):
                findings.append(Finding(
                    title="Django DEBUG Mode Enabled",
                    severity=Severity.HIGH,
                    description=(
                        "DEBUG mode is enabled in Django settings. This exposes sensitive "
                        "information including stack traces, SQL queries, and environment "
                        "variables to potential attackers."
                    ),
                    file_path=settings_file,
                    remediation="Set DEBUG = False in production environments.",
                    references=[
                        "https://docs.djangoproject.com/en/stable/ref/settings/#debug",
                        "https://owasp.org/www-project-top-ten/2017/A6_2017-Security_Misconfiguration",
                    ],
                    confidence=0.95
                ))

        except Exception as e:
            print(f"Error checking DEBUG mode in {settings_file}: {e}")

        return findings

    def _check_secret_key(self, settings_file: str) -> List[Finding]:
        """Check for hardcoded SECRET_KEY."""
        findings = []

        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if re.search(r'SECRET_KEY\s*=\s*["\']', line):
                        # Check if it's a hardcoded value (not reading from env)
                        if 'os.environ' not in line and 'getenv' not in line and 'env(' not in line:
                            findings.append(Finding(
                                title="Hardcoded Django SECRET_KEY",
                                severity=Severity.CRITICAL,
                                description=(
                                    "Django SECRET_KEY is hardcoded in settings file. This key is used "
                                    "for cryptographic signing and should never be committed to version "
                                    "control. An exposed SECRET_KEY can lead to session hijacking, "
                                    "CSRF token forgery, and other attacks."
                                ),
                                file_path=settings_file,
                                line_number=line_num,
                                code_snippet=line.strip(),
                                remediation=(
                                    "Store SECRET_KEY in environment variables:\n\n"
                                    "import os\n"
                                    "SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')\n\n"
                                    "Or use python-decouple:\n"
                                    "from decouple import config\n"
                                    "SECRET_KEY = config('SECRET_KEY')"
                                ),
                                references=[
                                    "https://docs.djangoproject.com/en/stable/ref/settings/#secret-key",
                                ],
                                confidence=0.9
                            ))

        except Exception as e:
            print(f"Error checking SECRET_KEY in {settings_file}: {e}")

        return findings

    def _check_security_middleware(self, settings_file: str) -> List[Finding]:
        """Check for missing security middleware."""
        findings = []

        required_middleware = [
            'SecurityMiddleware',
            'CsrfViewMiddleware',
            'XFrameOptionsMiddleware',
        ]

        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                content = f.read()

            missing = []
            for middleware in required_middleware:
                if middleware not in content:
                    missing.append(middleware)

            if missing:
                findings.append(Finding(
                    title="Missing Django Security Middleware",
                    severity=Severity.MEDIUM,
                    description=(
                        f"The following security middleware is missing: {', '.join(missing)}. "
                        f"These middleware components provide essential security protections."
                    ),
                    file_path=settings_file,
                    remediation=f"Add missing middleware to MIDDLEWARE setting: {', '.join(missing)}",
                    references=[
                        "https://docs.djangoproject.com/en/stable/ref/middleware/#module-django.middleware.security",
                    ],
                    confidence=0.8,
                    metadata={"missing_middleware": missing}
                ))

        except Exception as e:
            print(f"Error checking middleware in {settings_file}: {e}")

        return findings

    def _check_allowed_hosts(self, settings_file: str) -> List[Finding]:
        """Check for misconfigured ALLOWED_HOSTS."""
        findings = []

        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for wildcard
            if re.search(r'ALLOWED_HOSTS\s*=\s*\[\s*["\']?\*["\']?\s*\]', content):
                findings.append(Finding(
                    title="Django ALLOWED_HOSTS Wildcard",
                    severity=Severity.MEDIUM,
                    description=(
                        "ALLOWED_HOSTS is set to ['*'], which allows any host header. "
                        "This can lead to Host header attacks and cache poisoning."
                    ),
                    file_path=settings_file,
                    remediation="Set ALLOWED_HOSTS to specific domain names.",
                    references=[
                        "https://docs.djangoproject.com/en/stable/ref/settings/#allowed-hosts",
                    ],
                    confidence=0.95
                ))

        except Exception as e:
            print(f"Error checking ALLOWED_HOSTS in {settings_file}: {e}")

        return findings

    def _scan_sql_injection(self, target_path: str) -> List[Finding]:
        """Scan for potential SQL injection vulnerabilities."""
        findings = []

        sql_patterns = [
            r'\.raw\(["\'].*%s.*["\']',  # Raw SQL with string formatting
            r'\.extra\(.*where=',  # .extra() with WHERE clause
            r'execute\(["\'].*\+.*["\']',  # Cursor execute with concatenation
        ]

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'venv', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    matches = self._scan_file_for_patterns(file_path, sql_patterns)

                    for line_num, line_content, pattern in matches:
                        findings.append(Finding(
                            title="Potential SQL Injection in Django",
                            severity=Severity.HIGH,
                            description=(
                                "Potential SQL injection vulnerability detected. The code appears "
                                "to use raw SQL or string concatenation with database queries."
                            ),
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line_content,
                            remediation=(
                                "Use parameterized queries or Django ORM:\n"
                                "- Use .filter() instead of .raw()\n"
                                "- Use query parameters: .raw('SELECT * FROM table WHERE id = %s', [user_id])\n"
                                "- Avoid .extra() if possible"
                            ),
                            references=[
                                "https://docs.djangoproject.com/en/stable/topics/security/#sql-injection-protection",
                            ],
                            confidence=0.7
                        ))

        return findings
