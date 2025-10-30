"""PyYAML vulnerability detector."""

import os
import re
from typing import List, Dict, Any
from pathlib import Path

from .base import BaseDetector, Finding, Severity


class PyYAMLDetector(BaseDetector):
    """Detects PyYAML deserialization vulnerabilities."""

    UNSAFE_PATTERNS = [
        r"yaml\.load\s*\(",
        r"yaml\.load_all\s*\(",
        r"Loader\s*=\s*yaml\.Loader",
        r"Loader\s*=\s*yaml\.UnsafeLoader",
        r"Loader\s*=\s*yaml\.FullLoader",
    ]

    SAFE_PATTERNS = [
        r"yaml\.safe_load\s*\(",
        r"yaml\.safe_load_all\s*\(",
        r"Loader\s*=\s*yaml\.SafeLoader",
    ]

    CVE_IDS = [
        "GHSA-rprw-h62v-c2w7",
        "PYSEC-2018-49",
        "PYSEC-2020-176",
        "PYSEC-2020-96",
        "PYSEC-2021-142",
        "GHSA-3pqx-4fqf-j49f",
        "GHSA-6757-jp84-gxfx",
        "GHSA-8q59-q68h-6hv4",
    ]

    def detect(self, target_path: str, dependencies: List[Dict[str, Any]]) -> List[Finding]:
        """
        Detect PyYAML vulnerabilities.

        Args:
            target_path: Path to the code/repository to scan
            dependencies: List of dependencies

        Returns:
            List of findings
        """
        findings = []

        # Check if PyYAML is in dependencies
        has_pyyaml = any(
            dep.get("dependency_name", "").lower() in ["pyyaml", "yaml"]
            for dep in dependencies
        )

        if not has_pyyaml:
            return findings

        # Check version if available
        pyyaml_version = None
        for dep in dependencies:
            if dep.get("dependency_name", "").lower() in ["pyyaml", "yaml"]:
                pyyaml_version = dep.get("version_spec", "").strip(">=<~=")
                break

        if pyyaml_version:
            findings.extend(self._check_vulnerable_version(pyyaml_version))

        # Scan Python files for unsafe patterns
        findings.extend(self._scan_code_patterns(target_path))

        return findings

    def _check_vulnerable_version(self, version: str) -> List[Finding]:
        """Check if PyYAML version is vulnerable."""
        findings = []

        vulnerable_spec = self.config.get("vulnerable_versions", "<5.4")

        if self._check_version_vulnerable(version, vulnerable_spec):
            findings.append(Finding(
                title="Vulnerable PyYAML Version Detected",
                severity=Severity.HIGH,
                description=(
                    f"PyYAML version {version} is known to be vulnerable to "
                    f"arbitrary code execution through unsafe deserialization. "
                    f"Multiple CVEs affect versions prior to 5.4."
                ),
                cve_ids=self.CVE_IDS,
                remediation="Upgrade PyYAML to version 5.4 or later.",
                references=[
                    "https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation",
                    "https://nvd.nist.gov/vuln/detail/CVE-2020-14343",
                ],
                metadata={"detected_version": version}
            ))

        return findings

    def _scan_code_patterns(self, target_path: str) -> List[Finding]:
        """Scan code for unsafe PyYAML usage patterns."""
        findings = []

        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk(target_path):
            # Skip common exclude directories
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'venv', 'node_modules', '__pycache__']]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        # Scan each Python file
        for py_file in python_files:
            matches = self._scan_file_for_patterns(
                py_file,
                self.UNSAFE_PATTERNS,
                self.SAFE_PATTERNS
            )

            for line_num, line_content, pattern in matches:
                # Determine severity based on context
                severity = Severity.CRITICAL

                # Check if user input might be involved
                has_user_input = any(
                    keyword in line_content.lower()
                    for keyword in ["request", "input", "user", "file", "read"]
                )

                if has_user_input:
                    severity = Severity.CRITICAL
                    risk_note = "User input appears to be processed - HIGH RISK!"
                else:
                    risk_note = "Potentially unsafe YAML deserialization detected."

                findings.append(Finding(
                    title="Unsafe PyYAML Deserialization Pattern",
                    severity=severity,
                    description=(
                        f"{risk_note}\n\n"
                        f"The code uses an unsafe YAML loading method that can lead to "
                        f"arbitrary code execution. The pattern '{pattern}' allows "
                        f"deserialization of Python objects, which attackers can exploit "
                        f"to execute arbitrary code."
                    ),
                    file_path=py_file,
                    line_number=line_num,
                    code_snippet=line_content,
                    cve_ids=self.CVE_IDS,
                    remediation=(
                        "Replace unsafe methods with safe alternatives:\n"
                        "- Use yaml.safe_load() instead of yaml.load()\n"
                        "- Use yaml.safe_load_all() instead of yaml.load_all()\n"
                        "- Always use Loader=yaml.SafeLoader if specifying a loader\n\n"
                        "Example:\n"
                        "  # Unsafe:\n"
                        "  data = yaml.load(user_input)\n\n"
                        "  # Safe:\n"
                        "  data = yaml.safe_load(user_input)"
                    ),
                    references=[
                        "https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation",
                        "https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data",
                    ],
                    confidence=0.9 if has_user_input else 0.7,
                    metadata={
                        "pattern_matched": pattern,
                        "has_user_input": has_user_input,
                    }
                ))

        return findings
