"""Main vulnerability scanner orchestrator."""

import os
import sys
import sqlite3
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .detectors import (
    PyYAMLDetector,
    DjangoDetector,
    PillowDetector,
    RequestsDetector,
    Finding,
)


class VulnReconScanner:
    """Main vulnerability reconnaissance scanner."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the scanner.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.detectors = self._initialize_detectors()
        self.findings: List[Finding] = []

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {config_path} not found, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "detectors": {
                "enabled": ["pyyaml", "django", "pillow", "requests"],
                "pyyaml": {"enabled": True, "vulnerable_versions": "<5.4"},
                "django": {"enabled": True},
                "pillow": {"enabled": True, "vulnerable_versions": "<10.0.0"},
                "requests": {"enabled": True},
            },
            "general": {
                "output_directory": "results",
            },
        }

    def _initialize_detectors(self) -> List:
        """Initialize all enabled detectors."""
        detectors = []
        detector_config = self.config.get("detectors", {})
        enabled = detector_config.get("enabled", [])

        detector_classes = {
            "pyyaml": PyYAMLDetector,
            "django": DjangoDetector,
            "pillow": PillowDetector,
            "requests": RequestsDetector,
        }

        for detector_name in enabled:
            if detector_name in detector_classes:
                config = detector_config.get(detector_name, {})
                detector = detector_classes[detector_name](config)
                if detector.is_enabled():
                    detectors.append(detector)
                    print(f"[+] Loaded detector: {detector.get_name()}")

        return detectors

    def scan_repository(self, repo_path: str, repo_url: str = None) -> Dict[str, Any]:
        """
        Scan a repository for vulnerabilities.

        Args:
            repo_path: Local path to repository
            repo_url: URL of the repository (optional)

        Returns:
            Scan results dictionary
        """
        print(f"\n[*] Scanning repository: {repo_path}")
        print(f"[*] Timestamp: {datetime.now().isoformat()}")

        # Get dependencies from repository
        dependencies = self._get_dependencies(repo_path)
        print(f"[*] Found {len(dependencies)} dependencies")

        # Run all detectors
        all_findings = []
        for detector in self.detectors:
            print(f"[*] Running {detector.get_name()}...")
            try:
                findings = detector.detect(repo_path, dependencies)
                all_findings.extend(findings)
                print(f"    Found {len(findings)} issues")
            except Exception as e:
                print(f"    Error: {e}")

        # Calculate risk score
        risk_score = self._calculate_risk_score(all_findings)

        # Create scan result
        result = {
            "repository": {
                "path": repo_path,
                "url": repo_url,
            },
            "scan_metadata": {
                "timestamp": datetime.now().isoformat(),
                "scanner_version": "0.1.0",
                "detectors_used": [d.get_name() for d in self.detectors],
            },
            "summary": {
                "total_findings": len(all_findings),
                "by_severity": self._count_by_severity(all_findings),
                "risk_score": risk_score,
                "risk_level": self._get_risk_level(risk_score),
            },
            "findings": [f.to_dict() for f in all_findings],
            "dependencies": dependencies,
        }

        self.findings = all_findings
        return result

    def scan_from_database(
        self,
        db_path: str,
        project_name: Optional[str] = None,
        output_dir: str = "results"
    ) -> List[Dict[str, Any]]:
        """
        Scan projects from the dependency database.

        Args:
            db_path: Path to SQLite database
            project_name: Specific project to scan (None for all)
            output_dir: Directory to save results

        Returns:
            List of scan results
        """
        print(f"[*] Connecting to database: {db_path}")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get projects to scan
        if project_name:
            cursor.execute(
                "SELECT id, name, url FROM projects WHERE name = ?",
                (project_name,)
            )
        else:
            cursor.execute("SELECT id, name, url FROM projects LIMIT 20")

        projects = cursor.fetchall()
        print(f"[*] Found {len(projects)} projects to scan")

        results = []

        for project_id, name, url in projects:
            print(f"\n{'='*60}")
            print(f"Scanning: {name}")
            print(f"URL: {url}")

            # Get dependencies for this project
            cursor.execute(
                """
                SELECT dependency_name, version_spec, ecosystem
                FROM dependencies
                WHERE project_id = ?
                """,
                (project_id,)
            )

            dependencies = [
                {
                    "dependency_name": dep[0],
                    "version_spec": dep[1],
                    "ecosystem": dep[2],
                }
                for dep in cursor.fetchall()
            ]

            # Create a mock scan (we don't have local code)
            all_findings = []

            for detector in self.detectors:
                try:
                    # Detectors will only check dependency versions
                    findings = detector.detect("", dependencies)
                    all_findings.extend(findings)
                except Exception as e:
                    print(f"    Error in {detector.get_name()}: {e}")

            risk_score = self._calculate_risk_score(all_findings)

            result = {
                "repository": {
                    "name": name,
                    "url": url,
                    "id": project_id,
                },
                "scan_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "scanner_version": "0.1.0",
                    "scan_type": "database_only",
                },
                "summary": {
                    "total_findings": len(all_findings),
                    "by_severity": self._count_by_severity(all_findings),
                    "risk_score": risk_score,
                    "risk_level": self._get_risk_level(risk_score),
                },
                "findings": [f.to_dict() for f in all_findings],
                "dependencies": dependencies,
            }

            results.append(result)

            # Save individual result
            self._save_result(result, output_dir, name)

        conn.close()

        # Save summary report
        self._save_summary_report(results, output_dir)

        return results

    def _get_dependencies(self, repo_path: str) -> List[Dict[str, Any]]:
        """Extract dependencies from repository."""
        dependencies = []

        # Look for requirements.txt
        req_file = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_file):
            dependencies.extend(self._parse_requirements_txt(req_file))

        # Look for package.json
        pkg_file = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg_file):
            dependencies.extend(self._parse_package_json(pkg_file))

        return dependencies

    def _parse_requirements_txt(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse Python requirements.txt file."""
        dependencies = []

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Simple parsing (doesn't handle all edge cases)
                        if '==' in line:
                            name, version = line.split('==')
                            dependencies.append({
                                "dependency_name": name.strip(),
                                "version_spec": version.strip(),
                                "ecosystem": "pypi",
                            })
                        else:
                            dependencies.append({
                                "dependency_name": line.split('>=')[0].split('<')[0].strip(),
                                "version_spec": "",
                                "ecosystem": "pypi",
                            })
        except Exception as e:
            print(f"Error parsing requirements.txt: {e}")

        return dependencies

    def _parse_package_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse Node.js package.json file."""
        dependencies = []

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            for dep_name, dep_version in data.get("dependencies", {}).items():
                dependencies.append({
                    "dependency_name": dep_name,
                    "version_spec": dep_version.strip('^~'),
                    "ecosystem": "npm",
                })

        except Exception as e:
            print(f"Error parsing package.json: {e}")

        return dependencies

    def _calculate_risk_score(self, findings: List[Finding]) -> float:
        """Calculate overall risk score."""
        if not findings:
            return 0.0

        severity_weights = {
            "CRITICAL": 10.0,
            "HIGH": 7.5,
            "MEDIUM": 5.0,
            "LOW": 2.5,
            "INFO": 0.0,
        }

        total_score = sum(
            severity_weights.get(f.severity.value, 0) * f.confidence
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

    def _count_by_severity(self, findings: List[Finding]) -> Dict[str, int]:
        """Count findings by severity."""
        counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }

        for finding in findings:
            counts[finding.severity.value] += 1

        return counts

    def _save_result(self, result: Dict[str, Any], output_dir: str, name: str):
        """Save scan result to file."""
        os.makedirs(output_dir, exist_ok=True)

        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_'))
        filename = os.path.join(output_dir, f"{safe_name}_scan.json")

        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"[+] Saved results to: {filename}")

    def _save_summary_report(self, results: List[Dict[str, Any]], output_dir: str):
        """Save summary report of all scans."""
        summary = {
            "scan_date": datetime.now().isoformat(),
            "total_projects_scanned": len(results),
            "aggregate_stats": {
                "total_findings": sum(r["summary"]["total_findings"] for r in results),
                "average_risk_score": round(
                    sum(r["summary"]["risk_score"] for r in results) / len(results), 2
                ) if results else 0.0,
            },
            "top_vulnerable_projects": sorted(
                [
                    {
                        "name": r["repository"].get("name", "Unknown"),
                        "risk_score": r["summary"]["risk_score"],
                        "findings": r["summary"]["total_findings"],
                    }
                    for r in results
                ],
                key=lambda x: x["risk_score"],
                reverse=True
            )[:10],
            "projects": results,
        }

        filename = os.path.join(output_dir, "summary_report.json")
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n[+] Saved summary report to: {filename}")
        print(f"[+] Total projects scanned: {len(results)}")
        print(f"[+] Total findings: {summary['aggregate_stats']['total_findings']}")
