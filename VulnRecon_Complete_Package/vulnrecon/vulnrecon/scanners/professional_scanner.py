"""
Professional vulnerability scanner integrating multiple security tools.
"""

import json
import logging
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import requests

from ..utils.version_parser import enhanced_parser, is_vulnerable
from ..detectors.base import Finding, Severity

logger = logging.getLogger(__name__)


@dataclass
class VulnerabilityResult:
    """Structured vulnerability result."""
    tool: str
    package_name: str
    version: Optional[str]
    vulnerability_id: str
    severity: str
    title: str
    description: str
    fix_version: Optional[str]
    references: List[str]
    confidence: float


class ProfessionalVulnerabilityScanner:
    """Professional vulnerability scanner using multiple security tools."""
    
    def __init__(self):
        """Initialize the professional scanner."""
        self.available_tools = self._check_available_tools()
        self.osv_cache = {}
        
    def _check_available_tools(self) -> Dict[str, bool]:
        """Check which professional tools are available."""
        tools = {}
        
        # Check Bandit
        try:
            result = subprocess.run(['bandit', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            tools['bandit'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['bandit'] = False
        
        # Check Safety
        try:
            result = subprocess.run(['safety', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            tools['safety'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['safety'] = False
        
        # Check pip-audit
        try:
            result = subprocess.run(['pip-audit', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            tools['pip-audit'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['pip-audit'] = False
        
        # Check Semgrep
        try:
            result = subprocess.run(['semgrep', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            tools['semgrep'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['semgrep'] = False
        
        # Check Trivy
        try:
            result = subprocess.run(['trivy', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            tools['trivy'] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tools['trivy'] = False
        
        logger.info(f"Available tools: {[tool for tool, available in tools.items() if available]}")
        return tools
    
    def scan_dependencies(self, dependencies: List[Dict[str, Any]], 
                         target_path: Optional[str] = None) -> List[VulnerabilityResult]:
        """
        Scan dependencies using all available professional tools.
        
        Args:
            dependencies: List of dependency dictionaries
            target_path: Optional path to source code for static analysis
            
        Returns:
            List of vulnerability results
        """
        results = []
        
        # Create requirements.txt for dependency scanning
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            requirements_path = f.name
            for dep in dependencies:
                name = dep.get('dependency_name', dep.get('name', ''))
                version_spec = dep.get('version_spec', dep.get('version', ''))
                ecosystem = dep.get('ecosystem', 'pypi')
                
                if ecosystem.lower() in ['pypi', 'python'] and name:
                    if version_spec:
                        f.write(f"{name}{version_spec}\n")
                    else:
                        f.write(f"{name}\n")
        
        try:
            # Scan with Safety
            if self.available_tools.get('safety', False):
                safety_results = self._scan_with_safety(requirements_path, dependencies)
                results.extend(safety_results)
            
            # Scan with pip-audit
            if self.available_tools.get('pip-audit', False):
                pip_audit_results = self._scan_with_pip_audit(requirements_path, dependencies)
                results.extend(pip_audit_results)
            
            # Scan with Bandit (if source code available)
            if target_path and self.available_tools.get('bandit', False):
                bandit_results = self._scan_with_bandit(target_path)
                results.extend(bandit_results)
            
            # Scan with Semgrep (if source code available)
            if target_path and self.available_tools.get('semgrep', False):
                semgrep_results = self._scan_with_semgrep(target_path)
                results.extend(semgrep_results)
            
            # Scan with Trivy
            if self.available_tools.get('trivy', False):
                trivy_results = self._scan_with_trivy(requirements_path)
                results.extend(trivy_results)
            
            # Enhanced OSV API scan with better version matching
            osv_results = self._scan_with_enhanced_osv(dependencies)
            results.extend(osv_results)
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(requirements_path)
            except OSError:
                pass
        
        return self._deduplicate_results(results)
    
    def _scan_with_safety(self, requirements_path: str, 
                         dependencies: List[Dict[str, Any]]) -> List[VulnerabilityResult]:
        """Scan with Safety tool."""
        results = []
        
        try:
            cmd = ['safety', 'check', '--file', requirements_path, '--json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # No vulnerabilities found
                return results
            
            # Parse Safety JSON output
            try:
                safety_data = json.loads(result.stdout)
                for vuln in safety_data:
                    results.append(VulnerabilityResult(
                        tool='safety',
                        package_name=vuln.get('package', ''),
                        version=vuln.get('installed_version', ''),
                        vulnerability_id=vuln.get('id', ''),
                        severity=self._map_safety_severity(vuln.get('severity', '')),
                        title=vuln.get('advisory', ''),
                        description=vuln.get('advisory', ''),
                        fix_version=vuln.get('fixed_in', [None])[0] if vuln.get('fixed_in') else None,
                        references=[],
                        confidence=0.95
                    ))
            except json.JSONDecodeError:
                logger.warning("Could not parse Safety JSON output")
                
        except subprocess.TimeoutExpired:
            logger.warning("Safety scan timed out")
        except Exception as e:
            logger.error(f"Error running Safety: {e}")
        
        return results
    
    def _scan_with_pip_audit(self, requirements_path: str, 
                           dependencies: List[Dict[str, Any]]) -> List[VulnerabilityResult]:
        """Scan with pip-audit tool."""
        results = []
        
        try:
            cmd = ['pip-audit', '--requirement', requirements_path, '--format', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                try:
                    audit_data = json.loads(result.stdout)
                    vulnerabilities = audit_data.get('vulnerabilities', [])
                    
                    for vuln in vulnerabilities:
                        results.append(VulnerabilityResult(
                            tool='pip-audit',
                            package_name=vuln.get('package', ''),
                            version=vuln.get('installed_version', ''),
                            vulnerability_id=vuln.get('id', ''),
                            severity=self._map_pip_audit_severity(vuln),
                            title=vuln.get('description', ''),
                            description=vuln.get('description', ''),
                            fix_version=vuln.get('fix_versions', [None])[0] if vuln.get('fix_versions') else None,
                            references=vuln.get('aliases', []),
                            confidence=0.98
                        ))
                except json.JSONDecodeError:
                    logger.warning("Could not parse pip-audit JSON output")
                    
        except subprocess.TimeoutExpired:
            logger.warning("pip-audit scan timed out")
        except Exception as e:
            logger.error(f"Error running pip-audit: {e}")
        
        return results
    
    def _scan_with_bandit(self, target_path: str) -> List[VulnerabilityResult]:
        """Scan with Bandit tool."""
        results = []
        
        try:
            cmd = ['bandit', '-r', target_path, '-f', 'json', '-ll']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    for issue in bandit_data.get('results', []):
                        results.append(VulnerabilityResult(
                            tool='bandit',
                            package_name='code-analysis',
                            version=None,
                            vulnerability_id=issue.get('test_id', ''),
                            severity=self._map_bandit_severity(issue.get('issue_severity', '')),
                            title=issue.get('test_name', ''),
                            description=issue.get('issue_text', ''),
                            fix_version=None,
                            references=[],
                            confidence=issue.get('issue_confidence', 0.5)
                        ))
                except json.JSONDecodeError:
                    logger.warning("Could not parse Bandit JSON output")
                    
        except subprocess.TimeoutExpired:
            logger.warning("Bandit scan timed out")
        except Exception as e:
            logger.error(f"Error running Bandit: {e}")
        
        return results
    
    def _scan_with_semgrep(self, target_path: str) -> List[VulnerabilityResult]:
        """Scan with Semgrep tool."""
        results = []
        
        try:
            cmd = ['semgrep', '--config=auto', '--json', target_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.stdout:
                try:
                    semgrep_data = json.loads(result.stdout)
                    for finding in semgrep_data.get('results', []):
                        results.append(VulnerabilityResult(
                            tool='semgrep',
                            package_name='code-analysis',
                            version=None,
                            vulnerability_id=finding.get('check_id', ''),
                            severity=self._map_semgrep_severity(finding.get('extra', {}).get('severity', '')),
                            title=finding.get('extra', {}).get('message', ''),
                            description=finding.get('extra', {}).get('message', ''),
                            fix_version=None,
                            references=finding.get('extra', {}).get('references', []),
                            confidence=0.85
                        ))
                except json.JSONDecodeError:
                    logger.warning("Could not parse Semgrep JSON output")
                    
        except subprocess.TimeoutExpired:
            logger.warning("Semgrep scan timed out")
        except Exception as e:
            logger.error(f"Error running Semgrep: {e}")
        
        return results
    
    def _scan_with_trivy(self, requirements_path: str) -> List[VulnerabilityResult]:
        """Scan with Trivy tool."""
        results = []
        
        try:
            cmd = ['trivy', 'fs', '--format', 'json', '--security-checks', 'vuln', requirements_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                try:
                    trivy_data = json.loads(result.stdout)
                    for target in trivy_data.get('Results', []):
                        for vuln in target.get('Vulnerabilities', []):
                            results.append(VulnerabilityResult(
                                tool='trivy',
                                package_name=vuln.get('PkgName', ''),
                                version=vuln.get('InstalledVersion', ''),
                                vulnerability_id=vuln.get('VulnerabilityID', ''),
                                severity=vuln.get('Severity', 'UNKNOWN'),
                                title=vuln.get('Title', ''),
                                description=vuln.get('Description', ''),
                                fix_version=vuln.get('FixedVersion', ''),
                                references=vuln.get('References', []),
                                confidence=0.95
                            ))
                except json.JSONDecodeError:
                    logger.warning("Could not parse Trivy JSON output")
                    
        except subprocess.TimeoutExpired:
            logger.warning("Trivy scan timed out")
        except Exception as e:
            logger.error(f"Error running Trivy: {e}")
        
        return results
    
    def _scan_with_enhanced_osv(self, dependencies: List[Dict[str, Any]]) -> List[VulnerabilityResult]:
        """Enhanced OSV API scan with better version matching."""
        results = []
        
        for dep in dependencies:
            package_name = dep.get('dependency_name', dep.get('name', ''))
            version_spec = dep.get('version_spec', dep.get('version', ''))
            ecosystem = dep.get('ecosystem', 'pypi')
            
            if not package_name:
                continue
            
            # Extract exact version for more accurate matching
            exact_version = enhanced_parser.extract_exact_version(version_spec)
            
            # Query OSV API
            osv_vulns = self._query_osv_api(package_name, ecosystem, exact_version)
            
            for vuln in osv_vulns:
                # Enhanced version matching
                if exact_version:
                    vulnerable_ranges = self._extract_vulnerable_ranges(vuln)
                    is_vuln, reason = is_vulnerable(exact_version, vulnerable_ranges)
                    
                    if not is_vuln:
                        logger.debug(f"Skipping {package_name} {exact_version}: {reason}")
                        continue
                
                results.append(VulnerabilityResult(
                    tool='osv-enhanced',
                    package_name=package_name,
                    version=exact_version,
                    vulnerability_id=vuln.get('id', ''),
                    severity=self._extract_osv_severity(vuln),
                    title=vuln.get('summary', ''),
                    description=vuln.get('details', vuln.get('summary', '')),
                    fix_version=self._extract_fix_version(vuln),
                    references=[ref.get('url', '') for ref in vuln.get('references', [])],
                    confidence=0.90
                ))
        
        return results
    
    def _query_osv_api(self, package_name: str, ecosystem: str, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query OSV API with caching."""
        cache_key = (package_name, ecosystem, version)
        
        if cache_key in self.osv_cache:
            return self.osv_cache[cache_key]
        
        try:
            url = "https://api.osv.dev/v1/query"
            
            # Map ecosystem names to OSV API format
            ecosystem_mapping = {
                'pypi': 'PyPI',
                'python': 'PyPI',
                'pip': 'PyPI',
                'npm': 'npm',
                'maven': 'Maven',
                'go': 'Go',
                'crates': 'crates.io',
                'rust': 'crates.io'
            }
            
            # Use correct ecosystem name
            correct_ecosystem = ecosystem_mapping.get(ecosystem.lower(), ecosystem)
            
            query = {
                "package": {
                    "name": package_name,
                    "ecosystem": correct_ecosystem
                }
            }
            
            if version:
                query["version"] = version
            
            response = requests.post(url, json=query, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                vulns = data.get('vulns', [])
                self.osv_cache[cache_key] = vulns
                return vulns
            else:
                logger.warning(f"OSV API returned {response.status_code} for {package_name} (ecosystem: {correct_ecosystem})")
                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        logger.error(f"OSV API error details: {error_data}")
                    except:
                        logger.error(f"OSV API error response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error querying OSV API for {package_name}: {e}")
        
        self.osv_cache[cache_key] = []
        return []
    
    def _extract_vulnerable_ranges(self, vuln_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract vulnerable ranges from OSV vulnerability data."""
        ranges = []
        
        for affected in vuln_data.get('affected', []):
            for range_info in affected.get('ranges', []):
                ranges.append(range_info)
        
        return ranges
    
    def _extract_osv_severity(self, vuln_data: Dict[str, Any]) -> str:
        """Extract severity from OSV vulnerability data."""
        severity_info = vuln_data.get('severity', [])
        
        if severity_info and isinstance(severity_info, list):
            return severity_info[0].get('type', 'UNKNOWN')
        
        return 'UNKNOWN'
    
    def _extract_fix_version(self, vuln_data: Dict[str, Any]) -> Optional[str]:
        """Extract fix version from OSV vulnerability data."""
        for affected in vuln_data.get('affected', []):
            for range_info in affected.get('ranges', []):
                for event in range_info.get('events', []):
                    if 'fixed' in event:
                        return event['fixed']
        
        return None
    
    def _deduplicate_results(self, results: List[VulnerabilityResult]) -> List[VulnerabilityResult]:
        """Remove duplicate vulnerability results."""
        seen = set()
        deduplicated = []
        
        for result in results:
            # Create a key for deduplication
            key = (result.package_name, result.vulnerability_id, result.version)
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)
            else:
                # Keep the result with higher confidence
                for i, existing in enumerate(deduplicated):
                    existing_key = (existing.package_name, existing.vulnerability_id, existing.version)
                    if existing_key == key and result.confidence > existing.confidence:
                        deduplicated[i] = result
                        break
        
        return deduplicated
    
    def _map_safety_severity(self, severity: str) -> str:
        """Map Safety severity to standard levels."""
        mapping = {
            'high': 'HIGH',
            'medium': 'MEDIUM', 
            'low': 'LOW'
        }
        return mapping.get(severity.lower(), 'UNKNOWN')
    
    def _map_pip_audit_severity(self, vuln: Dict[str, Any]) -> str:
        """Map pip-audit severity to standard levels."""
        # pip-audit doesn't always provide severity, try to infer
        aliases = vuln.get('aliases', [])
        
        # Look for CVE scores or other indicators
        for alias in aliases:
            if 'CVE-' in alias:
                return 'HIGH'  # CVEs are generally high priority
        
        return 'MEDIUM'
    
    def _map_bandit_severity(self, severity: str) -> str:
        """Map Bandit severity to standard levels."""
        mapping = {
            'high': 'HIGH',
            'medium': 'MEDIUM',
            'low': 'LOW'
        }
        return mapping.get(severity.lower(), 'MEDIUM')
    
    def _map_semgrep_severity(self, severity: str) -> str:
        """Map Semgrep severity to standard levels."""
        mapping = {
            'error': 'HIGH',
            'warning': 'MEDIUM',
            'info': 'LOW'
        }
        return mapping.get(severity.lower(), 'MEDIUM')
    
    def convert_to_findings(self, results: List[VulnerabilityResult]) -> List[Finding]:
        """Convert vulnerability results to Finding objects."""
        findings = []
        
        for result in results:
            severity_map = {
                'CRITICAL': Severity.CRITICAL,
                'HIGH': Severity.HIGH,
                'MEDIUM': Severity.MEDIUM,
                'LOW': Severity.LOW,
                'UNKNOWN': Severity.INFO
            }
            
            finding = Finding(
                title=f"{result.tool.upper()}: {result.title}",
                severity=severity_map.get(result.severity, Severity.MEDIUM),
                description=result.description,
                cve_ids=[result.vulnerability_id] if result.vulnerability_id else [],
                remediation=f"Upgrade {result.package_name} to {result.fix_version}" if result.fix_version else "Update to latest version",
                references=result.references,
                confidence=result.confidence,
                metadata={
                    'tool': result.tool,
                    'package_name': result.package_name,
                    'version': result.version,
                    'fix_version': result.fix_version
                }
            )
            
            findings.append(finding)
        
        return findings


# Global instance
professional_scanner = ProfessionalVulnerabilityScanner()
