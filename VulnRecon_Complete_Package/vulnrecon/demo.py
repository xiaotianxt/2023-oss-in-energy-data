"""
Demo script showing VulnRecon usage.

This demonstrates how to use VulnRecon to scan the energy projects database
for vulnerabilities, focusing on the most exploitable packages like PyYAML.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vulnrecon.scanner import VulnReconScanner


def demo_scan_specific_projects():
    """Demo: Scan specific high-risk projects."""
    print("\n" + "="*70)
    print("DEMO: Scanning High-Risk Energy Projects for PyYAML Vulnerabilities")
    print("="*70 + "\n")

    # Initialize scanner
    scanner = VulnReconScanner(config_path="config.yaml")

    # Target projects that use PyYAML (from our earlier analysis)
    target_projects = [
        "REopt_API",
        "temoa",
        "the-building-data-genome-project",
        "foxbms-2",
        "gridpath",
    ]

    db_path = "../dependency_analyzer/data/dependencies.db"

    print(f"[*] Database: {db_path}")
    print(f"[*] Target projects: {len(target_projects)}")
    print(f"[*] Focus: PyYAML deserialization vulnerabilities\n")

    results = []

    for project_name in target_projects:
        print(f"\n{'─'*70}")
        print(f"Scanning: {project_name}")
        print(f"{'─'*70}")

        try:
            result = scanner.scan_from_database(
                db_path=db_path,
                project_name=project_name,
                output_dir="demo_results"
            )

            if result:
                results.extend(result)

                # Print findings summary
                project_result = result[0]
                summary = project_result["summary"]

                print(f"\n📊 Results for {project_name}:")
                print(f"   Total Findings: {summary['total_findings']}")
                print(f"   Risk Score: {summary['risk_score']}/10.0")
                print(f"   Risk Level: {summary['risk_level']}")

                if summary['total_findings'] > 0:
                    print(f"\n   Severity Breakdown:")
                    for severity, count in summary['by_severity'].items():
                        if count > 0:
                            print(f"      {severity}: {count}")

                    # Show critical findings
                    critical_findings = [
                        f for f in project_result['findings']
                        if f['severity'] == 'CRITICAL'
                    ]

                    if critical_findings:
                        print(f"\n   🚨 CRITICAL FINDINGS:")
                        for finding in critical_findings[:3]:  # Show first 3
                            print(f"      • {finding['title']}")
                            print(f"        {finding['description'][:100]}...")

        except Exception as e:
            print(f"   ❌ Error scanning {project_name}: {e}")

    # Summary
    print(f"\n\n{'='*70}")
    print("SCAN SUMMARY")
    print(f"{'='*70}")

    if results:
        total_findings = sum(r["summary"]["total_findings"] for r in results)
        avg_risk = sum(r["summary"]["risk_score"] for r in results) / len(results)

        print(f"\n✓ Projects Scanned: {len(results)}")
        print(f"✓ Total Vulnerabilities Found: {total_findings}")
        print(f"✓ Average Risk Score: {avg_risk:.2f}/10.0")

        # Most vulnerable
        most_vulnerable = max(results, key=lambda x: x["summary"]["risk_score"])
        print(f"\n🎯 Most Vulnerable Project:")
        print(f"   Name: {most_vulnerable['repository']['name']}")
        print(f"   Risk Score: {most_vulnerable['summary']['risk_score']}/10.0")
        print(f"   Findings: {most_vulnerable['summary']['total_findings']}")

        print(f"\n💾 Detailed results saved to: demo_results/")
    else:
        print("\n⚠️  No results generated")


def demo_create_test_vulnerable_code():
    """Demo: Create test code with vulnerabilities and scan it."""
    print("\n" + "="*70)
    print("DEMO: Creating and Scanning Vulnerable Test Code")
    print("="*70 + "\n")

    import tempfile
    import shutil

    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix="vulnrecon_test_")
    print(f"[*] Created test directory: {test_dir}")

    try:
        # Create vulnerable Python file
        vuln_file = os.path.join(test_dir, "vulnerable_app.py")
        with open(vuln_file, 'w') as f:
            f.write("""
import yaml
import os
from flask import Flask, request

app = Flask(__name__)

# VULNERABLE: DEBUG mode in production
app.config['DEBUG'] = True

# VULNERABLE: Hardcoded secret key
app.config['SECRET_KEY'] = 'super-secret-key-12345'

