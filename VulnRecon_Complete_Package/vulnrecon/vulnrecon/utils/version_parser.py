"""
Enhanced version parsing and matching utilities using professional libraries.
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from packaging import version
from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import InvalidVersion

logger = logging.getLogger(__name__)


class EnhancedVersionParser:
    """Enhanced version parser using packaging library and professional tools."""
    
    def __init__(self):
        """Initialize the enhanced version parser."""
        self.version_cache = {}
        
    def parse_requirement_string(self, req_string: str) -> Optional[Dict[str, Any]]:
        """
        Parse a requirement string using packaging library.
        
        Args:
            req_string: Requirement string (e.g., "PyYAML>=5.4,<7.0")
            
        Returns:
            Dictionary with parsed requirement info or None if invalid
        """
        if not req_string or not req_string.strip():
            return None
            
        req_string = req_string.strip()
        
        try:
            # Use packaging library for accurate parsing
            req = Requirement(req_string)
            
            return {
                'name': req.name,
                'specifier': str(req.specifier) if req.specifier else '',
                'extras': list(req.extras) if req.extras else [],
                'marker': str(req.marker) if req.marker else None,
                'url': req.url,
                'parsed_specifier': req.specifier,
            }
            
        except InvalidRequirement as e:
            logger.debug(f"Invalid requirement '{req_string}': {e}")
            # Fallback to regex parsing
            return self._fallback_parse_requirement(req_string)
    
    def _fallback_parse_requirement(self, req_string: str) -> Optional[Dict[str, Any]]:
        """Fallback regex-based parsing for malformed requirements."""
        # Handle common patterns
        patterns = [
            # Standard: package==1.0.0, package>=1.0
            r'^([a-zA-Z0-9\-_.]+)\s*([><=!~^]+[^;#]*)',
            # Just package name
            r'^([a-zA-Z0-9\-_.]+)\s*$',
            # With extras: package[extra]>=1.0
            r'^([a-zA-Z0-9\-_.]+)\[([^\]]+)\]\s*([><=!~^]+[^;#]*)?',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, req_string.strip())
            if match:
                groups = match.groups()
                name = groups[0]
                
                if len(groups) >= 2 and groups[1]:
                    if '[' in req_string:  # Has extras
                        extras = [e.strip() for e in groups[1].split(',')]
                        specifier = groups[2] if len(groups) > 2 and groups[2] else ''
                    else:
                        extras = []
                        specifier = groups[1]
                else:
                    extras = []
                    specifier = ''
                
                return {
                    'name': name,
                    'specifier': specifier.strip(),
                    'extras': extras,
                    'marker': None,
                    'url': None,
                    'parsed_specifier': None,
                }
        
        logger.warning(f"Could not parse requirement: {req_string}")
        return None
    
    def extract_exact_version(self, version_spec: str) -> Optional[str]:
        """
        Extract exact version from version specifier.
        
        Args:
            version_spec: Version specifier (e.g., "==1.0.0", ">=1.0,<2.0")
            
        Returns:
            Exact version string if found, None otherwise
        """
        if not version_spec:
            return None
            
        # Handle exact version (==1.0.0)
        exact_match = re.search(r'==\s*([^\s,;]+)', version_spec)
        if exact_match:
            return exact_match.group(1)
        
        # Handle single version without operator (common in lock files)
        if re.match(r'^\d+(\.\d+)*([a-zA-Z]\d*)?$', version_spec.strip()):
            return version_spec.strip()
        
        # For range specifiers, try to extract a representative version
        # This is less accurate but better than nothing
        version_match = re.search(r'([>=<~^!]*)\s*([^\s,;]+)', version_spec)
        if version_match:
            operator = version_match.group(1)
            ver = version_match.group(2)
            
            # For >= operators, the version is a good representative
            if operator.startswith('>=') or operator.startswith('>'):
                return ver
            # For < operators, we can't be sure of the exact version
            elif operator.startswith('<'):
                return None
        
        return None
    
    def is_version_vulnerable(self, current_version: str, vulnerable_ranges: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Check if a version is vulnerable based on OSV vulnerability ranges.
        
        Args:
            current_version: Current package version
            vulnerable_ranges: List of vulnerability range dictionaries from OSV
            
        Returns:
            Tuple of (is_vulnerable, reason)
        """
        if not current_version or not vulnerable_ranges:
            return False, "No version or vulnerability data"
        
        try:
            current_ver = version.parse(current_version)
        except InvalidVersion as e:
            logger.warning(f"Invalid version format '{current_version}': {e}")
            return True, f"Cannot parse version: {e}"
        
        for vuln_range in vulnerable_ranges:
            if self._version_in_vulnerable_range(current_ver, vuln_range):
                return True, f"Version {current_version} is in vulnerable range"
        
        return False, f"Version {current_version} is not in any vulnerable range"
    
    def _version_in_vulnerable_range(self, current_ver: version.Version, vuln_range: Dict[str, Any]) -> bool:
        """Check if version is within a specific vulnerable range."""
        try:
            # Parse OSV range format
            if 'events' in vuln_range:
                events = vuln_range['events']
                introduced = None
                fixed = None
                
                for event in events:
                    if 'introduced' in event:
                        intro_ver = event['introduced']
                        if intro_ver == '0':
                            introduced = version.parse('0.0.0')
                        else:
                            introduced = version.parse(intro_ver)
                    elif 'fixed' in event:
                        fixed = version.parse(event['fixed'])
                
                # Check if current version is in vulnerable range
                if introduced is not None:
                    if fixed is not None:
                        # Range: introduced <= version < fixed
                        return introduced <= current_ver < fixed
                    else:
                        # Range: introduced <= version (no upper bound)
                        return introduced <= current_ver
                elif fixed is not None:
                    # Range: version < fixed (from beginning)
                    return current_ver < fixed
            
            # Handle string format from database
            elif isinstance(vuln_range, str):
                # Try to parse as version specifier
                try:
                    spec = SpecifierSet(vuln_range)
                    return current_ver in spec
                except InvalidSpecifier:
                    logger.debug(f"Could not parse specifier: {vuln_range}")
            
        except (InvalidVersion, ValueError) as e:
            logger.debug(f"Error parsing vulnerability range: {e}")
        
        return False
    
    def normalize_package_name(self, name: str) -> str:
        """
        Normalize package name for consistent matching.
        
        Args:
            name: Package name
            
        Returns:
            Normalized package name
        """
        if not name:
            return ""
        
        # Convert to lowercase and replace underscores/hyphens
        normalized = name.lower().replace('_', '-')
        
        # Handle common aliases
        aliases = {
            'pyyaml': 'pyyaml',
            'yaml': 'pyyaml',
            'pillow': 'pillow',
            'pil': 'pillow',
        }
        
        return aliases.get(normalized, normalized)
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        try:
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
                
        except InvalidVersion as e:
            logger.warning(f"Error comparing versions '{version1}' and '{version2}': {e}")
            # Fallback to string comparison
            if version1 < version2:
                return -1
            elif version1 > version2:
                return 1
            else:
                return 0
    
    def get_latest_safe_version(self, package_name: str, ecosystem: str = 'pypi') -> Optional[str]:
        """
        Get the latest safe version of a package (placeholder for future implementation).
        
        Args:
            package_name: Package name
            ecosystem: Package ecosystem
            
        Returns:
            Latest safe version string or None
        """
        # This would integrate with package registries to get latest versions
        # For now, return None to indicate this feature needs implementation
        return None
    
    def validate_version_string(self, version_str: str) -> bool:
        """
        Validate if a version string is valid.
        
        Args:
            version_str: Version string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not version_str:
            return False
        
        try:
            version.parse(version_str)
            return True
        except InvalidVersion:
            return False


# Global instance
enhanced_parser = EnhancedVersionParser()


def parse_requirement(req_string: str) -> Optional[Dict[str, Any]]:
    """Convenience function to parse a requirement string."""
    return enhanced_parser.parse_requirement_string(req_string)


def is_vulnerable(current_version: str, vulnerable_ranges: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Convenience function to check if version is vulnerable."""
    return enhanced_parser.is_version_vulnerable(current_version, vulnerable_ranges)


def normalize_name(package_name: str) -> str:
    """Convenience function to normalize package name."""
    return enhanced_parser.normalize_package_name(package_name)
