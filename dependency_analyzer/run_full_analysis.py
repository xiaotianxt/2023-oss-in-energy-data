"""
Complete Deep CVE Analysis Script

This script performs a comprehensive, deep analysis of all dependencies:
1. Scans ALL unique packages for CVEs (not just top 20)
2. Resolves transitive dependencies for each project
3. Analyzes CVE impact project-by-project
4. Generates detailed reports with severity breakdowns
5. Creates vulnerability matrices
6. Exports comprehensive CSV and JSON reports

Expected runtime: 2-4 hours for full scan
"""

import sys
import logging
import sqlite3
import json
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import time

sys.path.insert(0, str(Path(__file__).parent))

from cve_scanner import CVEScanner
from dependency_resolver import DependencyResolverOptimized
from impact_analyzer import ImpactAnalyzer
from database import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class FullAnalysisRunner:
    """Runs complete deep analysis with all features."""

    def __init__(self, output_dir='full_analysis_results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.scanner = CVEScanner()
        self.resolver = DependencyResolverOptimized(max_depth=3)
        self.impact_analyzer = ImpactAnalyzer(max_depth=3)

        self.results = {
            'scan_start_time': datetime.now().isoformat(),
            'configuration': {
                'max_depth': 3,
                'full_scan': True,
                'resolve_transitive': True
            }
        }

    def step1_scan_all_packages(self, force_refresh=False):
        """
        STEP 1: Scan ALL unique packages for CVEs (not just top 20)

        This is the comprehensive scan that covers all 1,559 packages.
        Expected time: 1-2 hours
        """
        logger.info("="*70)
        logger.info("STEP 1: Scanning ALL packages for CVEs")
        logger.info("="*70)

        conn = sqlite3.connect(str(self.scanner.db_path))
        cursor = conn.cursor()

        # Get ALL unique packages
        cursor.execute("""
            SELECT DISTINCT dependency_name, ecosystem
            FROM dependencies
            WHERE dependency_name IS NOT NULL
            ORDER BY dependency_name
        """)
        all_packages = cursor.fetchall()
        total_packages = len(all_packages)

        logger.info(f"Total unique packages to scan: {total_packages}")
        logger.info(f"Estimated time: {total_packages * 1.5 / 60:.1f} minutes")
        logger.info("")

        results = []
        packages_with_cves = 0
        total_cves = 0

        start_time = time.time()

        for i, (package_name, ecosystem) in enumerate(all_packages, 1):
            # Progress update every 50 packages
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total_packages - i) / rate
                logger.info(f"Progress: {i}/{total_packages} ({i/total_packages*100:.1f}%) - "
                          f"ETA: {remaining/60:.1f} minutes")

            try:
                cves = self.scanner.scan_package(
                    package_name,
                    ecosystem,
                    force_refresh=force_refresh
                )

                if cves:
                    packages_with_cves += 1
                    total_cves += len(cves)
                    logger.info(f"  ⚠️  {package_name} ({ecosystem}): {len(cves)} CVEs")

                results.append({
                    'package': package_name,
                    'ecosystem': ecosystem,
                    'cve_count': len(cves),
                    'cves': [
                        {
                            'cve_id': cve['cve_id'],
                            'severity': cve['severity'],
                            'cvss_score': cve.get('cvss_score'),
                            'description': cve['description'][:200] + '...' if len(cve['description']) > 200 else cve['description']
                        }
                        for cve in cves
                    ]
                })

            except Exception as e:
                logger.error(f"  ✗ Error scanning {package_name}: {e}")
                results.append({
                    'package': package_name,
                    'ecosystem': ecosystem,
                    'error': str(e)
                })

        elapsed_time = time.time() - start_time

        logger.info("")
        logger.info("="*70)
        logger.info("STEP 1 COMPLETE")
        logger.info("="*70)
        logger.info(f"Total packages scanned: {total_packages}")
        logger.info(f"Packages with CVEs: {packages_with_cves}")
        logger.info(f"Total CVEs found: {total_cves}")
        logger.info(f"Time taken: {elapsed_time/60:.1f} minutes")
        logger.info("")

        # Save detailed results
        output_file = self.output_dir / 'step1_all_packages_cves.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_packages': total_packages,
                'packages_with_cves': packages_with_cves,
                'total_cves': total_cves,
                'scan_duration_seconds': elapsed_time,
                'packages': results
            }, f, indent=2)

        logger.info(f"Detailed results saved to: {output_file}")

        self.results['step1'] = {
            'total_packages': total_packages,
            'packages_with_cves': packages_with_cves,
            'total_cves': total_cves,
            'duration_seconds': elapsed_time
        }

        return results

    def step2_resolve_transitive_dependencies(self, sample_size=None):
        """
        STEP 2: Resolve transitive dependencies for all projects

        This explores the complete dependency tree for each project.
        Expected time: 30-60 minutes
        """
        logger.info("="*70)
        logger.info("STEP 2: Resolving Transitive Dependencies")
        logger.info("="*70)

        conn = sqlite3.connect(str(self.resolver.db_path))
        cursor = conn.cursor()

        # Get all projects
        cursor.execute("SELECT id, name FROM projects")
        projects = cursor.fetchall()

        if sample_size:
            projects = projects[:sample_size]
            logger.info(f"Running on sample of {sample_size} projects")

        total_projects = len(projects)
        logger.info(f"Resolving dependencies for {total_projects} projects")
        logger.info("")

        results = []
        start_time = time.time()

        for i, (project_id, project_name) in enumerate(projects, 1):
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total_projects - i) / rate
                logger.info(f"Progress: {i}/{total_projects} - ETA: {remaining/60:.1f} min")

            try:
                logger.info(f"  [{i}/{total_projects}] Resolving {project_name}...")

                resolution = self.resolver.resolve_all_project_dependencies(project_id)

                results.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'direct_dependencies': resolution['direct_dependencies'],
                    'total_transitive': resolution['total_transitive_dependencies'],
                    'cache_stats': resolution['cache_stats']
                })

            except Exception as e:
                logger.error(f"    ✗ Error: {e}")
                results.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'error': str(e)
                })

        elapsed_time = time.time() - start_time

        logger.info("")
        logger.info("="*70)
        logger.info("STEP 2 COMPLETE")
        logger.info("="*70)
        logger.info(f"Projects analyzed: {total_projects}")
        logger.info(f"Time taken: {elapsed_time/60:.1f} minutes")
        logger.info("")

        # Save results
        output_file = self.output_dir / 'step2_transitive_dependencies.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_projects': total_projects,
                'duration_seconds': elapsed_time,
                'projects': results
            }, f, indent=2)

        logger.info(f"Results saved to: {output_file}")

        self.results['step2'] = {
            'total_projects': total_projects,
            'duration_seconds': elapsed_time
        }

        return results

    def step3_full_impact_analysis(self, sample_size=None):
        """
        STEP 3: Complete impact analysis for all projects

        This combines CVE data with dependency trees to show full impact.
        Expected time: 1-2 hours
        """
        logger.info("="*70)
        logger.info("STEP 3: Full Impact Analysis (CVEs + Dependencies)")
        logger.info("="*70)

        conn = sqlite3.connect(str(self.impact_analyzer.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, url FROM projects")
        projects = cursor.fetchall()

        if sample_size:
            projects = projects[:sample_size]
            logger.info(f"Running on sample of {sample_size} projects")

        total_projects = len(projects)
        logger.info(f"Analyzing {total_projects} projects for CVE impact")
        logger.info("")

        results = []
        start_time = time.time()

        for i, (project_id, project_name, project_url) in enumerate(projects, 1):
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total_projects - i) / rate
                logger.info(f"Progress: {i}/{total_projects} - ETA: {remaining/60:.1f} min")

            try:
                logger.info(f"  [{i}/{total_projects}] Analyzing {project_name}...")

                report = self.impact_analyzer.analyze_project_full_impact(
                    project_id,
                    resolve_transitive=True,
                    scan_cves=True
                )

                summary = report['summary']

                if summary['total_cves'] > 0:
                    logger.info(f"    ⚠️  {summary['total_cves']} CVEs found!")

                results.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'project_url': project_url,
                    'summary': summary,
                    'severity_breakdown': report.get('severity_breakdown', {}),
                    'high_risk_dependencies': report.get('high_risk_dependencies', [])[:5],
                    'vulnerabilities': report.get('vulnerabilities', [])
                })

            except Exception as e:
                logger.error(f"    ✗ Error: {e}")
                results.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'error': str(e)
                })

        elapsed_time = time.time() - start_time

        logger.info("")
        logger.info("="*70)
        logger.info("STEP 3 COMPLETE")
        logger.info("="*70)
        logger.info(f"Projects analyzed: {total_projects}")
        logger.info(f"Time taken: {elapsed_time/60:.1f} minutes")
        logger.info("")

        # Save results
        output_file = self.output_dir / 'step3_full_impact_analysis.json'
        with open(output_file, 'w') as f:
            json.dump({
                'total_projects': total_projects,
                'duration_seconds': elapsed_time,
                'projects': results
            }, f, indent=2)

        logger.info(f"Results saved to: {output_file}")

        self.results['step3'] = {
            'total_projects': total_projects,
            'duration_seconds': elapsed_time
        }

        return results

    def step4_generate_reports(self):
        """
        STEP 4: Generate comprehensive reports and exports

        Creates multiple formats for different audiences:
        - Executive summary (high-level)
        - Technical deep-dive (detailed CVEs)
        - CSV exports for Excel
        - Vulnerability matrix
        """
        logger.info("="*70)
        logger.info("STEP 4: Generating Comprehensive Reports")
        logger.info("="*70)

        conn = sqlite3.connect(str(self.scanner.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. CVE Summary Report
        logger.info("  Generating CVE summary...")
        cursor.execute("""
            SELECT pc.package_name, pc.ecosystem, pc.cve_id, pc.severity,
                   pc.cvss_score, pc.description, pc.published_date,
                   COUNT(DISTINCT d.project_id) as affected_projects
            FROM package_cves pc
            LEFT JOIN dependencies d ON pc.package_name = d.dependency_name
                                     AND pc.ecosystem = d.ecosystem
            GROUP BY pc.id
            ORDER BY affected_projects DESC, pc.cvss_score DESC
        """)

        cve_summary = []
        for row in cursor.fetchall():
            cve_summary.append(dict(row))

        # Save CVE summary
        with open(self.output_dir / 'cve_summary_detailed.json', 'w') as f:
            json.dump(cve_summary, f, indent=2)

        # 2. CSV Export for Excel
        logger.info("  Generating CSV exports...")
        with open(self.output_dir / 'cve_summary.csv', 'w', newline='', encoding='utf-8') as f:
            if cve_summary:
                writer = csv.DictWriter(f, fieldnames=cve_summary[0].keys())
                writer.writeheader()
                writer.writerows(cve_summary)

        # 3. Vulnerability Matrix (Project × CVE)
        logger.info("  Generating vulnerability matrix...")
        cursor.execute("""
            SELECT p.name as project_name, p.url,
                   GROUP_CONCAT(DISTINCT pc.cve_id) as cves,
                   COUNT(DISTINCT pc.cve_id) as cve_count
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            JOIN package_cves pc ON d.dependency_name = pc.package_name
                                 AND d.ecosystem = pc.ecosystem
            GROUP BY p.id
            ORDER BY cve_count DESC
        """)

        vulnerability_matrix = []
        for row in cursor.fetchall():
            vulnerability_matrix.append(dict(row))

        with open(self.output_dir / 'vulnerability_matrix.csv', 'w', newline='', encoding='utf-8') as f:
            if vulnerability_matrix:
                writer = csv.DictWriter(f, fieldnames=['project_name', 'url', 'cve_count', 'cves'])
                writer.writeheader()
                writer.writerows(vulnerability_matrix)

        # 4. Executive Summary
        logger.info("  Generating executive summary...")

        cursor.execute("SELECT COUNT(*) FROM projects")
        total_projects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT package_name) FROM package_cves")
        packages_with_cves = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM package_cves")
        total_cves = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT p.id)
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            JOIN package_cves pc ON d.dependency_name = pc.package_name
        """)
        affected_projects = cursor.fetchone()[0]

        executive_summary = {
            'scan_completed': datetime.now().isoformat(),
            'overview': {
                'total_projects': total_projects,
                'projects_with_vulnerabilities': affected_projects,
                'percentage_affected': round(affected_projects / total_projects * 100, 1),
                'total_cves_found': total_cves,
                'unique_packages_with_cves': packages_with_cves
            },
            'top_risks': vulnerability_matrix[:10],
            'recommendations': [
                "Immediate update required for packages with CRITICAL/HIGH severity CVEs",
                "Implement automated dependency scanning in CI/CD pipeline",
                "Establish security response team for vulnerability triage",
                "Schedule quarterly dependency audits",
                "Consider using Dependabot or similar for automated updates"
            ]
        }

        with open(self.output_dir / 'EXECUTIVE_SUMMARY.json', 'w') as f:
            json.dump(executive_summary, f, indent=2)

        # 5. Final report
        self.results['scan_end_time'] = datetime.now().isoformat()
        self.results['executive_summary'] = executive_summary

        with open(self.output_dir / 'FULL_ANALYSIS_REPORT.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info("")
        logger.info("="*70)
        logger.info("STEP 4 COMPLETE - All Reports Generated")
        logger.info("="*70)
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        logger.info(f"  - FULL_ANALYSIS_REPORT.json (complete results)")
        logger.info(f"  - EXECUTIVE_SUMMARY.json (high-level overview)")
        logger.info(f"  - cve_summary.csv (Excel-ready)")
        logger.info(f"  - vulnerability_matrix.csv (Project × CVE matrix)")
        logger.info(f"  - step1_all_packages_cves.json (all CVE details)")
        logger.info(f"  - step2_transitive_dependencies.json (dependency trees)")
        logger.info(f"  - step3_full_impact_analysis.json (impact analysis)")
        logger.info("")

        return executive_summary

    def run_full_analysis(self, force_refresh=False, sample_projects=None):
        """
        Run the complete 4-step analysis.

        Args:
            force_refresh: Force re-scan even if cached
            sample_projects: If set, only analyze this many projects (for testing)

        Expected total time: 3-5 hours for full analysis
        """
        logger.info("="*70)
        logger.info("STARTING FULL DEEP CVE ANALYSIS")
        logger.info("="*70)
        logger.info(f"Configuration:")
        logger.info(f"  - Force refresh: {force_refresh}")
        logger.info(f"  - Sample projects: {sample_projects or 'ALL'}")
        logger.info(f"  - Max dependency depth: 3")
        logger.info(f"  - Output directory: {self.output_dir.absolute()}")
        logger.info("")

        try:
            # Step 1: Scan all packages for CVEs
            self.step1_scan_all_packages(force_refresh=force_refresh)

            # Step 2: Resolve transitive dependencies
            self.step2_resolve_transitive_dependencies(sample_size=sample_projects)

            # Step 3: Full impact analysis
            self.step3_full_impact_analysis(sample_size=sample_projects)

            # Step 4: Generate reports
            self.step4_generate_reports()

            logger.info("="*70)
            logger.info("🎉 FULL ANALYSIS COMPLETE!")
            logger.info("="*70)
            logger.info(f"All results saved to: {self.output_dir.absolute()}")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Review EXECUTIVE_SUMMARY.json for high-level findings")
            logger.info("  2. Check vulnerability_matrix.csv in Excel")
            logger.info("  3. Prioritize projects with highest CVE counts")
            logger.info("  4. Create remediation plan for high-severity CVEs")
            logger.info("")

            return self.results

        except KeyboardInterrupt:
            logger.warning("\n\nAnalysis interrupted by user")
            logger.info("Partial results saved to output directory")
            return self.results
        except Exception as e:
            logger.error(f"\n\nFatal error: {e}")
            import traceback
            traceback.print_exc()
            return self.results


def main():
    """Main entry point with command-line options."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Run comprehensive CVE and dependency analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full analysis (3-5 hours)
  python run_full_analysis.py --full

  # Quick test with sample (10 minutes)
  python run_full_analysis.py --sample 20

  # Force refresh cached data
  python run_full_analysis.py --full --force-refresh

  # Individual steps
  python run_full_analysis.py --step1-only  # Scan packages
  python run_full_analysis.py --step3-only  # Impact analysis
        """
    )

    parser.add_argument('--full', action='store_true',
                       help='Run complete analysis on ALL projects (3-5 hours)')
    parser.add_argument('--sample', type=int, metavar='N',
                       help='Run on sample of N projects (for testing)')
    parser.add_argument('--force-refresh', action='store_true',
                       help='Force re-scan even if cached')
    parser.add_argument('--step1-only', action='store_true',
                       help='Only run Step 1: Package CVE scan')
    parser.add_argument('--step2-only', action='store_true',
                       help='Only run Step 2: Transitive dependencies')
    parser.add_argument('--step3-only', action='store_true',
                       help='Only run Step 3: Impact analysis')
    parser.add_argument('--step4-only', action='store_true',
                       help='Only run Step 4: Generate reports')
    parser.add_argument('--output-dir', default='full_analysis_results',
                       help='Output directory for results')

    args = parser.parse_args()

    # Create runner
    runner = FullAnalysisRunner(output_dir=args.output_dir)

    # Run requested steps
    if args.step1_only:
        runner.step1_scan_all_packages(force_refresh=args.force_refresh)
    elif args.step2_only:
        runner.step2_resolve_transitive_dependencies(sample_size=args.sample)
    elif args.step3_only:
        runner.step3_full_impact_analysis(sample_size=args.sample)
    elif args.step4_only:
        runner.step4_generate_reports()
    else:
        # Full analysis
        sample = args.sample if args.sample else None
        runner.run_full_analysis(
            force_refresh=args.force_refresh,
            sample_projects=sample
        )


if __name__ == "__main__":
    main()
