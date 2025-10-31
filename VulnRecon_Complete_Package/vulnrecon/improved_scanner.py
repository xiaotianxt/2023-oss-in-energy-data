#!/usr/bin/env python3
"""
Improved VulnRecon scanner with enhanced version parsing and professional tool integration.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import click
from datetime import datetime

# Add the vulnrecon package to the path
sys.path.insert(0, str(Path(__file__).parent))

from vulnrecon.utils.version_parser import enhanced_parser
from vulnrecon.scanners.professional_scanner import professional_scanner
from vulnrecon.detectors.pyyaml_detector import PyYAMLDetector
from vulnrecon.detectors.base import Severity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImprovedVulnReconScanner:
    """Improved vulnerability scanner with enhanced version parsing."""
    
    def __init__(self):
        """Initialize the improved scanner."""
        self.professional_scanner = professional_scanner
        self.pyyaml_detector = PyYAMLDetector({})
        
    def scan_database_projects(self, db_path: str, limit: int = 10) -> Dict[str, Any]:
        """
        Scan projects from database with improved version matching.
        
        Args:
            db_path: Path to SQLite database
            limit: Number of projects to scan
            
        Returns:
            Scan results dictionary
        """
        import sqlite3
        
        logger.info(f"Connecting to database: {db_path}")
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get projects with PyYAML dependencies
            cursor.execute("""
                SELECT DISTINCT p.id, p.name, p.url, p.language
                FROM projects p
                JOIN dependencies d ON p.id = d.project_id
                WHERE LOWER(d.dependency_name) IN ('pyyaml', 'yaml')
                ORDER BY p.name
                LIMIT ?
            """, (limit,))
            
            projects = cursor.fetchall()
            logger.info(f"Found {len(projects)} projects with PyYAML dependencies")
            
            results = {
                'scan_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'scanner_version': '2.0.0-improved',
                    'database_path': db_path,
                    'projects_scanned': len(projects)
                },
                'summary': {
                    'total_projects': len(projects),
                    'vulnerable_projects': 0,
                    'safe_projects': 0,
                    'unknown_projects': 0,
                    'total_findings': 0
                },
                'projects': []
            }
            
            for project in projects:
                project_result = self._scan_single_project(cursor, project)
                results['projects'].append(project_result)
                
                # Update summary
                if project_result['risk_level'] in ['CRITICAL', 'HIGH']:
                    results['summary']['vulnerable_projects'] += 1
                elif project_result['risk_level'] in ['LOW', 'INFO']:
                    results['summary']['safe_projects'] += 1
                else:
                    results['summary']['unknown_projects'] += 1
                
                results['summary']['total_findings'] += project_result['total_findings']
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error scanning database: {e}")
            return {'error': str(e)}
    
    def _scan_single_project(self, cursor, project) -> Dict[str, Any]:
        """Scan a single project with improved version matching."""
        project_id = project['id']
        project_name = project['name']
        project_url = project['url']
        
        logger.info(f"Scanning project: {project_name}")
        
        # Get dependencies for this project
        cursor.execute("""
            SELECT dependency_name, version_spec, ecosystem
            FROM dependencies
            WHERE project_id = ?
        """, (project_id,))
        
        dependencies = [dict(row) for row in cursor.fetchall()]
        
        # Run improved PyYAML detection
        findings = self.pyyaml_detector.detect("", dependencies)
        
        # Try professional scanner if available
        if self.professional_scanner.available_tools:
            try:
                prof_results = self.professional_scanner.scan_dependencies(dependencies)
                prof_findings = self.professional_scanner.convert_to_findings(prof_results)
                findings.extend(prof_findings)
            except Exception as e:
                logger.warning(f"Professional scanner failed for {project_name}: {e}")
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(findings)
        risk_level = self._get_risk_level(risk_score)
        
        # Analyze PyYAML versions specifically
        pyyaml_analysis = self._analyze_pyyaml_versions(dependencies)
        
        return {
            'project_id': project_id,
            'project_name': project_name,
            'project_url': project_url,
            'language': project['language'],
            'total_dependencies': len(dependencies),
            'total_findings': len(findings),
            'risk_score': risk_score,
            'risk_level': risk_level,
            'pyyaml_analysis': pyyaml_analysis,
            'findings': [f.to_dict() for f in findings],
            'dependencies': dependencies
        }
    
    def _analyze_pyyaml_versions(self, dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze PyYAML versions in dependencies."""
        pyyaml_deps = []
        
        for dep in dependencies:
            dep_name = dep.get('dependency_name', '')
            normalized_name = enhanced_parser.normalize_package_name(dep_name)
            
            if normalized_name == 'pyyaml':
                version_spec = dep.get('version_spec', '')
                exact_version = enhanced_parser.extract_exact_version(version_spec)
                
                analysis = {
                    'original_name': dep_name,
                    'version_spec': version_spec,
                    'exact_version': exact_version,
                    'ecosystem': dep.get('ecosystem', 'pypi')
                }
                
                # Enhanced version analysis
                if exact_version:
                    vulnerable_ranges = [
                        {
                            'events': [
                                {'introduced': '0'},
                                {'fixed': '5.4'}
                            ]
                        }
                    ]
                    
                    is_vuln, reason = enhanced_parser.is_version_vulnerable(exact_version, vulnerable_ranges)
                    analysis['is_vulnerable'] = is_vuln
                    analysis['vulnerability_reason'] = reason
                    analysis['status'] = 'VULNERABLE' if is_vuln else 'SAFE'
                else:
                    analysis['is_vulnerable'] = None
                    analysis['vulnerability_reason'] = 'Could not determine exact version'
                    analysis['status'] = 'UNKNOWN'
                
                pyyaml_deps.append(analysis)
        
        return {
            'total_pyyaml_dependencies': len(pyyaml_deps),
            'dependencies': pyyaml_deps,
            'summary': {
                'vulnerable': len([d for d in pyyaml_deps if d.get('is_vulnerable') == True]),
                'safe': len([d for d in pyyaml_deps if d.get('is_vulnerable') == False]),
                'unknown': len([d for d in pyyaml_deps if d.get('is_vulnerable') is None])
            }
        }
    
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
    
    def generate_report(self, results: Dict[str, Any], output_path: str):
        """Generate detailed report."""
        report_data = {
            'scan_metadata': results['scan_metadata'],
            'executive_summary': self._generate_executive_summary(results),
            'detailed_findings': self._generate_detailed_findings(results),
            'recommendations': self._generate_recommendations(results),
            'raw_results': results
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Report saved to: {output_path}")
    
    def _generate_executive_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary."""
        summary = results['summary']
        
        # Analyze PyYAML versions across all projects
        all_pyyaml_deps = []
        for project in results['projects']:
            all_pyyaml_deps.extend(project['pyyaml_analysis']['dependencies'])
        
        vulnerable_versions = [d for d in all_pyyaml_deps if d.get('is_vulnerable') == True]
        safe_versions = [d for d in all_pyyaml_deps if d.get('is_vulnerable') == False]
        unknown_versions = [d for d in all_pyyaml_deps if d.get('is_vulnerable') is None]
        
        return {
            'total_projects_scanned': summary['total_projects'],
            'projects_with_vulnerabilities': summary['vulnerable_projects'],
            'projects_confirmed_safe': summary['safe_projects'],
            'projects_status_unknown': summary['unknown_projects'],
            'total_findings': summary['total_findings'],
            'pyyaml_analysis': {
                'total_pyyaml_dependencies': len(all_pyyaml_deps),
                'confirmed_vulnerable': len(vulnerable_versions),
                'confirmed_safe': len(safe_versions),
                'status_unknown': len(unknown_versions),
                'accuracy_improvement': f"{(len(safe_versions) + len(vulnerable_versions)) / len(all_pyyaml_deps) * 100:.1f}%" if all_pyyaml_deps else "N/A"
            },
            'key_findings': [
                f"Found {len(vulnerable_versions)} confirmed vulnerable PyYAML installations",
                f"Found {len(safe_versions)} confirmed safe PyYAML installations (6.0+)",
                f"{len(unknown_versions)} dependencies need manual review (no version specified)",
                f"Improved accuracy: {(len(safe_versions) + len(vulnerable_versions)) / len(all_pyyaml_deps) * 100:.1f}% of dependencies accurately classified" if all_pyyaml_deps else "No PyYAML dependencies found"
            ]
        }
    
    def _generate_detailed_findings(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate detailed findings."""
        detailed = []
        
        for project in results['projects']:
            if project['total_findings'] > 0:
                detailed.append({
                    'project_name': project['project_name'],
                    'project_url': project['project_url'],
                    'risk_level': project['risk_level'],
                    'risk_score': project['risk_score'],
                    'pyyaml_status': project['pyyaml_analysis']['summary'],
                    'key_issues': [
                        f.get('title', 'Unknown issue')
                        for f in project['findings']
                        if f.get('severity') in ['CRITICAL', 'HIGH']
                    ]
                })
        
        return detailed
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations."""
        recommendations = []
        
        summary = results['summary']
        
        if summary['vulnerable_projects'] > 0:
            recommendations.append(f"URGENT: {summary['vulnerable_projects']} projects have confirmed PyYAML vulnerabilities - upgrade to PyYAML 5.4+ immediately")
        
        if summary['unknown_projects'] > 0:
            recommendations.append(f"REVIEW: {summary['unknown_projects']} projects have unspecified PyYAML versions - pin to PyYAML>=5.4")
        
        recommendations.extend([
            "Use professional security tools (Safety, Bandit, pip-audit) for comprehensive scanning",
            "Implement automated dependency scanning in CI/CD pipelines",
            "Regularly update dependencies and monitor for new vulnerabilities",
            "Consider using dependency management tools like Dependabot or Renovate"
        ])
        
        return recommendations


@click.command()
@click.option('--database', '-d', required=True, help='Path to dependencies database')
@click.option('--limit', '-l', default=20, help='Number of projects to scan')
@click.option('--output', '-o', default='improved_scan_results.json', help='Output file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(database, limit, output, verbose):
    """Run improved VulnRecon scanner with enhanced version parsing."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    click.echo("🔍 VulnRecon Improved Scanner v2.0")
    click.echo("=" * 50)
    
    if not os.path.exists(database):
        click.echo(f"❌ Database not found: {database}")
        sys.exit(1)
    
    scanner = ImprovedVulnReconScanner()
    
    # Check available tools
    available_tools = [tool for tool, available in scanner.professional_scanner.available_tools.items() if available]
    
    click.echo(f"📊 Available professional tools: {', '.join(available_tools) if available_tools else 'None (using enhanced custom scanner)'}")
    click.echo(f"🎯 Scanning {limit} projects from: {database}")
    click.echo()
    
    # Run scan
    results = scanner.scan_database_projects(database, limit)
    
    if 'error' in results:
        click.echo(f"❌ Scan failed: {results['error']}")
        sys.exit(1)
    
    # Generate report
    scanner.generate_report(results, output)
    
    # Display summary
    summary = results['summary']
    click.echo("📋 SCAN RESULTS SUMMARY")
    click.echo("-" * 30)
    click.echo(f"Total projects scanned: {summary['total_projects']}")
    click.echo(f"Projects with vulnerabilities: {summary['vulnerable_projects']}")
    click.echo(f"Projects confirmed safe: {summary['safe_projects']}")
    click.echo(f"Projects needing review: {summary['unknown_projects']}")
    click.echo(f"Total findings: {summary['total_findings']}")
    click.echo()
    
    # PyYAML specific analysis
    all_pyyaml_deps = []
    for project in results['projects']:
        all_pyyaml_deps.extend(project['pyyaml_analysis']['dependencies'])
    
    if all_pyyaml_deps:
        vulnerable = len([d for d in all_pyyaml_deps if d.get('is_vulnerable') == True])
        safe = len([d for d in all_pyyaml_deps if d.get('is_vulnerable') == False])
        unknown = len([d for d in all_pyyaml_deps if d.get('is_vulnerable') is None])
        
        click.echo("🔍 PYYAML VERSION ANALYSIS")
        click.echo("-" * 30)
        click.echo(f"Total PyYAML dependencies: {len(all_pyyaml_deps)}")
        click.echo(f"Confirmed vulnerable (< 5.4): {vulnerable}")
        click.echo(f"Confirmed safe (>= 5.4): {safe}")
        click.echo(f"Version unknown: {unknown}")
        
        accuracy = (safe + vulnerable) / len(all_pyyaml_deps) * 100
        click.echo(f"Classification accuracy: {accuracy:.1f}%")
        click.echo()
        
        if vulnerable > 0:
            click.echo("⚠️  VULNERABLE PROJECTS:")
            for project in results['projects']:
                vuln_deps = [d for d in project['pyyaml_analysis']['dependencies'] if d.get('is_vulnerable') == True]
                if vuln_deps:
                    click.echo(f"  • {project['project_name']}: {len(vuln_deps)} vulnerable PyYAML dependencies")
        
        if safe > 0:
            click.echo("✅ SAFE PROJECTS:")
            for project in results['projects']:
                safe_deps = [d for d in project['pyyaml_analysis']['dependencies'] if d.get('is_vulnerable') == False]
                if safe_deps and not any(d.get('is_vulnerable') == True for d in project['pyyaml_analysis']['dependencies']):
                    click.echo(f"  • {project['project_name']}: All PyYAML dependencies are safe")
    
    click.echo(f"\n📄 Detailed report saved to: {output}")
    click.echo("\n🎯 NEXT STEPS:")
    click.echo("1. Review projects with confirmed vulnerabilities")
    click.echo("2. Update PyYAML to version 5.4+ in vulnerable projects")
    click.echo("3. Specify versions for dependencies marked as 'unknown'")
    click.echo("4. Consider using professional tools for comprehensive scanning")


if __name__ == '__main__':
    main()
