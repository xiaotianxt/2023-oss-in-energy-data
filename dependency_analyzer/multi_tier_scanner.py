"""
Multi-Tiered CVE Scanner with comprehensive fallback strategy.

This scanner implements a 4-tier approach:
1. GitHub's automatically generated SBOM API (requires GITHUB_TOKEN - not yet activated)
2. Raw lockfile scraping from repositories (SBOM files)
3. Oct 28 methodology (recursive dependency resolution)
4. Database fallback (cached results)

Supports:
- Python-only scanning (optimized for PyPI ecosystem)
- Multi-language scanning (PyPI, npm, crates, Go, Maven, RubyGems)
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import defaultdict
import json

from database import db
from config import DATABASE_PATH
from cve_scanner import CVEScanner
from sbom_scraper import SBOMScraperDP, get_sbom_scraper
from dependency_resolver import DependencyResolver

logger = logging.getLogger(__name__)


class MultiTierScanner:
    """
    Comprehensive multi-tiered CVE scanner with intelligent fallback.

    Tier 1: GitHub SBOM API (fastest, requires token - NOT YET ACTIVATED)
    Tier 2: Raw SBOM file scraping (fast, accurate versions)
    Tier 3: Recursive dependency resolution (Oct 28 approach - thorough)
    Tier 4: Database fallback (cached historical data)
    """

    def __init__(self, github_token: Optional[str] = None, python_only: bool = False):
        """
        Initialize multi-tier scanner.

        Args:
            github_token: GitHub API token (required for Tier 1 - not yet activated)
            python_only: If True, only scan Python/PyPI packages
        """
        self.github_token = github_token
        self.python_only = python_only
        self.cve_scanner = CVEScanner()
        self.sbom_scraper = get_sbom_scraper(github_token)
        self.dependency_resolver = DependencyResolver()

        # Dynamic Programming cache
        self.package_cve_cache: Dict[tuple, List[Dict]] = {}
        self.dependency_cache: Dict[tuple, List[Dict]] = {}

        # Statistics
        self.stats = {
            'tier1_github_api': 0,  # Not yet activated
            'tier2_sbom_files': 0,
            'tier3_recursive': 0,
            'tier4_database': 0,
            'failed': 0
        }

    def scan_project(self, project_data: Dict[str, Any],
                    force_refresh: bool = False) -> Dict[str, Any]:
        """
        Scan a single project using multi-tiered approach.

        Args:
            project_data: Project information dict with 'name', 'url', 'language'
            force_refresh: Force re-fetching all data

        Returns:
            Dict with scan results including CVEs, dependencies, and tier used
        """
        project_name = project_data.get('name', 'unknown')
        project_url = project_data.get('url', '')
        language = project_data.get('language', 'python').lower()

        logger.info(f"Scanning {project_name} using multi-tier approach")

        # Filter by language if python_only is enabled
        if self.python_only and language != 'python':
            logger.info(f"Skipping {project_name} (language: {language}, python_only mode)")
            return {
                'project_name': project_name,
                'scan_status': 'skipped',
                'reason': f'python_only mode enabled, project language is {language}'
            }

        results = {
            'project_name': project_name,
            'project_url': project_url,
            'language': language,
            'scan_timestamp': datetime.now().isoformat(),
            'tier_used': None,
            'dependencies': [],
            'cves': [],
            'cve_count': 0,
            'scan_status': 'success'
        }

        # Try each tier in order until one succeeds
        dependencies = None

        # TIER 1: GitHub SBOM API (NOT YET ACTIVATED - requires API key)
        # if self.github_token:
        #     dependencies = self._try_github_sbom_api(project_url, force_refresh)
        #     if dependencies:
        #         results['tier_used'] = 'github_sbom_api'
        #         self.stats['tier1_github_api'] += 1

        # TIER 2: Raw SBOM file scraping
        if not dependencies:
            dependencies = self._try_sbom_scraping(project_data, force_refresh)
            if dependencies:
                results['tier_used'] = 'sbom_files'
                self.stats['tier2_sbom_files'] += 1

        # TIER 3: Recursive dependency resolution (Oct 28 methodology)
        if not dependencies:
            dependencies = self._try_recursive_resolution(project_data)
            if dependencies:
                results['tier_used'] = 'recursive_resolution'
                self.stats['tier3_recursive'] += 1

        # TIER 4: Database fallback
        if not dependencies:
            dependencies = self._try_database_fallback(project_data)
            if dependencies:
                results['tier_used'] = 'database_cache'
                self.stats['tier4_database'] += 1

        # If all tiers failed
        if not dependencies:
            logger.warning(f"All tiers failed for {project_name}")
            results['scan_status'] = 'failed'
            results['reason'] = 'No dependencies found via any tier'
            self.stats['failed'] += 1
            return results

        results['dependencies'] = dependencies
        results['dependency_count'] = len(dependencies)

        # Scan dependencies for CVEs with DP optimization
        logger.info(f"Scanning {len(dependencies)} dependencies for CVEs")
        cves = self._scan_dependencies_for_cves(dependencies)
        results['cves'] = cves
        results['cve_count'] = len(cves)

        # Severity breakdown
        severity_counts = defaultdict(int)
        for cve in cves:
            severity_counts[cve.get('severity', 'UNKNOWN')] += 1
        results['severity_breakdown'] = dict(severity_counts)

        logger.info(f"Found {len(cves)} CVEs in {project_name} using tier: {results['tier_used']}")

        return results

    def _try_github_sbom_api(self, project_url: str, force_refresh: bool) -> Optional[List[Dict]]:
        """
        Tier 1: Try GitHub's automatically generated SBOM API.

        NOTE: This feature is NOT YET ACTIVATED. It requires:
        - GitHub API token with appropriate permissions
        - Implementation of GitHub SBOM API calls
        - SBOM may not be available for all repositories

        When activated, this will be the fastest method as GitHub pre-generates SBOMs.
        """
        # TODO: Implement GitHub SBOM API integration
        # This would use: GET /repos/{owner}/{repo}/dependency-graph/sbom
        # Requires: github_token with read permissions
        logger.debug("GitHub SBOM API tier not yet activated")
        return None

    def _try_sbom_scraping(self, project_data: Dict[str, Any],
                          force_refresh: bool) -> Optional[List[Dict]]:
        """
        Tier 2: Scrape raw SBOM files (lockfiles) from repository.

        Fast and accurate - gets exact versions from lockfiles.
        """
        try:
            sbom_data = self.sbom_scraper.fetch_sbom_for_project(project_data, force_refresh)
            if sbom_data and sbom_data.get('dependencies'):
                logger.info(f"Tier 2 success: Found {len(sbom_data['dependencies'])} deps via SBOM scraping")
                return sbom_data['dependencies']
        except Exception as e:
            logger.warning(f"Tier 2 failed: SBOM scraping error: {e}")

        return None

    def _try_recursive_resolution(self, project_data: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Tier 3: Use Oct 28 methodology - recursive dependency resolution.

        Thorough but slower - resolves full transitive dependency tree.
        """
        try:
            project_id = project_data.get('id')
            if not project_id:
                return None

            # Get direct dependencies first
            direct_deps = self._get_direct_dependencies(project_id)
            if not direct_deps:
                return None

            # Resolve transitive dependencies
            all_deps = []
            for dep in direct_deps:
                # Add direct dependency
                all_deps.append({
                    'package_name': dep['package_name'],
                    'version_spec': dep['version_spec'],
                    'ecosystem': dep['ecosystem'],
                    'exact_version': dep.get('exact_version'),
                    'is_direct': True
                })

                # Resolve transitive dependencies (with DP caching)
                cache_key = (dep['package_name'], dep['ecosystem'])
                if cache_key in self.dependency_cache:
                    transitive = self.dependency_cache[cache_key]
                else:
                    transitive = self.dependency_resolver.resolve_transitive(
                        dep['package_name'],
                        dep['ecosystem']
                    )
                    self.dependency_cache[cache_key] = transitive

                for trans_dep in transitive:
                    all_deps.append({
                        'package_name': trans_dep['depends_on_package'],
                        'version_spec': trans_dep.get('depends_on_version', ''),
                        'ecosystem': trans_dep['depends_on_ecosystem'],
                        'exact_version': None,
                        'is_direct': False,
                        'depth': trans_dep.get('dependency_depth', 1)
                    })

            if all_deps:
                logger.info(f"Tier 3 success: Found {len(all_deps)} deps via recursive resolution")
                return all_deps

        except Exception as e:
            logger.warning(f"Tier 3 failed: Recursive resolution error: {e}")

        return None

    def _try_database_fallback(self, project_data: Dict[str, Any]) -> Optional[List[Dict]]:
        """
        Tier 4: Fallback to cached database results.

        Uses historical data from previous scans.
        """
        try:
            project_id = project_data.get('id')
            if not project_id:
                return None

            deps = self._get_direct_dependencies(project_id)
            if deps:
                logger.info(f"Tier 4 success: Found {len(deps)} deps in database cache")
                return deps
        except Exception as e:
            logger.warning(f"Tier 4 failed: Database fallback error: {e}")

        return None

    def _get_direct_dependencies(self, project_id: int) -> List[Dict]:
        """Get direct dependencies from database."""
        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT dependency_name as package_name, version_spec, ecosystem
                FROM dependencies
                WHERE project_id = ?
            """, (project_id,))

            return [dict(row) for row in cursor.fetchall()]

    def _scan_dependencies_for_cves(self, dependencies: List[Dict]) -> List[Dict]:
        """
        Scan all dependencies for CVEs with DP optimization.

        Each unique (package, ecosystem, version) is queried exactly once.
        """
        cves = []
        packages_scanned = set()

        for dep in dependencies:
            package_name = dep['package_name']
            ecosystem = dep['ecosystem']
            exact_version = dep.get('exact_version')

            # Filter by ecosystem if python_only
            if self.python_only and ecosystem.lower() not in ['pypi', 'python']:
                continue

            # DP: Check cache first
            cache_key = (package_name, ecosystem, exact_version)
            if cache_key in self.package_cve_cache:
                package_cves = self.package_cve_cache[cache_key]
                logger.debug(f"Cache hit for {package_name}")
            else:
                # Query OSV API and properly parse response
                raw_cves = self.cve_scanner.check_osv_api(package_name, ecosystem, exact_version)

                # Parse each vulnerability using the proper parser
                package_cves = []
                for vuln in raw_cves:
                    parsed = self._parse_osv_vulnerability(vuln, package_name, ecosystem, exact_version)
                    package_cves.append(parsed)

                # Cache the result (DP)
                self.package_cve_cache[cache_key] = package_cves

            # Add all CVEs for this package
            cves.extend(package_cves)

            if package_cves:
                packages_scanned.add(package_name)

        logger.info(f"Found {len(cves)} total CVEs across {len(packages_scanned)} vulnerable packages")
        return cves

    def _parse_osv_vulnerability(self, vuln_data: Dict[str, Any],
                                package_name: str, ecosystem: str,
                                version: Optional[str]) -> Dict[str, Any]:
        """
        Parse OSV vulnerability data properly.

        Handles complex nested structures from OSV API response.
        """
        cve_id = vuln_data.get('id', 'UNKNOWN')

        # Extract severity - can be nested in multiple ways
        severity = 'UNKNOWN'
        cvss_score = None

        if 'severity' in vuln_data:
            severity_data = vuln_data['severity']
            if isinstance(severity_data, list) and len(severity_data) > 0:
                severity_info = severity_data[0]
                severity = severity_info.get('type', 'UNKNOWN')
                if 'score' in severity_info:
                    cvss_score = severity_info['score']

        # Extract affected versions from 'affected' array
        affected_versions = []
        fixed_versions = []

        for affected in vuln_data.get('affected', []):
            if 'ranges' in affected:
                for range_info in affected['ranges']:
                    events = range_info.get('events', [])
                    for event in events:
                        if 'introduced' in event:
                            affected_versions.append(f">={event['introduced']}")
                        if 'fixed' in event:
                            fixed_versions.append(event['fixed'])

        # Extract reference URLs - handle various structures
        reference_urls = []
        for ref in vuln_data.get('references', []):
            if isinstance(ref, dict) and 'url' in ref:
                reference_urls.append(ref['url'])
            elif isinstance(ref, str):
                reference_urls.append(ref)

        return {
            'cve_id': cve_id,
            'package_name': package_name,
            'ecosystem': ecosystem,
            'version': version or 'any',
            'severity': severity,
            'cvss_score': cvss_score,
            'description': vuln_data.get('summary', vuln_data.get('details', ''))[:500],
            'published': vuln_data.get('published', ''),
            'affected_versions': ', '.join(affected_versions) if affected_versions else 'Not specified',
            'patched_versions': ', '.join(fixed_versions) if fixed_versions else 'Not specified',
            'reference_urls': ', '.join(reference_urls[:3]) if reference_urls else ''  # Limit to 3 URLs
        }

    def scan_all_projects(self, limit: Optional[int] = None,
                         force_refresh: bool = False) -> Dict[str, Any]:
        """
        Scan all projects using multi-tier approach.

        Args:
            limit: Limit number of projects to scan
            force_refresh: Force refresh all data

        Returns:
            Comprehensive scan report with statistics
        """
        # Get projects from database
        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT id, name, url, language FROM projects"
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            projects = [dict(row) for row in cursor.fetchall()]

        logger.info(f"Starting multi-tier scan of {len(projects)} projects")
        if self.python_only:
            logger.info("Python-only mode enabled - skipping non-Python projects")

        scan_results = []
        total_cves = 0
        projects_with_cves = 0

        for i, project in enumerate(projects, 1):
            logger.info(f"[{i}/{len(projects)}] Scanning {project['name']}")

            try:
                result = self.scan_project(project, force_refresh)
                scan_results.append(result)

                if result.get('cve_count', 0) > 0:
                    projects_with_cves += 1
                    total_cves += result['cve_count']

            except Exception as e:
                logger.error(f"Error scanning {project['name']}: {e}")
                scan_results.append({
                    'project_name': project['name'],
                    'scan_status': 'error',
                    'error': str(e)
                })
                self.stats['failed'] += 1

        # Generate summary report
        report = {
            'scan_timestamp': datetime.now().isoformat(),
            'scan_mode': 'python_only' if self.python_only else 'multi_language',
            'total_projects': len(projects),
            'projects_scanned': len([r for r in scan_results if r.get('scan_status') != 'skipped']),
            'projects_with_vulnerabilities': projects_with_cves,
            'total_cves_found': total_cves,
            'tier_statistics': dict(self.stats),
            'project_results': scan_results
        }

        logger.info(f"\nScan complete!")
        logger.info(f"Projects scanned: {report['projects_scanned']}/{report['total_projects']}")
        logger.info(f"Total CVEs found: {total_cves}")
        logger.info(f"Tier usage: {dict(self.stats)}")

        return report

    def get_statistics(self) -> Dict[str, Any]:
        """Get current scan statistics."""
        return {
            'tier_usage': dict(self.stats),
            'cache_sizes': {
                'cve_cache': len(self.package_cve_cache),
                'dependency_cache': len(self.dependency_cache)
            }
        }


# Singleton instances
_python_scanner = None
_multi_lang_scanner = None


def get_python_scanner(github_token: Optional[str] = None) -> MultiTierScanner:
    """Get or create Python-only multi-tier scanner."""
    global _python_scanner
    if _python_scanner is None:
        _python_scanner = MultiTierScanner(github_token=github_token, python_only=True)
    return _python_scanner


def get_multi_language_scanner(github_token: Optional[str] = None) -> MultiTierScanner:
    """Get or create multi-language multi-tier scanner."""
    global _multi_lang_scanner
    if _multi_lang_scanner is None:
        _multi_lang_scanner = MultiTierScanner(github_token=github_token, python_only=False)
    return _multi_lang_scanner
