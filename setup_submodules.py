#!/usr/bin/env python3
"""
Script to add all projects from projects.csv as git submodules
"""

import csv
import subprocess
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

def sanitize_name(name):
    """Sanitize project name to create valid directory name"""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()

def add_submodule(project_name, repo_url, submodules_dir):
    """Add a single git submodule"""
    if not repo_url or repo_url.strip() == '':
        return (project_name, 'skipped', 'No repository URL')
    
    safe_name = sanitize_name(project_name)
    submodule_path = submodules_dir / safe_name
    
    # Check if submodule already exists
    if submodule_path.exists():
        return (project_name, 'exists', f'Already exists at {submodule_path}')
    
    print(f"📥 Adding {project_name}...")
    
    try:
        # Add submodule with depth 1 for shallow clone
        result = subprocess.run(
            [
                'git', 'submodule', 'add',
                '--depth', '1',
                '--', repo_url,
                str(submodule_path)
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd='/Users/tian/Develop.localized/2023-oss-in-energy-data'
        )
        
        if result.returncode == 0:
            print(f"✅ Added {project_name}")
            return (project_name, 'success', str(submodule_path))
        else:
            error = result.stderr[:150] if result.stderr else 'Unknown error'
            print(f"❌ Failed to add {project_name}: {error}")
            return (project_name, 'failed', error)
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout adding {project_name}")
        return (project_name, 'timeout', 'Timeout during clone')
    except Exception as e:
        print(f"❌ Error adding {project_name}: {str(e)}")
        return (project_name, 'error', str(e))

def main():
    base_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data')
    csv_file = base_dir / 'projects.csv'
    submodules_dir = base_dir / 'repos'
    
    # Create repos directory
    submodules_dir.mkdir(exist_ok=True)
    
    # Read projects from CSV
    projects = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            project_name = row.get('Project', '').strip()
            repo_url = row.get('Repository URL', '').strip()
            if project_name and repo_url:
                projects.append((project_name, repo_url))
    
    print(f"📊 Found {len(projects)} projects to add as submodules\n")
    print(f"📁 Submodules will be added to: {submodules_dir}\n")
    
    # Process projects in parallel
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
        'exists': [],
        'timeout': [],
        'error': []
    }
    
    # Use ThreadPoolExecutor for parallel git operations
    max_workers = 10  # Limit concurrent git operations
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_project = {
            executor.submit(add_submodule, name, url, submodules_dir): name
            for name, url in projects
        }
        
        # Process completed tasks
        for future in as_completed(future_to_project):
            project_name, status, message = future.result()
            results[status].append((project_name, message))
    
    # Summary
    print("\n" + "="*70)
    print("📈 Submodule Addition Summary:")
    print(f"   Total projects: {len(projects)}")
    print(f"   ✅ Successfully added: {len(results['success'])}")
    print(f"   📁 Already existed: {len(results['exists'])}")
    print(f"   ❌ Failed: {len(results['failed'])}")
    print(f"   ⏭️  Skipped: {len(results['skipped'])}")
    print(f"   ⏱️  Timeout: {len(results['timeout'])}")
    print(f"   ⚠️  Error: {len(results['error'])}")
    print("="*70)
    
    # Show failed projects
    if results['failed']:
        print("\n❌ Failed projects:")
        for name, error in results['failed'][:10]:  # Show first 10
            print(f"   - {name}: {error}")
        if len(results['failed']) > 10:
            print(f"   ... and {len(results['failed']) - 10} more")

if __name__ == '__main__':
    main()


