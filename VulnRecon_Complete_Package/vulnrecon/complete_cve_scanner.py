#!/usr/bin/env python3
"""
Complete CVE scanner for all energy sector open source projects.
Uses fixed OSV API integration with proper ecosystem mapping.
"""

import sys
import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import click
from datetime import datetime
import time

# Add the vulnrecon package to the path
sys.path.insert(0, str(Path(__file__).parent))

from vulnrecon.utils.version_parser import enhanced_parser, is_vulnerable
from vulnrecon.scanners.professional_scanner import professional_scanner
from vulnrecon.detectors.pyyaml_detector import PyYAMLDetector
from vulnrecon.detectors.base import Severity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CompleteCVEScanner:
    """Complete CVE scanner for all energy sector projects."""
    
    def __init__(self):
        """Initialize the complete scanner."""
        self.professional_scanner = professional_scanner
        self.pyyaml_detector = PyYAMLDetector({})
        self.scan_stats = {
            'total_projects': 0,
            'projects_scanned': 0,
            'projects_with_vulnerabilities': 0,
            'projects_safe': 0,
            'projects_needs_review': 0,
            'total_vulnerabilities': 0,
            'api_errors': 0,
            'scan_start_time': None,
            'scan_end_time': None
        }
        
    def scan_all_projects(self, db_path: str, output_dir: str = "complete_scan_results") -> Dict[str, Any]:
        """
        Scan all projects in the database for CVE vulnerabilities.
        
        Args:
            db_path: Path to SQLite database
            output_dir: Directory to save results
            
        Returns:
            Complete scan results
        """
        self.scan_stats['scan_start_time'] = datetime.now()
        
        logger.info("🚀 Starting Complete CVE Scan of All Energy Sector Projects")
        logger.info("=" * 80)
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all projects with dependencies
        cursor.execute("""
            SELECT DISTINCT p.id, p.name, p.url, p.language, p.stars, p.forks
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            ORDER BY p.stars DESC, p.name
        """)
        
        all_projects = cursor.fetchall()
        self.scan_stats['total_projects'] = len(all_projects)
        
        logger.info(f"📊 Found {len(all_projects)} projects with dependencies")
        logger.info(f"🔧 Available professional tools: {list(self.professional_scanner.available_tools.keys())}")
        logger.info("")
        
        results = {
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'scanner_version': '2.0.0-complete',
                'database_path': db_path,
                'output_directory': output_dir,
                'total_projects': len(all_projects)
            },
            'summary': {
                'total_projects': len(all_projects),
                'projects_scanned': 0,
                'projects_with_vulnerabilities': 0,
                'projects_safe': 0,
                'projects_needs_review': 0,
                'total_vulnerabilities': 0,
                'scan_duration_minutes': 0
            },
            'projects': [],
            'vulnerability_summary': {},
            'package_analysis': {}
        }
        
        # Scan each project
        for i, project in enumerate(all_projects, 1):
            try:
                logger.info(f"🔍 [{i}/{len(all_projects)}] Scanning: {project['name']}")
                logger.info(f"    URL: {project['url']}")
                logger.info(f"    Language: {project['language']}, Stars: {project['stars']}")
                
                project_result = self._scan_single_project(cursor, project)
                results['projects'].append(project_result)
                
                # Update summary statistics
                self.scan_stats['projects_scanned'] += 1
                
                if project_result['risk_level'] in ['CRITICAL', 'HIGH']:
                    self.scan_stats['projects_with_vulnerabilities'] += 1
                elif project_result['risk_level'] in ['LOW', 'INFO']:
                    self.scan_stats['projects_safe'] += 1
                else:
                    self.scan_stats['projects_needs_review'] += 1
                
                self.scan_stats['total_vulnerabilities'] += project_result['total_findings']
                
                # Save individual project result
                self._save_project_result(project_result, output_dir)
                
                # Progress update every 10 projects
                if i % 10 == 0:
                    self._print_progress_update(i, len(all_projects))
                
                # Small delay to be respectful to APIs
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error scanning {project['name']}: {e}")
                self.scan_stats['api_errors'] += 1
                continue
        
        conn.close()
        
        # Finalize results
        self.scan_stats['scan_end_time'] = datetime.now()
        scan_duration = (self.scan_stats['scan_end_time'] - self.scan_stats['scan_start_time']).total_seconds() / 60
        
        results['summary'].update({
            'projects_scanned': self.scan_stats['projects_scanned'],
            'projects_with_vulnerabilities': self.scan_stats['projects_with_vulnerabilities'],
            'projects_safe': self.scan_stats['projects_safe'],
            'projects_needs_review': self.scan_stats['projects_needs_review'],
            'total_vulnerabilities': self.scan_stats['total_vulnerabilities'],
            'scan_duration_minutes': round(scan_duration, 2),
            'api_errors': self.scan_stats['api_errors']
        })
        
        # Generate analysis summaries
        results['vulnerability_summary'] = self._generate_vulnerability_summary(results['projects'])
        results['package_analysis'] = self._generate_package_analysis(results['projects'])
        
        # Save complete results
        self._save_complete_results(results, output_dir)
        
        return results
    
    def _scan_single_project(self, cursor, project) -> Dict[str, Any]:
        """Scan a single project with enhanced CVE detection."""
        project_id = project['id']
        project_name = project['name']
        project_url = project['url']
        
        # Get all dependencies for this project
        cursor.execute("""
            SELECT dependency_name, version_spec, ecosystem, dependency_type
            FROM dependencies
            WHERE project_id = ?
            ORDER BY dependency_name
        """, (project_id,))
        
        dependencies = [dict(row) for row in cursor.fetchall()]
        
        # Run enhanced detection with professional tools
        all_findings = []
        
        # 1. Run custom PyYAML detector (enhanced version parsing)
        pyyaml_findings = self.pyyaml_detector.detect("", dependencies)
        all_findings.extend(pyyaml_findings)
        
        # 2. Run professional scanner with fixed OSV API
        try:
            prof_results = self.professional_scanner.scan_dependencies(dependencies)
            prof_findings = self.professional_scanner.convert_to_findings(prof_results)
            all_findings.extend(prof_findings)
        except Exception as e:
            logger.debug(f"Professional scanner error for {project_name}: {e}")
        
        # Calculate risk metrics
        risk_score = self._calculate_risk_score(all_findings)
        risk_level = self._get_risk_level(risk_score)
        
        # Analyze specific packages
        package_analysis = self._analyze_project_packages(dependencies)
        
        return {
            'project_id': project_id,
            'project_name': project_name,
            'project_url': project_url,
            'language': project['language'],
            'stars': project['stars'],
            'forks': project['forks'],
            'total_dependencies': len(dependencies),
            'total_findings': len(all_findings),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'findings_by_severity': self._count_by_severity(all_findings),
            'package_analysis': package_analysis,
            'findings': [f.to_dict() for f in all_findings],
            'dependencies': dependencies,
            'scan_timestamp': datetime.now().isoformat()
        }
    
    def _analyze_project_packages(self, dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze specific packages in the project."""
        analysis = {
            'high_risk_packages': [],
            'safe_packages': [],
            'unknown_packages': [],
            'package_counts': {}
        }
        
        # Known high-risk packages to analyze
        risk_packages = {
            'pyyaml': {'name_variants': ['pyyaml', 'yaml'], 'safe_version': '5.4'},
            'django': {'name_variants': ['django'], 'safe_version': '4.2.0'},
            'pillow': {'name_variants': ['pillow', 'pil'], 'safe_version': '10.0.0'},
            'requests': {'name_variants': ['requests'], 'safe_version': '2.31.0'},
            'numpy': {'name_variants': ['numpy'], 'safe_version': '1.22.0'},
        }
        
        for dep in dependencies:
            dep_name = dep.get('dependency_name', '').lower()
            version_spec = dep.get('version_spec', '')
            
            # Check if this is a known risk package
            for risk_pkg, info in risk_packages.items():
                if dep_name in info['name_variants']:
                    analysis['package_counts'][risk_pkg] = analysis['package_counts'].get(risk_pkg, 0) + 1
                    
                    exact_version = enhanced_parser.extract_exact_version(version_spec)
                    
                    if exact_version:
                        # Compare with safe version
                        try:
                            if enhanced_parser.compare_versions(exact_version, info['safe_version']) >= 0:
                                analysis['safe_packages'].append({
                                    'package': risk_pkg,
                                    'version': exact_version,
                                    'status': 'safe'
                                })
                            else:
                                analysis['high_risk_packages'].append({
                                    'package': risk_pkg,
                                    'version': exact_version,
                                    'status': 'vulnerable',
                                    'safe_version': info['safe_version']
                                })
                        except:
                            analysis['unknown_packages'].append({
                                'package': risk_pkg,
                                'version': exact_version,
                                'status': 'version_comparison_failed'
                            })
                    else:
                        analysis['unknown_packages'].append({
                            'package': risk_pkg,
                            'version_spec': version_spec,
                            'status': 'no_exact_version'
                        })
        
        return analysis
    
    def _calculate_risk_score(self, findings) -> float:
        """Calculate risk score based on findings."""
        if not findings:
            return 0.0
        
        severity_weights = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 7.5,
            Severity.MEDIUM: 5.0,
            Severity.LOW: 2.5,
            Severity.INFO: 0.0
        }
        
        total_score = sum(
            severity_weights.get(f.severity, 0) * f.confidence
            for f in findings
        )
        
        # Normalize to 0-10 scale
        max_possible = len(findings) * 10.0
        return round(min(10.0, (total_score / max_possible) * 10.0), 2) if max_possible > 0 else 0.0
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level from score."""
        if risk_score >= 9.0:
            return "CRITICAL"
        elif risk_score >= 7.0:
            return "HIGH"
        elif risk_score >= 4.0:
            return "MEDIUM"
        elif risk_score > 0:
            return "LOW"
        else:
            return "INFO"
    
    def _count_by_severity(self, findings) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0
        }
        
        for finding in findings:
            counts[finding.severity.value] += 1
        
        return counts
    
    def _generate_vulnerability_summary(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate vulnerability summary across all projects."""
        summary = {
            'total_vulnerabilities': 0,
            'by_severity': {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0},
            'by_risk_level': {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0},
            'most_vulnerable_projects': [],
            'common_vulnerabilities': {}
        }
        
        for project in projects:
            summary['total_vulnerabilities'] += project['total_findings']
            
            # Count by severity
            for severity, count in project['findings_by_severity'].items():
                summary['by_severity'][severity] += count
            
            # Count by risk level
            summary['by_risk_level'][project['risk_level']] += 1
        
        # Get most vulnerable projects
        summary['most_vulnerable_projects'] = sorted(
            [
                {
                    'name': p['project_name'],
                    'url': p['project_url'],
                    'risk_level': p['risk_level'],
                    'risk_score': p['risk_score'],
                    'total_findings': p['total_findings'],
                    'stars': p['stars']
                }
                for p in projects if p['total_findings'] > 0
            ],
            key=lambda x: (x['risk_score'], x['total_findings']),
            reverse=True
        )[:20]
        
        return summary
    
    def _generate_package_analysis(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate package analysis across all projects."""
        package_stats = {}
        
        for project in projects:
            for pkg_name, count in project['package_analysis']['package_counts'].items():
                if pkg_name not in package_stats:
                    package_stats[pkg_name] = {
                        'total_projects': 0,
                        'vulnerable_projects': 0,
                        'safe_projects': 0,
                        'unknown_projects': 0
                    }
                
                package_stats[pkg_name]['total_projects'] += 1
                
                # Count status
                vulnerable = len([p for p in project['package_analysis']['high_risk_packages'] if p['package'] == pkg_name])
                safe = len([p for p in project['package_analysis']['safe_packages'] if p['package'] == pkg_name])
                unknown = len([p for p in project['package_analysis']['unknown_packages'] if p['package'] == pkg_name])
                
                if vulnerable > 0:
                    package_stats[pkg_name]['vulnerable_projects'] += 1
                elif safe > 0:
                    package_stats[pkg_name]['safe_projects'] += 1
                else:
                    package_stats[pkg_name]['unknown_projects'] += 1
        
        return package_stats
    
    def _print_progress_update(self, current: int, total: int):
        """Print progress update."""
        progress = (current / total) * 100
        logger.info(f"📊 Progress: {current}/{total} ({progress:.1f}%)")
        logger.info(f"   Scanned: {self.scan_stats['projects_scanned']}")
        logger.info(f"   Vulnerable: {self.scan_stats['projects_with_vulnerabilities']}")
        logger.info(f"   Safe: {self.scan_stats['projects_safe']}")
        logger.info(f"   Needs Review: {self.scan_stats['projects_needs_review']}")
        logger.info(f"   API Errors: {self.scan_stats['api_errors']}")
        logger.info("")
    
    def _save_project_result(self, result: Dict[str, Any], output_dir: str):
        """Save individual project result."""
        project_name = result['project_name'].replace('/', '_').replace(' ', '_')
        filename = f"{project_name}_scan.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2)
    
    def _save_complete_results(self, results: Dict[str, Any], output_dir: str):
        """Save complete scan results."""
        # Save main results
        main_file = os.path.join(output_dir, "complete_scan_results.json")
        with open(main_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save summary report
        summary_file = os.path.join(output_dir, "scan_summary.json")
        summary_data = {
            'scan_metadata': results['scan_metadata'],
            'summary': results['summary'],
            'vulnerability_summary': results['vulnerability_summary'],
            'package_analysis': results['package_analysis']
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info(f"💾 Complete results saved to: {main_file}")
        logger.info(f"💾 Summary report saved to: {summary_file}")


@click.command()
@click.option('--database', '-d', required=True, help='Path to dependencies database')
@click.option('--output', '-o', default='complete_scan_results', help='Output directory')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(database, output, verbose):
    """Run complete CVE scan on all energy sector projects."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo("🚀 Complete CVE Scanner for Energy Sector Open Source Projects")
    click.echo("=" * 80)
    
    if not os.path.exists(database):
        click.echo(f"❌ Database not found: {database}")
        sys.exit(1)
    
    scanner = CompleteCVEScanner()
    
    # Check available tools
    available_tools = [tool for tool, available in scanner.professional_scanner.available_tools.items() if available]
    
    click.echo(f"🔧 Available professional tools: {', '.join(available_tools) if available_tools else 'None'}")
    click.echo(f"📊 Database: {database}")
    click.echo(f"📁 Output directory: {output}")
    click.echo()
    
    try:
        # Run complete scan
        results = scanner.scan_all_projects(database, output)
        
        # Display final summary
        click.echo("\n" + "=" * 80)
        click.echo("🎉 COMPLETE SCAN FINISHED!")
        click.echo("=" * 80)
        
        summary = results['summary']
        click.echo(f"📊 SCAN STATISTICS:")
        click.echo(f"   Total projects: {summary['total_projects']}")
        click.echo(f"   Projects scanned: {summary['projects_scanned']}")
        click.echo(f"   Scan duration: {summary['scan_duration_minutes']:.1f} minutes")
        click.echo()
        
        click.echo(f"🔍 VULNERABILITY ANALYSIS:")
        click.echo(f"   Projects with vulnerabilities: {summary['projects_with_vulnerabilities']}")
        click.echo(f"   Projects confirmed safe: {summary['projects_safe']}")
        click.echo(f"   Projects needing review: {summary['projects_needs_review']}")
        click.echo(f"   Total vulnerabilities found: {summary['total_vulnerabilities']}")
        click.echo()
        
        if summary['api_errors'] > 0:
            click.echo(f"⚠️  API errors encountered: {summary['api_errors']}")
            click.echo()
        
        # Show top vulnerable projects
        vuln_summary = results['vulnerability_summary']
        if vuln_summary['most_vulnerable_projects']:
            click.echo("🚨 TOP 10 MOST VULNERABLE PROJECTS:")
            for i, project in enumerate(vuln_summary['most_vulnerable_projects'][:10], 1):
                click.echo(f"   {i:2d}. {project['name']} - {project['risk_level']} ({project['total_findings']} issues)")
        
        click.echo(f"\n📁 Results saved to: {output}/")
        click.echo("   • complete_scan_results.json - Full detailed results")
        click.echo("   • scan_summary.json - Executive summary")
        click.echo("   • Individual project files - Per-project details")
        
    except KeyboardInterrupt:
        click.echo("\n\n⏹️  Scan interrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Scan failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
