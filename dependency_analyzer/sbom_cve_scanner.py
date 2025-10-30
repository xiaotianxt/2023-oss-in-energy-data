"""SBOM-based CVE Scanner with hybrid fallback.

Scans CVEs using SBOM files (fast, accurate) with fallback to
dependencies.db. Uses dynamic programming for maximum efficiency.
"""

import logging
import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import time

from sbom_scraper import SBOMScraperDP, get_sbom_scraper
from cve_scanner import CVEScanner
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class SBOMCVEScannerDP:
    """SBOM-based CVE scanner with DP optimization and hybrid fallback."""

    def __init__(self, github_token: Optional[str] = None):
        """Initialize SBOM CVE scanner.

        Args:
            github_token: GitHub API token (optional but recommended)
        """
        self.sbom_scraper = get_sbom_scraper(github_token)
        self.cve_scanner = CVEScanner()

        # DP cache for package CVE lookups
        self.package_cve_cache: Dict[Tuple[str, str, Optional[str]], List[Dict]] = {}

    def scan_project_sbom(self, project_data: Dict[str, Any],
                         force_refresh: bool = False) -> Dict[str, Any]:
        """Scan a project using SBOM (primary) with fallback to dependencies.db.

        Args:
            project_data: Project dictionary with 'id', 'url', 'name'
            force_refresh: Force re-fetch SBOM and re-scan CVEs

        Returns:
            Scan results with CVEs found
        """
        project_id = project_data['id']
        project_name = project_data['name']
        project_url = project_data['url']

        logger.info(f"Scanning project: {project_name} ({project_url})")

        results = {
            'project_id': project_id,
            'project_name': project_name,
            'project_url': project_url,
            'scan_method': None,
            'dependencies': [],
            'cves_found': [],
            'cve_count': 0,
            'unique_packages_with_cves': 0,
            'severity_breakdown': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'UNKNOWN': 0},
        }

        # Step 1: Try SBOM scraping (FAST + ACCURATE)
        sbom_data = self.sbom_scraper.fetch_sbom_for_project(project_data, force_refresh)

        if sbom_data and sbom_data['dependencies']:
            logger.info(f"Using SBOM data for {project_name} ({len(sbom_data['dependencies'])} deps)")
            results['scan_method'] = 'sbom'
            results['dependencies'] = sbom_data['dependencies']
        else:
            # Step 2: Fallback to dependencies.db (LEGACY)
            logger.info(f"No SBOM found for {project_name}, falling back to dependencies.db")
            results['scan_method'] = 'database_fallback'
            results['dependencies'] = self._get_dependencies_from_db(project_id)

        if not results['dependencies']:
            logger.warning(f"No dependencies found for {project_name}")
            return results

        # Step 3: Scan all dependencies for CVEs (with DP caching)
        logger.info(f"Scanning {len(results['dependencies'])} dependencies for CVEs")

        packages_with_cves = set()

        for dep in results['dependencies']:
            package_name = dep['package_name']
            ecosystem = dep['ecosystem']
            exact_version = dep.get('exact_version')

            # DP: Check cache first
            cache_key = (package_name, ecosystem, exact_version)
            if cache_key in self.package_cve_cache:
                cves = self.package_cve_cache[cache_key]
                logger.debug(f"Using cached CVEs for {package_name}")
            else:
                # Query OSV API
                cves = self.cve_scanner.check_osv_api(package_name, ecosystem, exact_version)
                # Cache result (DP)
                self.package_cve_cache[cache_key] = cves

            if cves:
                packages_with_cves.add(package_name)

                for cve in cves:
                    # Convert list fields to strings for database storage
                    affected = cve.get('affected', [])
                    fixed = cve.get('fixed', [])

                    # Handle affected versions (can be list of strings or dicts)
                    if isinstance(affected, list):
                        affected_str = ','.join(str(v) if not isinstance(v, dict) else str(v.get('version', '')) for v in affected)
                    else:
                        affected_str = str(affected) if affected else ''

                    # Handle fixed versions (can be list of strings or dicts)
                    if isinstance(fixed, list):
                        fixed_str = ','.join(str(v) if not isinstance(v, dict) else str(v.get('version', '')) for v in fixed)
                    else:
                        fixed_str = str(fixed) if fixed else ''

                    cve_record = {
                        'cve_id': cve['id'],
                        'package_name': package_name,
                        'ecosystem': ecosystem,
                        'version': exact_version or dep['version_spec'],
                        'severity': cve.get('severity', 'UNKNOWN'),
                        'cvss_score': cve.get('cvss_score'),
                        'description': cve.get('summary', '')[:200],
                        'published': cve.get('published'),
                        'affected_versions': affected_str,
                        'patched_versions': fixed_str,
                    }

                    results['cves_found'].append(cve_record)
                    results['severity_breakdown'][cve_record['severity']] += 1

        results['cve_count'] = len(results['cves_found'])
        results['unique_packages_with_cves'] = len(packages_with_cves)

        logger.info(f"Found {results['cve_count']} CVEs in {project_name}")

        # Save results to database
        self._save_scan_results(results)

        return results

    def _get_dependencies_from_db(self, project_id: int) -> List[Dict[str, Any]]:
        """Get dependencies from database (fallback method)."""
        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT dependency_name as package_name,
                       version_spec,
                       ecosystem,
                       dependency_type
                FROM dependencies
                WHERE project_id = ?
            """, (project_id,))

            deps = []
            for row in cursor.fetchall():
                dep_dict = dict(row)
                # Normalize to SBOM format
                dep_dict['exact_version'] = self._extract_exact_version(dep_dict.get('version_spec', ''))
                dep_dict['is_direct'] = True
                deps.append(dep_dict)

            return deps

    def _extract_exact_version(self, version_spec: str) -> Optional[str]:
        """Extract exact version from version specifier."""
        if not version_spec:
            return None

        import re
        match = re.match(r'^==?\s*([0-9][0-9a-zA-Z\.\-\+]*)', version_spec)
        if match:
            return match.group(1)

        return None

    def _save_scan_results(self, results: Dict[str, Any]):
        """Save scan results to database."""
        project_id = results['project_id']

        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            cursor = conn.cursor()

            # Save CVEs to package_cves table (for caching)
            for cve in results['cves_found']:
                cursor.execute("""
                    INSERT OR IGNORE INTO package_cves
                    (package_name, ecosystem, version_spec, cve_id, severity,
                     cvss_score, description, published_date, affected_versions,
                     patched_versions, reference_urls)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cve['package_name'], cve['ecosystem'], cve['version'],
                    cve['cve_id'], cve['severity'], cve.get('cvss_score'),
                    cve['description'], cve.get('published'),
                    cve.get('affected_versions'), cve.get('patched_versions'),
                    None  # reference_urls
                ))

                # Save to project impact table
                cursor.execute("""
                    INSERT OR IGNORE INTO project_cve_impact
                    (project_id, cve_id, affected_package, ecosystem,
                     is_direct_dependency, severity, cvss_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, cve['cve_id'], cve['package_name'],
                    cve['ecosystem'], True, cve['severity'], cve.get('cvss_score')
                ))

            conn.commit()

    def scan_all_projects_sbom(self, limit: Optional[int] = None,
                               force_refresh: bool = False) -> Dict[str, Any]:
        """Scan all projects using SBOM approach.

        Args:
            limit: Limit number of projects to scan
            force_refresh: Force re-fetch and re-scan

        Returns:
            Summary statistics
        """
        # Get all projects
        projects = self.sbom_scraper.get_all_projects()

        if limit:
            projects = projects[:limit]

        stats = {
            'total_projects': len(projects),
            'projects_scanned': 0,
            'projects_with_cves': 0,
            'sbom_method': 0,
            'fallback_method': 0,
            'total_cves': 0,
            'unique_packages_with_cves': set(),
            'severity_breakdown': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0, 'UNKNOWN': 0},
            'scan_results': [],
        }

        logger.info(f"Starting SBOM-based CVE scan for {len(projects)} projects")
        start_time = time.time()

        for i, project in enumerate(projects, 1):
            logger.info(f"[{i}/{len(projects)}] Scanning {project['name']}")

            try:
                result = self.scan_project_sbom(project, force_refresh)

                stats['projects_scanned'] += 1

                if result['cve_count'] > 0:
                    stats['projects_with_cves'] += 1

                if result['scan_method'] == 'sbom':
                    stats['sbom_method'] += 1
                else:
                    stats['fallback_method'] += 1

                stats['total_cves'] += result['cve_count']

                for cve in result['cves_found']:
                    stats['unique_packages_with_cves'].add((cve['package_name'], cve['ecosystem']))
                    stats['severity_breakdown'][cve['severity']] += 1

                stats['scan_results'].append({
                    'project_name': project['name'],
                    'project_url': project['url'],
                    'scan_method': result['scan_method'],
                    'cve_count': result['cve_count'],
                    'dependency_count': len(result['dependencies']),
                })

            except Exception as e:
                logger.error(f"Error scanning {project['name']}: {e}")
                continue

            # Progress update every 10 projects
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (len(projects) - i) / rate if rate > 0 else 0
                logger.info(f"Progress: {i}/{len(projects)} projects, "
                          f"{stats['total_cves']} CVEs found, "
                          f"ETA: {remaining/60:.1f} min")

        elapsed = time.time() - start_time
        stats['unique_packages_with_cves'] = len(stats['unique_packages_with_cves'])
        stats['elapsed_time_seconds'] = elapsed
        stats['elapsed_time_minutes'] = elapsed / 60

        logger.info(f"SBOM CVE scan complete in {elapsed/60:.1f} minutes")
        logger.info(f"Results: {stats['total_cves']} CVEs found across "
                   f"{stats['projects_with_cves']} projects")

        return stats

    def generate_sbom_report(self, stats: Dict[str, Any], output_path: str):
        """Generate comprehensive SBOM scan report.

        Args:
            stats: Statistics from scan_all_projects_sbom
            output_path: Path to save report (JSON)
        """
        report = {
            'scan_date': datetime.now().isoformat(),
            'scan_type': 'sbom_based_cve_scan',
            'summary': {
                'total_projects': stats['total_projects'],
                'projects_scanned': stats['projects_scanned'],
                'projects_with_vulnerabilities': stats['projects_with_cves'],
                'vulnerability_rate': f"{stats['projects_with_cves'] / stats['projects_scanned'] * 100:.1f}%"
                                     if stats['projects_scanned'] > 0 else "0%",
                'total_cves_found': stats['total_cves'],
                'unique_vulnerable_packages': stats['unique_packages_with_cves'],
                'scan_time_minutes': stats['elapsed_time_minutes'],
            },
            'methodology': {
                'sbom_primary': stats['sbom_method'],
                'database_fallback': stats['fallback_method'],
                'sbom_coverage': f"{stats['sbom_method'] / stats['projects_scanned'] * 100:.1f}%"
                                if stats['projects_scanned'] > 0 else "0%",
            },
            'severity_breakdown': stats['severity_breakdown'],
            'top_at_risk_projects': sorted(
                stats['scan_results'],
                key=lambda x: x['cve_count'],
                reverse=True
            )[:20],
            'projects_by_scan_method': {
                'sbom': [p for p in stats['scan_results'] if p['scan_method'] == 'sbom'],
                'fallback': [p for p in stats['scan_results'] if p['scan_method'] == 'database_fallback'],
            },
        }

        # Save report
        output_file = Path(output_path)
        output_file.parent.mkdir(exist_ok=True, parents=True)

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"SBOM scan report saved to {output_path}")

        return report


# Singleton instance
sbom_cve_scanner: Optional[SBOMCVEScannerDP] = None


def get_sbom_cve_scanner(github_token: Optional[str] = None) -> SBOMCVEScannerDP:
    """Get or create singleton SBOM CVE scanner instance."""
    global sbom_cve_scanner

    if sbom_cve_scanner is None:
        sbom_cve_scanner = SBOMCVEScannerDP(github_token)

    return sbom_cve_scanner
