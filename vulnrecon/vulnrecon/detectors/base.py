"""Base detector class for vulnerability detection."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Finding:
    """Represents a security finding."""

    title: str
    severity: Severity
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    cve_ids: List[str] = field(default_factory=list)
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "title": self.title,
            "severity": self.severity.value,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "cve_ids": self.cve_ids,
            "remediation": self.remediation,
            "references": self.references,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class BaseDetector(ABC):
    """Base class for all vulnerability detectors."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the detector.

        Args:
            config: Configuration dictionary for this detector
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.name = self.__class__.__name__

    @abstractmethod
    def detect(self, target_path: str, dependencies: List[Dict[str, Any]]) -> List[Finding]:
        """
        Perform vulnerability detection.

        Args:
            target_path: Path to the code/repository to scan
            dependencies: List of dependencies with version information

        Returns:
            List of findings discovered
        """
        pass

    def is_enabled(self) -> bool:
        """Check if detector is enabled."""
        return self.enabled

    def get_name(self) -> str:
        """Get detector name."""
        return self.name

    def _scan_file_for_patterns(
        self,
        file_path: str,
        patterns: List[str],
        exclude_patterns: List[str] = None
    ) -> List[tuple]:
        """
        Scan a file for dangerous patterns.

        Args:
            file_path: Path to file to scan
            patterns: List of regex patterns to search for
            exclude_patterns: Patterns that indicate safe usage

        Returns:
            List of (line_number, line_content, matched_pattern) tuples
        """
        import re

        matches = []
        exclude_patterns = exclude_patterns or []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Check if line matches any exclusion pattern
                    is_safe = any(
                        re.search(pattern, line)
                        for pattern in exclude_patterns
                    )

                    if is_safe:
                        continue

                    # Check for dangerous patterns
                    for pattern in patterns:
                        if re.search(pattern, line):
                            matches.append((line_num, line.strip(), pattern))

        except Exception as e:
            # Log error but don't fail the scan
            print(f"Error scanning {file_path}: {e}")

        return matches

    def _check_version_vulnerable(
        self,
        current_version: str,
        vulnerable_spec: str
    ) -> bool:
        """
        Check if a version matches vulnerable specification.

        Args:
            current_version: Current package version
            vulnerable_spec: Vulnerable version specification (e.g., "<5.4", ">=1.0,<2.0")

        Returns:
            True if version is vulnerable
        """
        try:
            from packaging import version
            from packaging.specifiers import SpecifierSet

            current = version.parse(current_version)
            spec = SpecifierSet(vulnerable_spec)

            return current in spec
        except Exception:
            # If we can't parse, assume potentially vulnerable
            return True
