"""PyYAML vulnerability detector with enhanced version parsing."""

import os
import re
from typing import List, Dict, Any
from pathlib import Path

from .base import BaseDetector, Finding, Severity
from ..utils.version_parser import enhanced_parser, is_vulnerable


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
        Detect PyYAML vulnerabilities with enhanced version parsing.

        Args:
            target_path: Path to the code/repository to scan
            dependencies: List of dependencies

        Returns:
            List of findings
        """
        findings = []

        # Find PyYAML dependencies with enhanced name matching
        pyyaml_deps = []
        for dep in dependencies:
            dep_name = dep.get("dependency_name", dep.get("name", ""))
            normalized_name = enhanced_parser.normalize_package_name(dep_name)
            
            if normalized_name == "pyyaml":
                pyyaml_deps.append(dep)

        if not pyyaml_deps:
            return findings

        # Check versions with enhanced parsing
        for dep in pyyaml_deps:
            version_spec = dep.get("version_spec", dep.get("version", ""))
            
            if version_spec:
                findings.extend(self._check_vulnerable_version_enhanced(dep_name, version_spec))
            else:
                # No version specified - flag as potential risk
                findings.append(Finding(
                    title="PyYAML Version Not Specified",
                    severity=Severity.MEDIUM,
                    description=(
                        f"PyYAML dependency '{dep_name}' does not specify a version. "
                        f"This could potentially install a vulnerable version. "
                        f"It's recommended to pin to a safe version (>=5.4)."
                    ),
                    cve_ids=self.CVE_IDS,
                    remediation="Pin PyYAML to a safe version: PyYAML>=5.4",
                    references=[
                        "https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation",
                    ],
                    confidence=0.6,
                    metadata={"dependency_name": dep_name, "version_spec": "unspecified"}
                ))

        # Scan Python files for unsafe patterns
        findings.extend(self._scan_code_patterns(target_path))

        return findings

    def _check_vulnerable_version(self, version: str) -> List[Finding]:
        """Check if PyYAML version is vulnerable (legacy method)."""
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
    
    def _check_vulnerable_version_enhanced(self, dep_name: str, version_spec: str) -> List[Finding]:
        """Check if PyYAML version is vulnerable using enhanced parsing."""
        findings = []
        
        # Parse the requirement string properly
        parsed_req = enhanced_parser.parse_requirement_string(f"{dep_name}{version_spec}")
        
        if not parsed_req:
            # Could not parse - treat as potential risk
            findings.append(Finding(
                title="PyYAML Version Parsing Failed",
                severity=Severity.MEDIUM,
                description=(
                    f"Could not parse PyYAML version specification '{version_spec}'. "
                    f"This may indicate an unusual version format that needs manual review."
                ),
                cve_ids=self.CVE_IDS,
                remediation="Review and standardize version specification, ensure PyYAML>=5.4",
                references=[
                    "https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation",
                ],
                confidence=0.5,
                metadata={"dependency_name": dep_name, "version_spec": version_spec, "parse_error": True}
            ))
            return findings
        
        # Extract exact version if possible
        exact_version = enhanced_parser.extract_exact_version(version_spec)
        
        if exact_version:
            # Define PyYAML vulnerability ranges based on known CVEs
            vulnerable_ranges = [
                {
                    'events': [
                        {'introduced': '0'},
                        {'fixed': '5.4'}
                    ]
                }
            ]
            
            is_vuln, reason = is_vulnerable(exact_version, vulnerable_ranges)
            
            if is_vuln:
                findings.append(Finding(
                    title="Vulnerable PyYAML Version Detected",
                    severity=Severity.HIGH,
                    description=(
                        f"PyYAML version {exact_version} is vulnerable to arbitrary code execution "
                        f"through unsafe deserialization. Versions prior to 5.4 are affected by "
                        f"multiple CVEs including CVE-2020-14343."
                    ),
                    cve_ids=self.CVE_IDS,
                    remediation="Upgrade PyYAML to version 5.4 or later.",
                    references=[
                        "https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation",
                        "https://nvd.nist.gov/vuln/detail/CVE-2020-14343",
                    ],
                    confidence=0.95,
                    metadata={
                        "dependency_name": dep_name,
                        "detected_version": exact_version,
                        "version_spec": version_spec,
                        "vulnerability_reason": reason
                    }
                ))
            else:
                # Version is safe - log for debugging
                findings.append(Finding(
                    title="PyYAML Safe Version Detected",
                    severity=Severity.INFO,
                    description=(
                        f"PyYAML version {exact_version} appears to be safe from known "
                        f"deserialization vulnerabilities. {reason}"
                    ),
                    cve_ids=[],
                    remediation="No action required for this version.",
                    references=[],
                    confidence=0.90,
                    metadata={
                        "dependency_name": dep_name,
                        "detected_version": exact_version,
                        "version_spec": version_spec,
                        "safety_reason": reason
                    }
                ))
        else:
            # Version range specified - analyze the range
            specifier = parsed_req.get('parsed_specifier')
            if specifier:
                # Check if the range could include vulnerable versions
                could_be_vulnerable = self._analyze_version_range(specifier)
                
                if could_be_vulnerable:
                    findings.append(Finding(
                        title="PyYAML Version Range May Include Vulnerable Versions",
                        severity=Severity.MEDIUM,
                        description=(
                            f"PyYAML version specification '{version_spec}' may allow "
                            f"installation of vulnerable versions (< 5.4). "
                            f"Consider tightening the version constraint."
                        ),
                        cve_ids=self.CVE_IDS,
                        remediation="Update version constraint to ensure PyYAML>=5.4",
                        references=[
                            "https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation",
                        ],
                        confidence=0.7,
                        metadata={
                            "dependency_name": dep_name,
                            "version_spec": version_spec,
                            "range_analysis": "may_include_vulnerable"
                        }
                    ))
                else:
                    findings.append(Finding(
                        title="PyYAML Version Range Appears Safe",
                        severity=Severity.INFO,
                        description=(
                            f"PyYAML version specification '{version_spec}' appears to "
                            f"exclude known vulnerable versions (< 5.4)."
                        ),
                        cve_ids=[],
                        remediation="No action required.",
                        references=[],
                        confidence=0.8,
                        metadata={
                            "dependency_name": dep_name,
                            "version_spec": version_spec,
                            "range_analysis": "appears_safe"
                        }
                    ))
        
        return findings
    
    def _analyze_version_range(self, specifier) -> bool:
        """Analyze if a version range could include vulnerable versions."""
        try:
            from packaging import version
            
            # Test some known vulnerable versions
            vulnerable_versions = ['3.11', '5.0', '5.1', '5.2', '5.3', '5.3.1']
            
            for vuln_ver in vulnerable_versions:
                try:
                    if version.parse(vuln_ver) in specifier:
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            # If we can't analyze, assume it could be vulnerable
            return True

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
