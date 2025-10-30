"""Impact analysis combining CVE scanning and dependency resolution."""

import logging
import sqlite3
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path

from database import db
from config import DATABASE_PATH
from cve_scanner import CVEScanner
from dependency_resolver import DependencyResolver

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Analyzes the impact of CVEs across the dependency tree.

    This class combines CVE scanning with recursive dependency resolution
    to determine which projects are affected by vulnerabilities in their
    direct and transitive dependencies.
    """

    def __init__(self, max_depth: int = 3):
        self.db_path = DATABASE_PATH
        self.cve_scanner = CVEScanner()
        self.dependency_resolver = DependencyResolver(max_depth=max_depth)

    def analyze_project_full_impact(self, project_id: int,
                                    resolve_transitive: bool = True,
                                    scan_cves: bool = True) -> Dict[str, Any]:
        """
        Perform complete impact analysis for a project.

        Steps:
        1. Get all direct dependencies
        2. Resolve transitive dependencies (if enabled)
        3. Scan all dependencies for CVEs (if enabled)
        4. Build impact report

        Args:
            project_id: Database ID of the project
            resolve_transitive: Whether to resolve transitive dependencies
            scan_cves: Whether to scan for CVEs

        Returns:
            Comprehensive impact analysis report
        """
        logger.info(f"Starting full impact analysis for project {project_id}")

        # Get project info
        project_info = self._get_project_info(project_id)
        if not project_info:
            return {'error': f'Project {project_id} not found'}

        # Get direct dependencies
        direct_deps = self._get_direct_dependencies(project_id)
        logger.info(f"Found {len(direct_deps)} direct dependencies")

        # Resolve transitive dependencies
        all_dependencies = set()
        transitive_map = defaultdict(list)

        if resolve_transitive:
            logger.info("Resolving transitive dependencies...")
            for dep in direct_deps:
                # Add direct dependency
                all_dependencies.add((dep['dependency_name'], dep['ecosystem']))

                # Resolve transitive
                transitive = self.dependency_resolver.get_all_transitive_dependencies(
                    dep['dependency_name'],
                    dep['ecosystem']
                )

                for trans_dep in transitive:
                    all_dependencies.add((
                        trans_dep['package_name'],
                        trans_dep['ecosystem']
                    ))
                    transitive_map[dep['dependency_name']].append(trans_dep)

            logger.info(f"Total dependencies (including transitive): {len(all_dependencies)}")
        else:
            all_dependencies = {(d['dependency_name'], d['ecosystem']) for d in direct_deps}

        # Scan for CVEs
        cve_results = []
        packages_with_cves = 0
        total_cves = 0

        if scan_cves:
            logger.info("Scanning dependencies for CVEs...")
            for package_name, ecosystem in all_dependencies:
                cves = self.cve_scanner.scan_package(package_name, ecosystem)

                if cves:
                    packages_with_cves += 1
                    total_cves += len(cves)

                    for cve in cves:
                        # Determine if this is a direct or transitive dependency
                        is_direct = any(
                            d['dependency_name'] == package_name and d['ecosystem'] == ecosystem
                            for d in direct_deps
                        )

                        # Find dependency path
                        dep_path = self._find_dependency_path(
                            package_name,
                            ecosystem,
                            direct_deps,
                            transitive_map
                        )

                        cve_result = {
                            'cve_id': cve['cve_id'],
                            'package_name': package_name,
                            'ecosystem': ecosystem,
                            'severity': cve['severity'],
                            'cvss_score': cve['cvss_score'],
                            'description': cve['description'],
                            'is_direct_dependency': is_direct,
                            'dependency_path': dep_path,
                            'published_date': cve['published_date']
                        }

                        cve_results.append(cve_result)

                        # Store in database
                        self._store_project_impact(project_id, cve_result)

            logger.info(f"Found {total_cves} CVEs in {packages_with_cves} packages")

        # Build report
        report = {
            'project_id': project_id,
            'project_name': project_info['name'],
            'project_url': project_info['url'],
            'analysis_timestamp': datetime.now().isoformat(),
            'summary': {
                'direct_dependencies': len(direct_deps),
                'total_dependencies': len(all_dependencies),
                'transitive_dependencies': len(all_dependencies) - len(direct_deps),
                'packages_with_cves': packages_with_cves,
                'total_cves': total_cves
            },
            'dependencies': {
                'direct': [
                    {
                        'name': d['dependency_name'],
                        'ecosystem': d['ecosystem'],
                        'version': d.get('version_spec', '')
                    }
                    for d in direct_deps
                ],
                'all': [
                    {'name': pkg, 'ecosystem': eco}
                    for pkg, eco in all_dependencies
                ]
            },
            'vulnerabilities': cve_results,
            'severity_breakdown': self._calculate_severity_breakdown(cve_results),
            'high_risk_dependencies': self._identify_high_risk_deps(cve_results)
        }

        return report

    def _get_project_info(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get basic project information."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def _get_direct_dependencies(self, project_id: int) -> List[Dict[str, Any]]:
        """Get direct dependencies for a project."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dependency_name, ecosystem, version_spec, dependency_type
                FROM dependencies
                WHERE project_id = ?
            """, (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def _find_dependency_path(self, package_name: str, ecosystem: str,
                             direct_deps: List[Dict[str, Any]],
                             transitive_map: Dict[str, List[Dict[str, Any]]]) -> str:
        """Find the dependency path from root to this package."""
        # Check if it's a direct dependency
        for dep in direct_deps:
            if dep['dependency_name'] == package_name and dep['ecosystem'] == ecosystem:
                return package_name

        # Search through transitive dependencies
        for root_dep_name, transitive_deps in transitive_map.items():
            for trans_dep in transitive_deps:
                if (trans_dep['package_name'] == package_name and
                    trans_dep['ecosystem'] == ecosystem):
                    return f"{root_dep_name} → {package_name}"

        return package_name

    def _store_project_impact(self, project_id: int, cve_result: Dict[str, Any]):
        """Store CVE impact in the database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO project_cve_impact
                (project_id, cve_id, affected_package, ecosystem, is_direct_dependency,
                 dependency_path, severity, cvss_score, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                cve_result['cve_id'],
                cve_result['package_name'],
                cve_result['ecosystem'],
                cve_result['is_direct_dependency'],
                cve_result['dependency_path'],
                cve_result['severity'],
                cve_result['cvss_score'],
                datetime.now().isoformat()
            ))
            conn.commit()

    def _calculate_severity_breakdown(self, cve_results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate breakdown of CVEs by severity."""
        breakdown = defaultdict(int)
        for cve in cve_results:
            severity = cve.get('severity', 'UNKNOWN')
            breakdown[severity] += 1
        return dict(breakdown)

    def _identify_high_risk_deps(self, cve_results: List[Dict[str, Any]],
                                 top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify dependencies with the most/highest severity CVEs."""
        dep_risk = defaultdict(lambda: {'cve_count': 0, 'max_cvss': 0, 'cves': []})

        for cve in cve_results:
            key = f"{cve['package_name']} ({cve['ecosystem']})"
            dep_risk[key]['cve_count'] += 1
            dep_risk[key]['cves'].append(cve['cve_id'])

            cvss_score = cve.get('cvss_score', 0)
            if cvss_score and cvss_score > dep_risk[key]['max_cvss']:
                dep_risk[key]['max_cvss'] = cvss_score

        # Sort by CVE count and max CVSS score
        high_risk = sorted(
            [
                {
                    'dependency': dep,
                    'cve_count': data['cve_count'],
                    'max_cvss_score': data['max_cvss'],
                    'cves': data['cves']
                }
                for dep, data in dep_risk.items()
            ],
            key=lambda x: (x['cve_count'], x['max_cvss_score']),
            reverse=True
        )[:top_n]

        return high_risk

    def analyze_all_projects(self, resolve_transitive: bool = True,
                           scan_cves: bool = True) -> Dict[str, Any]:
        """
        Analyze all projects in the database.

        Args:
            resolve_transitive: Whether to resolve transitive dependencies
            scan_cves: Whether to scan for CVEs

        Returns:
            Summary of analysis across all projects
        """
        # Get all projects
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM projects")
            projects = cursor.fetchall()

        logger.info(f"Analyzing {len(projects)} projects...")

        results = []
        total_cves = 0
        projects_with_cves = 0

        for i, (project_id, project_name) in enumerate(projects, 1):
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(projects)} projects analyzed")

            try:
                report = self.analyze_project_full_impact(
                    project_id,
                    resolve_transitive=resolve_transitive,
                    scan_cves=scan_cves
                )

                project_cve_count = report.get('summary', {}).get('total_cves', 0)
                total_cves += project_cve_count

                if project_cve_count > 0:
                    projects_with_cves += 1
                    logger.warning(f"⚠️  {project_name}: {project_cve_count} CVEs found")

                results.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'cve_count': project_cve_count,
                    'high_risk_count': len([
                        cve for cve in report.get('vulnerabilities', [])
                        if cve.get('severity') in ['HIGH', 'CRITICAL']
                    ])
                })

            except Exception as e:
                logger.error(f"Error analyzing project {project_name}: {e}")
                results.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'error': str(e)
                })

        # Calculate statistics
        summary = {
            'total_projects': len(projects),
            'projects_with_cves': projects_with_cves,
            'total_cves_found': total_cves,
            'average_cves_per_project': total_cves / len(projects) if projects else 0,
            'projects': sorted(results, key=lambda x: x.get('cve_count', 0), reverse=True)
        }

        return summary

    def find_cve_downstream_impact(self, cve_id: str) -> Dict[str, Any]:
        """
        Find all projects affected by a specific CVE.

        This performs reverse impact analysis - given a CVE,
        find all projects that use the affected package.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2023-1234" or OSV ID)

        Returns:
            Report of all affected projects
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get CVE details
            cursor.execute("""
                SELECT * FROM package_cves WHERE cve_id = ? LIMIT 1
            """, (cve_id,))
            cve_info = cursor.fetchone()

            if not cve_info:
                return {'error': f'CVE {cve_id} not found in database'}

            cve_info = dict(cve_info)

            # Find all projects affected
            cursor.execute("""
                SELECT p.id, p.name, p.url, pci.affected_package, pci.ecosystem,
                       pci.is_direct_dependency, pci.dependency_path, pci.severity
                FROM project_cve_impact pci
                JOIN projects p ON pci.project_id = p.id
                WHERE pci.cve_id = ?
                ORDER BY p.name
            """, (cve_id,))

            affected_projects = [dict(row) for row in cursor.fetchall()]

        return {
            'cve_id': cve_id,
            'package': cve_info['package_name'],
            'ecosystem': cve_info['ecosystem'],
            'severity': cve_info['severity'],
            'cvss_score': cve_info['cvss_score'],
            'description': cve_info['description'],
            'affected_project_count': len(affected_projects),
            'affected_projects': affected_projects
        }

    def export_report(self, output_path: Path, format: str = 'json'):
        """
        Export complete vulnerability report.

        Args:
            output_path: Path to output file
            format: Export format ('json' or 'csv')
        """
        # Get all project impacts
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT p.name as project_name, p.url, p.category,
                       pci.cve_id, pci.affected_package, pci.ecosystem,
                       pci.is_direct_dependency, pci.dependency_path,
                       pci.severity, pci.cvss_score
                FROM project_cve_impact pci
                JOIN projects p ON pci.project_id = p.id
                ORDER BY pci.severity DESC, pci.cvss_score DESC
            """)

            data = [dict(row) for row in cursor.fetchall()]

        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported {len(data)} CVE impacts to {output_path}")

        elif format == 'csv':
            import csv
            with open(output_path, 'w', newline='') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            logger.info(f"Exported {len(data)} CVE impacts to {output_path}")