@app.route('/parse_yaml', methods=['POST'])
def parse_yaml():
    '''VULNERABLE: Unsafe YAML deserialization'''
    user_data = request.data
    # This allows arbitrary code execution!
    parsed = yaml.load(user_data)  # UNSAFE!
    return str(parsed)

@app.route('/fetch_url', methods=['GET'])
def fetch_url():
    '''VULNERABLE: SSRF vulnerability'''
    import requests
    url = request.args.get('url')
    # No validation - attacker can access internal resources!
    response = requests.get(url, verify=False)  # Also disables SSL!
    return response.text

if __name__ == '__main__':
    app.run(host='0.0.0.0')  # Exposed to all interfaces
""")

        # Create requirements.txt
        req_file = os.path.join(test_dir, "requirements.txt")
        with open(req_file, 'w') as f:
            f.write("""
Flask==2.0.1
PyYAML==5.3.1
requests==2.25.0
Pillow==8.0.0
""")

        print(f"[*] Created vulnerable application files")
        print(f"[*] Vulnerabilities planted:")
        print(f"    - Unsafe PyYAML deserialization")
        print(f"    - Django DEBUG=True")
        print(f"    - Hardcoded SECRET_KEY")
        print(f"    - SSRF vulnerability")
        print(f"    - Disabled SSL verification")
        print(f"    - Multiple vulnerable dependency versions")

        # Scan the vulnerable code
        print(f"\n[*] Scanning vulnerable code...\n")

        scanner = VulnReconScanner(config_path="config.yaml")
        result = scanner.scan_repository(test_dir, "test://vulnerable-app")

        # Display results
        print(f"\n{'='*70}")
        print("SCAN RESULTS")
        print(f"{'='*70}")

        summary = result["summary"]
        print(f"\n🔍 Analysis Complete!")
        print(f"   Total Vulnerabilities Found: {summary['total_findings']}")
        print(f"   Risk Score: {summary['risk_score']}/10.0")
        print(f"   Risk Level: {summary['risk_level']}")

        print(f"\n📊 Findings by Severity:")
        for severity, count in summary['by_severity'].items():
            if count > 0:
                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "INFO": "⚪"}
                print(f"   {emoji.get(severity, '•')} {severity}: {count}")

        print(f"\n🔎 Detailed Findings:\n")
        for i, finding in enumerate(result['findings'][:5], 1):
            print(f"{i}. [{finding['severity']}] {finding['title']}")
            if finding.get('file_path'):
                print(f"   File: {os.path.basename(finding['file_path'])}")
                if finding.get('line_number'):
                    print(f"   Line: {finding['line_number']}")
            if finding.get('code_snippet'):
                print(f"   Code: {finding['code_snippet'][:80]}")
            print(f"   Description: {finding['description'][:150]}...")
            if finding.get('remediation'):
                print(f"   Fix: {finding['remediation'][:100]}...")
            print()

        # Save results
        import json
        output_file = "demo_results/vulnerable_app_scan.json"
        os.makedirs("demo_results", exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"💾 Full report saved to: {output_file}")

    finally:
        # Cleanup
        print(f"\n[*] Cleaning up test directory...")
        shutil.rmtree(test_dir)
        print(f"[*] Cleanup complete")


def main():
    """Run demos."""
    print("""
╦  ╦╦ ╦╦  ╔╗╔╦═╗╔═╗╔═╗╔═╗╔╗╔
╚╗╔╝║ ║║  ║║║╠╦╝║╣ ║  ║ ║║║║
 ╚╝ ╚═╝╩═╝╝╚╝╩╚═╚═╝╚═╝╚═╝╝╚╝
    Demo Script - VulnRecon
    """)

    print("This demo shows VulnRecon's capabilities for automated")
    print("vulnerability reconnaissance and security testing.")
    print("\nSelect a demo to run:\n")
    print("1. Scan high-risk energy projects from database")
    print("2. Create and scan vulnerable test code")
    print("3. Run both demos")
    print("0. Exit")

    choice = input("\nEnter choice (0-3): ").strip()

    if choice == "1":
        demo_scan_specific_projects()
    elif choice == "2":
        demo_create_test_vulnerable_code()
    elif choice == "3":
        demo_create_test_vulnerable_code()
        demo_scan_specific_projects()
    else:
        print("\nExiting...")
        return

    print("\n" + "="*70)
    print("Demo complete! Check the demo_results/ directory for full reports.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
