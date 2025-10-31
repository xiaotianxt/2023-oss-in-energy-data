#!/usr/bin/env python3
"""
Scan all SBOM files with Grype and save vulnerability results in CSV format.
"""

import os
import subprocess
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Thread-safe printing
print_lock = threading.Lock()

def safe_print(message):
    with print_lock:
        print(message, flush=True)

def scan_sbom_with_grype(sbom_file, output_dir):
    """
    Scan an SBOM file with Grype and save results as CSV.
    
    Args:
        sbom_file: Path to the SBOM JSON file
        output_dir: Directory to save CSV output
    
    Returns:
        Tuple of (project_name, status, vuln_count)
    """
    project_name = sbom_file.stem
    output_file = output_dir / f"{project_name}.csv"
    
    safe_print(f"🔍 Scanning {project_name}...")
    
    try:
        # Run Grype with CSV output using template
        result = subprocess.run(
            ['grype', f'sbom:{sbom_file}', '-o', 'template', '-t', '/Users/tian/Develop.localized/2023-oss-in-energy-data/csv_template.tmpl'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            # Save the CSV output
            with open(output_file, 'w') as f:
                f.write(result.stdout)
            
            # Count vulnerabilities (lines minus header)
            lines = result.stdout.strip().split('\n')
            vuln_count = max(0, len(lines) - 1) if lines and lines[0] else 0
            
            if vuln_count == 0:
                safe_print(f"✅ {project_name}: No vulnerabilities found")
                # Still save the CSV with just the header
                return (project_name, 'clean', 0)
            else:
                safe_print(f"⚠️  {project_name}: Found {vuln_count} vulnerabilities")
                return (project_name, 'vulnerable', vuln_count)
        else:
            safe_print(f"❌ {project_name}: Scan failed - {result.stderr.strip()[:100]}")
            return (project_name, 'failed', 0)
            
    except subprocess.TimeoutExpired:
        safe_print(f"⏱️  {project_name}: Scan timed out")
        return (project_name, 'timeout', 0)
    except Exception as e:
        safe_print(f"❌ {project_name}: Error - {str(e)}")
        return (project_name, 'error', 0)

def main():
    sbom_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data/sbom')
    output_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data/csv-vulnerability')
    
    # Get all SBOM JSON files
    sbom_files = sorted(sbom_dir.glob('*.json'))
    total_files = len(sbom_files)
    
    safe_print(f"\n📊 Starting vulnerability scans for {total_files} projects\n")
    safe_print("=" * 80)
    
    results = []
    
    # Use ThreadPoolExecutor for parallel scanning
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_file = {
            executor.submit(scan_sbom_with_grype, sbom_file, output_dir): sbom_file 
            for sbom_file in sbom_files
        }
        
        completed = 0
        for future in as_completed(future_to_file):
            sbom_file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                completed += 1
                if completed % 10 == 0:
                    safe_print(f"\n📈 Progress: {completed}/{total_files} completed\n")
            except Exception as e:
                safe_print(f"❌ Unexpected error processing {sbom_file.name}: {str(e)}")
                results.append((sbom_file.stem, 'error', 0))
    
    # Generate summary report
    safe_print("\n" + "=" * 80)
    safe_print("\n📊 VULNERABILITY SCAN SUMMARY\n")
    safe_print("=" * 80)
    
    clean_count = sum(1 for r in results if r[1] == 'clean')
    vulnerable_count = sum(1 for r in results if r[1] == 'vulnerable')
    failed_count = sum(1 for r in results if r[1] in ['failed', 'timeout', 'error'])
    total_vulns = sum(r[2] for r in results if r[1] == 'vulnerable')
    
    safe_print(f"\n✅ Clean projects (no vulnerabilities):  {clean_count}")
    safe_print(f"⚠️  Vulnerable projects:                  {vulnerable_count}")
    safe_print(f"❌ Failed scans:                          {failed_count}")
    safe_print(f"📊 Total vulnerabilities found:          {total_vulns}")
    safe_print(f"\n📁 Results saved to: {output_dir}/")
    
    # Save summary CSV
    summary_file = output_dir / '_SUMMARY.csv'
    with open(summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Project', 'Status', 'Vulnerability Count'])
        for project, status, count in sorted(results, key=lambda x: (-x[2], x[0])):
            writer.writerow([project, status, count])
    
    safe_print(f"📄 Summary saved to: {summary_file}")
    safe_print("\n" + "=" * 80 + "\n")
    
    # Show top 10 most vulnerable projects
    vulnerable_projects = [(p, c) for p, s, c in results if s == 'vulnerable' and c > 0]
    if vulnerable_projects:
        vulnerable_projects.sort(key=lambda x: -x[1])
        safe_print("\n🔴 TOP 10 MOST VULNERABLE PROJECTS:\n")
        for i, (project, count) in enumerate(vulnerable_projects[:10], 1):
            safe_print(f"  {i:2d}. {project:50s} - {count:4d} vulnerabilities")
        safe_print("")

if __name__ == '__main__':
    main()