def main():
    """Main function for impact analysis."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    analyzer = ImpactAnalyzer(max_depth=2)

    print("="*60)
    print("DEPENDENCY & CVE IMPACT ANALYSIS")
    print("="*60)

    # Get first project for demo
    with sqlite3.connect(str(DATABASE_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM projects LIMIT 1")
        result = cursor.fetchone()

    if result:
        project_id, project_name = result
        print(f"\nAnalyzing project: {project_name} (ID: {project_id})")

        report = analyzer.analyze_project_full_impact(
            project_id,
            resolve_transitive=True,
            scan_cves=True
        )

        print("\nSummary:")
        print(f"  Direct dependencies: {report['summary']['direct_dependencies']}")
        print(f"  Total dependencies: {report['summary']['total_dependencies']}")
        print(f"  Transitive dependencies: {report['summary']['transitive_dependencies']}")
        print(f"  Packages with CVEs: {report['summary']['packages_with_cves']}")
        print(f"  Total CVEs: {report['summary']['total_cves']}")

        if report['summary']['total_cves'] > 0:
            print("\nSeverity Breakdown:")
            for severity, count in report['severity_breakdown'].items():
                print(f"  {severity}: {count}")

            print("\nHigh Risk Dependencies:")
            for dep in report['high_risk_dependencies'][:5]:
                print(f"  {dep['dependency']}: {dep['cve_count']} CVEs (max CVSS: {dep['max_cvss_score']})")

        # Export report
        output_path = Path("vulnerability_report.json")
        analyzer.export_report(output_path)
        print(f"\nFull report exported to {output_path}")


if __name__ == "__main__":
    main()
