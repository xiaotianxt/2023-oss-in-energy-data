"""
Enhanced VulnRecon Scanner using Professional Security Tools

This version integrates multiple industry-standard security tools:
- Bandit: Python code security analysis
- Safety: Known CVE detection in dependencies
- pip-audit: Python package auditing
- Semgrep: Multi-language pattern scanning

Much more accurate and comprehensive than custom detectors.
"""

import os
import sys
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import tempfile
import shutil

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("Install rich for better output: pip install rich")


class EnhancedVulnScanner:
    """Enhanced vulnerability scanner using professional tools."""

    def __init__(self):
        self.console = Console() if HAS_RICH else None
        self.tools_available = self._check_tools()

    def _check_tools(self) -> Dict[str, bool]:
        """Check which security tools are available."""
        tools = {
            'bandit': self._command_exists('bandit'),
            'safety': self._command_exists('safety'),
            'pip-audit': self._command_exists('pip-audit'),
            'semgrep': self._command_exists('semgrep'),
            'trivy': self._command_exists('trivy'),
        }

        if self.console:
            table = Table(title="Available Security Tools")
            table.add_column("Tool", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Purpose")

            tool_info = {
                'bandit': 'Python code security',
                'safety': 'Dependency CVE check',
                'pip-audit': 'Python package audit',
                'semgrep': 'Pattern-based scanning',
                'trivy': 'Comprehensive scanner',
            }

            for tool, available in tools.items():
                status = "✓ Available" if available else "✗ Not installed"
                style = "green" if available else "red"
                table.add_row(tool, status, tool_info.get(tool, ""))

            self.console.print(table)
        else:
            print("\nAvailable Security Tools:")
            for tool, available in tools.items():
                status = "✓" if available else "✗"
                print(f"  {status} {tool}")

        return tools

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists."""
        try:
            result = subprocess.run(
                [command, '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def scan_with_bandit(self, target_path: str) -> Dict[str, Any]:
        """Scan Python code with Bandit."""
        if not self.tools_available['bandit']:
            return {"error": "Bandit not available"}

        print("\n[*] Running Bandit (Python security scanner)...")

        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        output_file.close()

        try:
            result = subprocess.run(
                ['bandit', '-r', target_path, '-f', 'json', '-o', output_file.name],
                capture_output=True,
                text=True,
                timeout=300
            )

            with open(output_file.name, 'r') as f:
                data = json.load(f)

            # Extract key information
            findings = data.get('results', [])
            summary = {
                'tool': 'bandit',
                'total_issues': len(findings),
                'by_severity': {
                    'HIGH': len([f for f in findings if f['issue_severity'] == 'HIGH']),
                    'MEDIUM': len([f for f in findings if f['issue_severity'] == 'MEDIUM']),
                    'LOW': len([f for f in findings if f['issue_severity'] == 'LOW']),
                },
                'findings': findings,
                'raw_output': data
            }

            print(f"    Found {len(findings)} issues")
            return summary

        except subprocess.TimeoutExpired:
            return {"error": "Bandit timeout"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            try:
                os.unlink(output_file.name)
            except:
                pass

    def scan_with_safety(self, target_path: str) -> Dict[str, Any]:
        """Scan dependencies with Safety."""
        if not self.tools_available['safety']:
            return {"error": "Safety not available"}

        print("\n[*] Running Safety (dependency CVE scanner)...")

        # Find requirements files
        req_files = list(Path(target_path).rglob('requirements*.txt'))

        if not req_files:
            return {"error": "No requirements.txt found"}

        all_findings = []

        for req_file in req_files:
            try:
                result = subprocess.run(
                    ['safety', 'check', '--file', str(req_file), '--json'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.stdout:
                    data = json.loads(result.stdout)
                    all_findings.extend(data)

            except subprocess.TimeoutExpired:
                continue
            except json.JSONDecodeError:
                # Safety might not return JSON if no issues
                continue
            except Exception as e:
                print(f"    Error scanning {req_file}: {e}")

        summary = {
            'tool': 'safety',
            'total_vulnerabilities': len(all_findings),
            'findings': all_findings,
            'files_scanned': [str(f) for f in req_files]
        }

        print(f"    Found {len(all_findings)} known vulnerabilities")
        return summary

    def scan_with_pip_audit(self, target_path: str) -> Dict[str, Any]:
        """Scan with pip-audit."""
        if not self.tools_available['pip-audit']:
            return {"error": "pip-audit not available"}

        print("\n[*] Running pip-audit (Python package auditor)...")

        req_files = list(Path(target_path).rglob('requirements*.txt'))

        if not req_files:
            return {"error": "No requirements.txt found"}

        all_findings = []

        for req_file in req_files:
            try:
                result = subprocess.run(
                    ['pip-audit', '-r', str(req_file), '--format', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.stdout:
                    data = json.loads(result.stdout)
                    vulnerabilities = data.get('vulnerabilities', [])
                    all_findings.extend(vulnerabilities)

            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                print(f"    Error: {e}")

        summary = {
            'tool': 'pip-audit',
            'total_vulnerabilities': len(all_findings),
            'findings': all_findings,
        }

        print(f"    Found {len(all_findings)} vulnerabilities")
        return summary

    def scan_with_semgrep(self, target_path: str) -> Dict[str, Any]:
        """Scan with Semgrep."""
        if not self.tools_available['semgrep']:
            return {"error": "Semgrep not available"}

        print("\n[*] Running Semgrep (pattern-based scanner)...")

        try:
            result = subprocess.run(
                ['semgrep', '--config=auto', '--json', target_path],
                capture_output=True,
                text=True,
                timeout=300
            )

            data = json.loads(result.stdout)
            findings = data.get('results', [])

            # Group by severity
            by_severity = {}
            for finding in findings:
                severity = finding.get('extra', {}).get('severity', 'INFO')
                by_severity[severity] = by_severity.get(severity, 0) + 1

            summary = {
                'tool': 'semgrep',
                'total_findings': len(findings),
                'by_severity': by_severity,
                'findings': findings,
            }

            print(f"    Found {len(findings)} issues")
            return summary

        except subprocess.TimeoutExpired:
            return {"error": "Semgrep timeout"}
        except Exception as e:
            return {"error": str(e)}

    def scan_with_trivy(self, target_path: str) -> Dict[str, Any]:
        """Scan with Trivy."""
        if not self.tools_available['trivy']:
            return {"error": "Trivy not available"}

        print("\n[*] Running Trivy (comprehensive scanner)...")

        try:
            result = subprocess.run(
                ['trivy', 'fs', '--format', 'json', target_path],
                capture_output=True,
                text=True,
                timeout=300
            )

            data = json.loads(result.stdout)

            # Extract vulnerabilities
            total_vulns = 0
            by_severity = {}

            for target in data.get('Results', []):
                vulns = target.get('Vulnerabilities', [])
                total_vulns += len(vulns)

                for vuln in vulns:
                    severity = vuln.get('Severity', 'UNKNOWN')
                    by_severity[severity] = by_severity.get(severity, 0) + 1

            summary = {
                'tool': 'trivy',
                'total_vulnerabilities': total_vulns,
                'by_severity': by_severity,
                'raw_results': data,
            }

            print(f"    Found {total_vulns} vulnerabilities")
            return summary

        except subprocess.TimeoutExpired:
            return {"error": "Trivy timeout"}
        except Exception as e:
            return {"error": str(e)}

    def scan_repository(self, repo_path: str, repo_name: str = None) -> Dict[str, Any]:
        """Run all available scanners on a repository."""
        print(f"\n{'='*70}")
        print(f"Scanning: {repo_name or repo_path}")
        print(f"{'='*70}")

        results = {
            'repository': {
                'name': repo_name,
                'path': repo_path,
            },
            'scan_metadata': {
                'timestamp': datetime.now().isoformat(),
                'tools_used': [t for t, available in self.tools_available.items() if available],
            },
            'scans': {}
        }

        # Run all available scanners
        if self.tools_available['bandit']:
            results['scans']['bandit'] = self.scan_with_bandit(repo_path)

        if self.tools_available['safety']:
            results['scans']['safety'] = self.scan_with_safety(repo_path)

        if self.tools_available['pip-audit']:
            results['scans']['pip_audit'] = self.scan_with_pip_audit(repo_path)

        if self.tools_available['semgrep']:
            results['scans']['semgrep'] = self.scan_with_semgrep(repo_path)

        if self.tools_available['trivy']:
            results['scans']['trivy'] = self.scan_with_trivy(repo_path)

        # Calculate aggregate statistics
        results['summary'] = self._calculate_summary(results['scans'])

        return results

    def _calculate_summary(self, scans: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate aggregate summary from all scans."""
        total_issues = 0
        critical_count = 0
        high_count = 0

        for tool, scan_result in scans.items():
            if 'error' in scan_result:
                continue

            # Count issues
            if 'total_issues' in scan_result:
                total_issues += scan_result['total_issues']
            if 'total_vulnerabilities' in scan_result:
                total_issues += scan_result['total_vulnerabilities']
            if 'total_findings' in scan_result:
                total_issues += scan_result['total_findings']

            # Count by severity
            by_severity = scan_result.get('by_severity', {})
            critical_count += by_severity.get('CRITICAL', 0)
            high_count += by_severity.get('HIGH', 0)

        # Calculate risk level
        if critical_count > 0:
            risk_level = "CRITICAL"
        elif high_count > 5:
            risk_level = "HIGH"
        elif total_issues > 10:
            risk_level = "MEDIUM"
        elif total_issues > 0:
            risk_level = "LOW"
        else:
            risk_level = "INFO"

        return {
            'total_issues': total_issues,
            'critical_issues': critical_count,
            'high_issues': high_count,
            'risk_level': risk_level,
        }

    def scan_from_database(self, db_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Scan projects from database (without cloning repos)."""
        print(f"\n[*] Scanning projects from database: {db_path}")
        print(f"[*] Mode: Dependency-only analysis (no source code)")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get projects with PyYAML
        cursor.execute("""
            SELECT DISTINCT p.id, p.name, p.url
            FROM projects p
            JOIN dependencies d ON p.id = d.project_id
            WHERE LOWER(d.dependency_name) IN ('pyyaml', 'yaml', 'pillow', 'django', 'requests')
            LIMIT ?
        """, (limit,))

        projects = cursor.fetchall()
        print(f"[*] Found {len(projects)} vulnerable projects\n")

        results = []

        for project_id, name, url in projects:
            print(f"\n{'─'*70}")
            print(f"Analyzing: {name}")

            # Get dependencies
            cursor.execute("""
                SELECT dependency_name, version_spec, ecosystem
                FROM dependencies
                WHERE project_id = ?
            """, (project_id,))

            dependencies = cursor.fetchall()

            # Create temporary requirements.txt
            with tempfile.TemporaryDirectory() as tmpdir:
                req_file = os.path.join(tmpdir, 'requirements.txt')

                with open(req_file, 'w') as f:
                    for dep_name, version, ecosystem in dependencies:
                        if ecosystem and ecosystem.lower() == 'pypi':
                            if version:
                                f.write(f"{dep_name}{version}\n")
                            else:
                                f.write(f"{dep_name}\n")

                # Run scanners on requirements file
                result = {
                    'repository': {
                        'name': name,
                        'url': url,
                        'id': project_id,
                    },
                    'scan_metadata': {
                        'timestamp': datetime.now().isoformat(),
                        'scan_type': 'dependency_only',
                    },
                    'scans': {}
                }

                # Safety scan
                if self.tools_available['safety']:
                    result['scans']['safety'] = self.scan_with_safety(tmpdir)

                # pip-audit scan
                if self.tools_available['pip-audit']:
                    result['scans']['pip_audit'] = self.scan_with_pip_audit(tmpdir)

                result['summary'] = self._calculate_summary(result['scans'])

                # Print summary
                summary = result['summary']
                print(f"   Issues: {summary['total_issues']}")
                print(f"   Risk: {summary['risk_level']}")

                results.append(result)

        conn.close()

        return results

    def save_results(self, results: Any, output_file: str):
        """Save scan results to JSON file."""
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n[+] Results saved to: {output_file}")


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced VulnRecon - Professional Security Scanner"
    )

    parser.add_argument('--target', help='Path to repository to scan')
    parser.add_argument('--database', help='Path to SQLite database')
    parser.add_argument('--limit', type=int, default=5, help='Number of projects to scan from DB')
    parser.add_argument('--output', default='enhanced_results', help='Output directory')

    args = parser.parse_args()

    scanner = EnhancedVulnScanner()

    if args.target:
        # Scan local repository
        result = scanner.scan_repository(args.target)
        output_file = os.path.join(args.output, 'scan_result.json')
        scanner.save_results(result, output_file)

        print(f"\n{'='*70}")
        print("SCAN COMPLETE")
        print(f"{'='*70}")
        print(f"Total Issues: {result['summary']['total_issues']}")
        print(f"Risk Level: {result['summary']['risk_level']}")

    elif args.database:
        # Scan from database
        results = scanner.scan_from_database(args.database, args.limit)
        output_file = os.path.join(args.output, 'database_scan_results.json')
        scanner.save_results(results, output_file)

        print(f"\n{'='*70}")
        print("BATCH SCAN COMPLETE")
        print(f"{'='*70}")
        print(f"Projects Scanned: {len(results)}")

        total_issues = sum(r['summary']['total_issues'] for r in results)
        print(f"Total Issues Found: {total_issues}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
