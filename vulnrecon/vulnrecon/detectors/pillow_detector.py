"""Pillow (PIL) vulnerability detector."""

import os
from typing import List, Dict, Any

from .base import BaseDetector, Finding, Severity


class PillowDetector(BaseDetector):
    """Detects Pillow image processing vulnerabilities."""

    def detect(self, target_path: str, dependencies: List[Dict[str, Any]]) -> List[Finding]:
        """Detect Pillow vulnerabilities."""
        findings = []

        # Check if Pillow is in dependencies
        pillow_dep = None
        for dep in dependencies:
            if dep.get("dependency_name", "").lower() in ["pillow", "pil"]:
                pillow_dep = dep
                break

        if not pillow_dep:
            return findings

        # Check version
        version = pillow_dep.get("version_spec", "").strip(">=<~=")
        if version:
            findings.extend(self._check_vulnerable_version(version))

        # Scan for unsafe image processing patterns
        findings.extend(self._scan_image_processing(target_path))

        return findings

    def _check_vulnerable_version(self, version: str) -> List[Finding]:
        """Check if Pillow version is vulnerable."""
        findings = []

        vulnerable_spec = self.config.get("vulnerable_versions", "<10.0.0")

        if self._check_version_vulnerable(version, vulnerable_spec):
            findings.append(Finding(
                title="Vulnerable Pillow Version Detected",
                severity=Severity.HIGH,
                description=(
                    f"Pillow version {version} has known vulnerabilities including buffer "
                    f"overflows, DoS, and arbitrary code execution through malformed images."
                ),
                remediation="Upgrade Pillow to version 10.0.0 or later.",
                references=[
                    "https://pillow.readthedocs.io/en/stable/releasenotes/",
                ],
                metadata={"detected_version": version},
                confidence=0.9
            ))

        return findings

    def _scan_image_processing(self, target_path: str) -> List[Finding]:
        """Scan for unsafe image processing patterns."""
        findings = []

        patterns = [
            r'Image\.open\(',
            r'ImageFile\.LOAD_TRUNCATED_IMAGES\s*=\s*True',
        ]

        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', 'venv', 'node_modules']]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    matches = self._scan_file_for_patterns(file_path, patterns)

                    for line_num, line_content, pattern in matches:
                        # Check context for user input
                        has_user_input = any(
                            keyword in line_content.lower()
                            for keyword in ["request", "upload", "user", "file"]
                        )

                        if has_user_input or "LOAD_TRUNCATED_IMAGES" in line_content:
                            severity = Severity.HIGH if has_user_input else Severity.MEDIUM

                            findings.append(Finding(
                                title="Unsafe Image Processing Pattern",
                                severity=severity,
                                description=(
                                    "Image processing on potentially untrusted input detected. "
                                    "Malformed images can exploit vulnerabilities in Pillow to "
                                    "cause DoS or potentially execute code."
                                ),
                                file_path=file_path,
                                line_number=line_num,
                                code_snippet=line_content,
                                remediation=(
                                    "1. Validate image file types before processing\n"
                                    "2. Set resource limits (max image size, pixels)\n"
                                    "3. Process images in sandboxed environment\n"
                                    "4. Keep Pillow updated to latest version"
                                ),
                                confidence=0.7 if has_user_input else 0.5
                            ))

        return findings
