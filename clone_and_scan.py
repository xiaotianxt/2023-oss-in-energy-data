#!/usr/bin/env python3
"""
Script to clone all repositories and scan them with Syft in parallel
"""

import csv
import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Thread-safe printing
print_lock = threading.Lock()

def safe_print(message):
    """Thread-safe printing"""
    with print_lock:
        print(message, flush=True)

def sanitize_name(name):
    """Sanitize project name to create valid directory name"""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()

def clone_repository(project_name, repo_url, repos_dir):
    """Clone a repository if it doesn't exist"""
    safe_name = sanitize_name(project_name)
    repo_path = repos_dir / safe_name
    
    # Check if already cloned
    if repo_path.exists() and (repo_path / '.git').exists():
        safe_print(f"⏭️  {project_name}: Already cloned")
        return (project_name, 'exists', repo_path)
    
    safe_print(f"📥 Cloning {project_name}...")
    
    try:
        # Clone with depth 1 and single-branch for minimal clone (only HEAD commit)
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', '--single-branch', '--quiet', repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes for cloning
        )
        
        if result.returncode == 0:
            safe_print(f"✅ {project_name}: Cloned successfully")
            return (project_name, 'cloned', repo_path)
        else:
            error = result.stderr[:100] if result.stderr else 'Unknown error'
            safe_print(f"❌ {project_name}: Clone failed - {error}")
            return (project_name, 'clone_failed', None)
            
    except subprocess.TimeoutExpired:
        safe_print(f"⏱️  {project_name}: Clone timeout")
        return (project_name, 'clone_timeout', None)
    except Exception as e:
        safe_print(f"❌ {project_name}: Clone error - {str(e)[:100]}")
        return (project_name, 'clone_error', None)

def scan_repository(project_name, repo_path, output_dir):
    """Scan a repository with Syft"""
    if not repo_path or not repo_path.exists():
        return (project_name, 'no_repo', 'Repository not available')
    
    safe_name = sanitize_name(project_name)
    output_file = output_dir / f"{safe_name}.json"
    
    # Check if already scanned
    if output_file.exists():
        safe_print(f"⏭️  {project_name}: Already scanned")
        return (project_name, 'scan_exists', output_file)
    
    safe_print(f"🔍 Scanning {project_name}...")
    
    try:
        result = subprocess.run(
            ['syft', f'dir:{repo_path}', '-o', f'json={output_file}', '-q'],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            safe_print(f"✅ {project_name}: Scan complete")
            return (project_name, 'scan_success', output_file)
        else:
            error = result.stderr[:100] if result.stderr else 'Unknown error'
            safe_print(f"❌ {project_name}: Scan failed - {error}")
            return (project_name, 'scan_failed', None)
            
    except subprocess.TimeoutExpired:
        safe_print(f"⏱️  {project_name}: Scan timeout")
        return (project_name, 'scan_timeout', None)
    except Exception as e:
        safe_print(f"❌ {project_name}: Scan error - {str(e)[:100]}")
        return (project_name, 'scan_error', None)

def process_project(project_name, repo_url, repos_dir, output_dir):
    """Clone and scan a single project"""
    # First clone
    clone_name, clone_status, repo_path = clone_repository(project_name, repo_url, repos_dir)
    
    # If clone successful or already exists, scan it
    if clone_status in ['cloned', 'exists'] and repo_path:
        scan_name, scan_status, scan_path = scan_repository(project_name, repo_path, output_dir)
        return {
            'name': project_name,
            'clone_status': clone_status,
            'scan_status': scan_status,
            'repo_path': repo_path,
            'scan_path': scan_path
        }
    else:
        return {
            'name': project_name,
            'clone_status': clone_status,
            'scan_status': 'skipped',
            'repo_path': None,
            'scan_path': None
        }

def main():
    base_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data')
    csv_file = base_dir / 'projects.csv'
    repos_dir = base_dir / 'repos'
    output_dir = base_dir / 'sbom'
    
    # Create directories
    repos_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Read projects from CSV
    projects = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            project_name = row.get('Project', '').strip()
            repo_url = row.get('Repository URL', '').strip()
            if project_name and repo_url:
                projects.append((project_name, repo_url))
    
    safe_print(f"📊 Found {len(projects)} projects")
    safe_print(f"📁 Repos directory: {repos_dir}")
    safe_print(f"💾 SBOM directory: {output_dir}\n")
    
    # Process projects in parallel
    results = []
    max_workers = 6  # Parallel clone + scan operations
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_project = {
            executor.submit(process_project, name, url, repos_dir, output_dir): (name, url)
            for name, url in projects
        }
        
        # Process completed tasks
        completed = 0
        total = len(projects)
        
        for future in as_completed(future_to_project):
            completed += 1
            result = future.result()
            results.append(result)
            
            # Progress indicator every 20 projects
            if completed % 20 == 0:
                safe_print(f"\n📊 Progress: {completed}/{total} projects processed\n")
    
    # Analyze results
    clone_stats = {}
    scan_stats = {}
    
    for r in results:
        clone_status = r['clone_status']
        scan_status = r['scan_status']
        
        clone_stats[clone_status] = clone_stats.get(clone_status, 0) + 1
        scan_stats[scan_status] = scan_stats.get(scan_status, 0) + 1
    
    # Summary
    print("\n" + "="*70)
    print("📈 Final Summary:")
    print(f"   Total projects: {len(projects)}")
    print("\n📥 Clone Statistics:")
    for status, count in sorted(clone_stats.items()):
        print(f"   {status}: {count}")
    print("\n🔍 Scan Statistics:")
    for status, count in sorted(scan_stats.items()):
        print(f"   {status}: {count}")
    print(f"\n📁 Repositories: {repos_dir}")
    print(f"💾 SBOMs: {output_dir}")
    print("="*70)
    
    # Count successful scans
    successful_scans = sum(1 for r in results if r['scan_status'] in ['scan_success', 'scan_exists'])
    print(f"\n✅ Total SBOMs generated: {successful_scans}")

if __name__ == '__main__':
    main()

