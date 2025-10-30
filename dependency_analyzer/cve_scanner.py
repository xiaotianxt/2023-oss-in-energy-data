"""CVE scanning and vulnerability detection for dependencies."""

import logging
import requests
import sqlite3
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import json
from pathlib import Path

from database import db
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class CVEScanner:
    """Scanner for detecting CVEs in package dependencies."""

    def __init__(self, cache_duration_hours: int = 24):
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.db_path = DATABASE_PATH
        self._init_cve_tables()

    def _init_cve_tables(self):
        """Initialize CVE-related tables in database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS package_cves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_name TEXT NOT NULL,
                    ecosystem TEXT NOT NULL,
                    version_spec TEXT,
                    cve_id TEXT NOT NULL,
                    severity TEXT,
                    cvss_score REAL,
                    description TEXT,
                    published_date TEXT,
                    affected_versions TEXT,
                    patched_versions TEXT,
                    reference_urls TEXT,
                    checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(package_name, ecosystem, cve_id)
                );

                CREATE TABLE IF NOT EXISTS transitive_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_name TEXT NOT NULL,
                    ecosystem TEXT NOT NULL,
                    version_spec TEXT,
                    depends_on_package TEXT NOT NULL,
                    depends_on_ecosystem TEXT NOT NULL,
                    depends_on_version TEXT,
                    dependency_depth INTEGER DEFAULT 1,
                    resolved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(package_name, ecosystem, depends_on_package, depends_on_ecosystem)
                );

                CREATE TABLE IF NOT EXISTS project_cve_impact (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    cve_id TEXT NOT NULL,
                    affected_package TEXT NOT NULL,
                    ecosystem TEXT NOT NULL,
                    is_direct_dependency BOOLEAN DEFAULT 0,
                    dependency_path TEXT,
                    severity TEXT,
                    cvss_score REAL,
                    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    UNIQUE(project_id, cve_id, affected_package)
                );

                CREATE INDEX IF NOT EXISTS idx_package_cves_package ON package_cves(package_name, ecosystem);
                CREATE INDEX IF NOT EXISTS idx_transitive_deps_package ON transitive_dependencies(package_name, ecosystem);
                CREATE INDEX IF NOT EXISTS idx_transitive_deps_depends ON transitive_dependencies(depends_on_package, depends_on_ecosystem);
                CREATE INDEX IF NOT EXISTS idx_project_cve_impact_project ON project_cve_impact(project_id);
                CREATE INDEX IF NOT EXISTS idx_project_cve_impact_cve ON project_cve_impact(cve_id);
            """)
            conn.commit()

    def check_osv_api(self, package_name: str, ecosystem: str,
                      version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Check OSV (Open Source Vulnerabilities) API for CVEs.

        OSV provides vulnerability data for multiple ecosystems:
        - PyPI (Python)
        - npm (JavaScript)
        - Maven (Java)
        - Go
        - crates.io (Rust)
        """
        # Map our ecosystem names to OSV ecosystem names
        ecosystem_mapping = {
            'pypi': 'PyPI',
            'npm': 'npm',
            'maven': 'Maven',
            'go': 'Go',
            'crates': 'crates.io',
        }

        osv_ecosystem = ecosystem_mapping.get(ecosystem.lower())
        if not osv_ecosystem:
            logger.warning(f"Ecosystem {ecosystem} not supported by OSV API")
            return []

        try:
            url = "https://api.osv.dev/v1/query"

            payload = {
                "package": {
                    "name": package_name,
                    "ecosystem": osv_ecosystem
                }
            }

            # If version is specified, include it
            if version and version.strip():
                # Clean version string
                clean_version = version.strip().lstrip('>=<~^!=')
                if clean_version:
                    payload["version"] = clean_version

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                vulnerabilities = data.get('vulns', [])

                logger.info(f"Found {len(vulnerabilities)} vulnerabilities for {package_name} ({ecosystem})")
                return vulnerabilities
            else:
                logger.warning(f"OSV API returned status {response.status_code} for {package_name}")
                return []

        except requests.RequestException as e:
            logger.error(f"Error querying OSV API for {package_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error checking OSV for {package_name}: {e}")
            return []

    def parse_osv_vulnerability(self, vuln_data: Dict[str, Any],
                               package_name: str, ecosystem: str) -> Dict[str, Any]:
        """Parse OSV vulnerability data into our format."""
        cve_id = vuln_data.get('id', 'UNKNOWN')

        # Extract severity
        severity = 'UNKNOWN'
        cvss_score = None

        if 'severity' in vuln_data:
            severity_data = vuln_data['severity']
            if isinstance(severity_data, list) and len(severity_data) > 0:
                severity_info = severity_data[0]
                severity = severity_info.get('type', 'UNKNOWN')
                cvss_score = severity_info.get('score')

        # Extract affected versions
        affected_versions = []
        for affected in vuln_data.get('affected', []):
            if 'ranges' in affected:
                for range_info in affected['ranges']:
                    events = range_info.get('events', [])
                    for event in events:
                        if 'introduced' in event or 'fixed' in event:
                            affected_versions.append(str(event))

        # Extract reference URLs
        reference_urls = [ref.get('url') for ref in vuln_data.get('references', []) if 'url' in ref]

        return {
            'cve_id': cve_id,
            'package_name': package_name,
            'ecosystem': ecosystem,
            'severity': severity,
            'cvss_score': cvss_score,
            'description': vuln_data.get('summary', vuln_data.get('details', '')),
            'published_date': vuln_data.get('published', ''),
            'affected_versions': json.dumps(affected_versions),
            'patched_versions': json.dumps(vuln_data.get('database_specific', {}).get('patched_versions', [])),
            'reference_urls': json.dumps(reference_urls)
        }

    def scan_package(self, package_name: str, ecosystem: str,
                    version: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Scan a single package for CVEs.

        Args:
            package_name: Name of the package
            ecosystem: Package ecosystem (pypi, npm, maven, etc.)
            version: Optional version specifier
            force_refresh: Force refresh even if cached

        Returns:
            List of CVE records
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_cves(package_name, ecosystem)
            if cached:
                logger.debug(f"Using cached CVEs for {package_name}")
                return cached

        # Query OSV API
        vulnerabilities = self.check_osv_api(package_name, ecosystem, version)

        # Parse and store results
        cve_records = []
        for vuln in vulnerabilities:
            parsed = self.parse_osv_vulnerability(vuln, package_name, ecosystem)
            cve_records.append(parsed)
            self._cache_cve(parsed)

        # If no vulnerabilities found, mark it as checked
        if not cve_records:
            self._mark_package_checked(package_name, ecosystem)

        return cve_records

    def _get_cached_cves(self, package_name: str, ecosystem: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached CVE data if it's still fresh."""
        cutoff_time = (datetime.now() - self.cache_duration).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM package_cves
                WHERE package_name = ? AND ecosystem = ? AND checked_at > ?
            """, (package_name, ecosystem, cutoff_time))

            rows = cursor.fetchall()
            if rows:
                return [dict(row) for row in rows]

        return None

    def _cache_cve(self, cve_record: Dict[str, Any]):
        """Cache CVE record in database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO package_cves
                (package_name, ecosystem, cve_id, severity, cvss_score,
                 description, published_date, affected_versions, patched_versions, reference_urls, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cve_record['package_name'],
                cve_record['ecosystem'],
                cve_record['cve_id'],
                cve_record['severity'],
                cve_record['cvss_score'],
                cve_record['description'],
                cve_record['published_date'],
                cve_record['affected_versions'],
                cve_record['patched_versions'],
                cve_record['reference_urls'],
                datetime.now().isoformat()
            ))
            conn.commit()

    def _mark_package_checked(self, package_name: str, ecosystem: str):
        """Mark package as checked even if no CVEs found."""
        # We can insert a dummy record or update a separate table
        # For simplicity, we'll skip this for now
        pass

    def scan_all_dependencies(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Scan all dependencies in the database for CVEs.

        Returns:
            Summary of scan results
        """
        # Get all unique dependencies
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT dependency_name, ecosystem
                FROM dependencies
                WHERE dependency_name IS NOT NULL
                ORDER BY dependency_name
            """)
            packages = cursor.fetchall()

        logger.info(f"Scanning {len(packages)} unique packages for CVEs...")

        total_cves = 0
        packages_with_cves = 0

        for i, (package_name, ecosystem) in enumerate(packages, 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(packages)} packages scanned")

            cves = self.scan_package(package_name, ecosystem, force_refresh=force_refresh)

            if cves:
                total_cves += len(cves)
                packages_with_cves += 1
                logger.warning(f"⚠️  {package_name} ({ecosystem}): {len(cves)} CVEs found")

        logger.info(f"Scan complete: {total_cves} CVEs found in {packages_with_cves} packages")

        return {
            'total_packages_scanned': len(packages),
            'packages_with_cves': packages_with_cves,
            'total_cves_found': total_cves
        }

    def analyze_project_impact(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Analyze CVE impact for a specific project.

        Returns list of CVEs affecting the project's dependencies.
        """
        # Get project dependencies
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT dependency_name, ecosystem, version_spec
                FROM dependencies
                WHERE project_id = ?
            """, (project_id,))

            dependencies = [dict(row) for row in cursor.fetchall()]

        # Check each dependency for CVEs
        project_cves = []

        for dep in dependencies:
            cves = self.scan_package(
                dep['dependency_name'],
                dep['ecosystem'],
                dep.get('version_spec')
            )

            for cve in cves:
                impact_record = {
                    'project_id': project_id,
                    'cve_id': cve['cve_id'],
                    'affected_package': cve['package_name'],
                    'ecosystem': cve['ecosystem'],
                    'is_direct_dependency': True,
                    'dependency_path': cve['package_name'],
                    'severity': cve['severity'],
                    'cvss_score': cve['cvss_score']
                }

                project_cves.append(impact_record)
                self._store_project_cve_impact(impact_record)

        return project_cves

    def _store_project_cve_impact(self, impact_record: Dict[str, Any]):
        """Store project CVE impact in database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO project_cve_impact
                (project_id, cve_id, affected_package, ecosystem, is_direct_dependency,
                 dependency_path, severity, cvss_score, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                impact_record['project_id'],
                impact_record['cve_id'],
                impact_record['affected_package'],
                impact_record['ecosystem'],
                impact_record['is_direct_dependency'],
                impact_record['dependency_path'],
                impact_record['severity'],
                impact_record['cvss_score'],
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_cve_summary(self) -> Dict[str, Any]:
        """Get summary of all CVEs in the database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Total CVEs
            cursor.execute("SELECT COUNT(*) FROM package_cves")
            total_cves = cursor.fetchone()[0]

            # CVEs by severity
            cursor.execute("""
                SELECT severity, COUNT(*) as count
                FROM package_cves
                GROUP BY severity
                ORDER BY count DESC
            """)
            severity_dist = dict(cursor.fetchall())

            # Packages with CVEs
            cursor.execute("""
                SELECT COUNT(DISTINCT package_name || ':' || ecosystem)
                FROM package_cves
            """)
            packages_with_cves = cursor.fetchone()[0]

            # Top vulnerable packages
            cursor.execute("""
                SELECT package_name, ecosystem, COUNT(*) as cve_count
                FROM package_cves
                GROUP BY package_name, ecosystem
                ORDER BY cve_count DESC
                LIMIT 10
            """)
            top_vulnerable = cursor.fetchall()

        return {
            'total_cves': total_cves,
            'packages_with_cves': packages_with_cves,
            'severity_distribution': severity_dist,
            'top_vulnerable_packages': [
                {'package': f"{name} ({eco})", 'cve_count': count}
                for name, eco, count in top_vulnerable
            ]
        }


def main():
    """Main function for CVE scanning."""
    logging.basicConfig(level=logging.INFO)

    scanner = CVEScanner()

    # Scan all dependencies
    print("="*60)
    print("CVE SCANNING")
    print("="*60)
    print("\nScanning all dependencies for vulnerabilities...")

    results = scanner.scan_all_dependencies()

    print(f"\nScan Results:")
    print(f"  Total packages scanned: {results['total_packages_scanned']}")
    print(f"  Packages with CVEs: {results['packages_with_cves']}")
    print(f"  Total CVEs found: {results['total_cves_found']}")

    # Get summary
    summary = scanner.get_cve_summary()

    print(f"\nCVE Summary:")
    print(f"  Total unique CVEs: {summary['total_cves']}")
    print(f"  Affected packages: {summary['packages_with_cves']}")

    print(f"\nSeverity Distribution:")
    for severity, count in summary['severity_distribution'].items():
        print(f"  {severity}: {count}")

    print(f"\nTop 10 Most Vulnerable Packages:")
    for pkg_info in summary['top_vulnerable_packages']:
        print(f"  {pkg_info['package']}: {pkg_info['cve_count']} CVEs")


if __name__ == "__main__":
    main()
