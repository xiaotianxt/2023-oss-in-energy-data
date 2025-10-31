#!/usr/bin/env python3
"""
Script to scan all cloned repositories using Syft and generate SBOMs in parallel
"""

import csv
import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def sanitize_name(name):
    """Sanitize project name to create valid directory name"""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()

def scan_repository(project_name, repo_dir, output_dir):
    """Scan a repository using Syft"""
    safe_name = sanitize_name(project_name)
    output_file = output_dir / f"{safe_name}.json"
    
    # Check if already scanned
    if output_file.exists():
        print(f"⏭️  {project_name}: Already scanned")
        return (project_name, 'skipped', 'Already scanned')
    
    # Check if repository exists
    if not repo_dir.exists():
        print(f"⚠️  {project_name}: Repository not found")
        return (project_name, 'not_found', 'Repository directory not found')
    
    print(f"🔍 Scanning {project_name}...")
    
    try:
        # Scan the repository with Syft
        result = subprocess.run(
            ['syft', f'dir:{repo_dir}', '-o', f'json={output_file}', '-q'],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {project_name}: Scanned successfully")
            return (project_name, 'success', str(output_file))
        else:
            error = result.stderr[:150] if result.stderr else 'Unknown error'
            print(f"❌ {project_name}: Failed - {error}")
            return (project_name, 'failed', error)
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  {project_name}: Timeout")
        return (project_name, 'timeout', 'Scanning timeout')
    except Exception as e:
        print(f"❌ {project_name}: Error - {str(e)}")
        return (project_name, 'error', str(e))

def main():
    base_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data')
    csv_file = base_dir / 'projects.csv'
    repos_dir = base_dir / 'repos'
    output_dir = base_dir / 'sbom'
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Read projects from CSV
    projects = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            project_name = row.get('Project', '').strip()
            if project_name:
                safe_name = sanitize_name(project_name)
                repo_path = repos_dir / safe_name
                projects.append((project_name, repo_path))
    
    print(f"📊 Found {len(projects)} projects to scan")
    print(f"📁 Scanning from: {repos_dir}")
    print(f"💾 Output directory: {output_dir}\n")
    
    # Process projects in parallel
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'not_found': [],
        'timeout': [],
        'error': []
    }
    
    # Use ThreadPoolExecutor for parallel scanning
    max_workers = 8  # Adjust based on your CPU cores
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_project = {
            executor.submit(scan_repository, name, path, output_dir): name
            for name, path in projects
        }
        
        # Process completed tasks
        completed = 0
        total = len(projects)
        
        for future in as_completed(future_to_project):
            completed += 1
            project_name, status, message = future.result()
            results[status].append((project_name, message))
            
            # Progress indicator
            if completed % 10 == 0:
                print(f"\n📊 Progress: {completed}/{total} completed\n")
    
    # Summary
    print("\n" + "="*70)
    print("📈 Scan Summary:")
    print(f"   Total projects: {len(projects)}")
    print(f"   ✅ Successfully scanned: {len(results['success'])}")
    print(f"   ⏭️  Already scanned: {len(results['skipped'])}")
    print(f"   📂 Repository not found: {len(results['not_found'])}")
    print(f"   ❌ Failed: {len(results['failed'])}")
    print(f"   ⏱️  Timeout: {len(results['timeout'])}")
    print(f"   ⚠️  Error: {len(results['error'])}")
    print(f"\n📁 SBOMs saved to: {output_dir}")
    print("="*70)
    
    # Show some failed projects
    if results['failed']:
        print("\n❌ Some failed projects:")
        for name, error in results['failed'][:5]:
            print(f"   - {name}: {error}")
        if len(results['failed']) > 5:
            print(f"   ... and {len(results['failed']) - 5} more")
    
    # Show some not found projects
    if results['not_found']:
        print(f"\n📂 {len(results['not_found'])} repositories not found (need to clone first)")

if __name__ == '__main__':
    main()


