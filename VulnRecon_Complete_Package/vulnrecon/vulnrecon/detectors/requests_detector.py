"""Requests library vulnerability detector."""

import os
from typing import List, Dict, Any

from .base import BaseDetector, Finding, Severity


class RequestsDetector(BaseDetector):
    """Detects vulnerabilities in requests library usage."""

    def detect(self, target_path: str, dependencies: List[Dict[str, Any]]) -> List[Finding]:
        """Detect requests library vulnerabilities."""
        findings = []

        # Check if requests is in dependencies
        has_requests = any(
            dep.get("dependency_name", "").lower() == "requests"
            for dep in dependencies
        )

        if not has_requests:
            return findings

        # Scan for unsafe patterns
        findings.extend(self._scan_ssl_verification(target_path))
        findings.extend(self._scan_ssrf_patterns(target_path))

        return findings

    def _scan_ssl_verification(self, target_path: str) -> List[Finding]:
        """Scan for disabled SSL verification."""
        findings = []

        patterns = [
            r'verify\s*=\s*False',
            r"verify\s*=\s*'?False'?",
        ]

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'venv', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    matches = self._scan_file_for_patterns(file_path, patterns)

                    for line_num, line_content, pattern in matches:
                        findings.append(Finding(
                            title="Disabled SSL Certificate Verification",
                            severity=Severity.HIGH,
                            description=(
                                "SSL certificate verification is disabled in requests call. "
                                "This makes the application vulnerable to man-in-the-middle "
                                "attacks where an attacker can intercept and modify traffic."
                            ),
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line_content,
                            remediation=(
                                "Remove verify=False parameter or set verify=True. "
                                "If using self-signed certificates, specify the CA bundle path:\n"
                                "requests.get(url, verify='/path/to/ca-bundle.crt')"
                            ),
                            references=[
                                "https://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification",
                            ],
                            confidence=0.95
                        ))

        return findings

    def _scan_ssrf_patterns(self, target_path: str) -> List[Finding]:
        """Scan for potential SSRF vulnerabilities."""
        findings = []

        patterns = [
            r'requests\.(get|post|put|delete)\s*\(["\']?\s*\+',  # URL concatenation
            r'requests\.(get|post|put|delete)\s*\(.*f["\']',  # f-string URLs
        ]

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'venv', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    matches = self._scan_file_for_patterns(file_path, patterns)

                    for line_num, line_content, pattern in matches:
                        # Check for user input indicators
                        has_user_input = any(
                            keyword in line_content.lower()
                            for keyword in ["request", "input", "user", "param"]
                        )

                        if has_user_input:
                            findings.append(Finding(
                                title="Potential Server-Side Request Forgery (SSRF)",
                                severity=Severity.HIGH,
                                description=(
                                    "User input appears to be used in constructing URLs for "
                                    "requests. This could allow an attacker to make the server "
                                    "send requests to arbitrary internal or external URLs."
                                ),
                                file_path=file_path,
                                line_number=line_num,
                                code_snippet=line_content,
                                remediation=(
                                    "1. Validate and sanitize all user input used in URLs\n"
                                    "2. Use allowlist of permitted domains/IPs\n"
                                    "3. Disable redirects or limit redirect chains\n"
                                    "4. Block requests to internal/private IP ranges"
                                ),
                                references=[
                                    "https://owasp.org/www-community/attacks/Server_Side_Request_Forgery",
                                ],
                                confidence=0.6
                            ))

        return findings
