#!/usr/bin/env python3
"""
Clone remaining vulnerable repositories that weren't cloned yet.
Matches by comparing sanitized folder names (case-insensitive).
"""

import csv
import subprocess
import sys
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Thread-safe print
print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

def sanitize_name(name):
    """Sanitize name to match scan results format."""
    # Convert to lowercase and replace spaces/special chars with hyphens
    sanitized = name.lower()
    sanitized = re.sub(r'[^\w\s-]', '', sanitized)
    sanitized = re.sub(r'[-\s]+', '-', sanitized)
    return sanitized.strip('-')

def get_repo_name_from_url(url):
    """Extract repository name from GitHub URL."""
    parts = url.rstrip('/').rstrip('.git').split('/')
    return parts[-1]

def load_vulnerable_and_cloned():
    """Load vulnerable projects and already cloned ones."""
    # Load vulnerable projects
    summary_file = Path('csv-vulnerability/_SUMMARY.csv')
    vulnerable = set()
    with open(summary_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Status'] == 'vulnerable':
                vulnerable.add(row['Project'])
    
    # Load already cloned
    repos_dir = Path('repos')
    cloned = set()
    if repos_dir.exists():
        cloned = set(d.name.lower() for d in repos_dir.iterdir() if d.is_dir())
    
    # Find missing (case-insensitive comparison)
    missing = set()
    for v in vulnerable:
        if v.lower() not in cloned:
            missing.add(v)
    
    return missing

def clone_with_sparse_checkout(url, path, project_name):
    """Clone repository with sparse checkout and depth 1."""
    try:
        path_obj = Path(path)
        
        # Check if already exists
        if path_obj.exists() and (path_obj / '.git').exists():
            return True, "exists"
        
        # Remove if exists but not a git repo
        if path_obj.exists():
            import shutil
            shutil.rmtree(path_obj)
        
        # Initialize git repo
        path_obj.mkdir(parents=True, exist_ok=True)
        
        result = subprocess.run(
            ['git', 'init'],
            cwd=path,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return False, "init_failed"
        
        # Enable sparse checkout
        subprocess.run(
            ['git', 'config', 'core.sparseCheckout', 'true'],
            cwd=path,
            capture_output=True
        )
        
        # Define sparse-checkout patterns
        sparse_checkout_file = path_obj / '.git' / 'info' / 'sparse-checkout'
        sparse_checkout_file.parent.mkdir(parents=True, exist_ok=True)
        
        patterns = """/*
!*.csv
!*.tsv
!*.parquet
!*.hdf5
!*.h5
!*.xlsx
!*.db
!*.sqlite
!*.pkl
!*.npy
!*.npz
!*.mp4
!*.avi
!*.zip
!*.tar.gz
!data/*.png
!data/*.jpg
!datasets/*.png
"""
        
        with open(sparse_checkout_file, 'w') as f:
            f.write(patterns)
        
        # Add remote and fetch
        subprocess.run(['git', 'remote', 'add', 'origin', url], cwd=path, capture_output=True)
        
        safe_print(f"  📥 Fetching: {project_name}")
        result = subprocess.run(
            ['git', 'fetch', '--depth', '1', 'origin', 'HEAD'],
            cwd=path,
            capture_output=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return False, "fetch_failed"
        
        # Checkout
        result = subprocess.run(
            ['git', 'checkout', 'FETCH_HEAD'],
            cwd=path,
            capture_output=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return False, "checkout_failed"
        
        # Get size
        size_result = subprocess.run(['du', '-sh', path], capture_output=True, text=True)
        size = size_result.stdout.split()[0] if size_result.returncode == 0 else "?"
        
        safe_print(f"  ✅ {project_name} ({size})")
        return True, "success"
        
    except subprocess.TimeoutExpired:
        safe_print(f"  ⏱️  Timeout: {project_name}")
        return False, "timeout"
    except Exception as e:
        safe_print(f"  ❌ {project_name}: {str(e)[:50]}")
        return False, "error"

def process_repository(repo_info):
    """Process a single repository."""
    return (
        repo_info['name'],
        clone_with_sparse_checkout(repo_info['url'], repo_info['path'], repo_info['name'])
    )

def main():
    safe_print("🔍 Finding remaining vulnerable repositories to clone...\n")
    
    # Load missing vulnerable projects
    missing_vulnerable = load_vulnerable_and_cloned()
    safe_print(f"📊 Found {len(missing_vulnerable)} repositories to clone\n")
    
    if not missing_vulnerable:
        safe_print("✅ All vulnerable repositories already cloned!")
        return
    
    # Load projects.csv and match by sanitized names
    projects_file = Path('projects.csv')
    repos_dir = Path('repos')
    repos_dir.mkdir(exist_ok=True)
    
    # Build mapping: sanitized_name -> (original_name, url)
    project_mapping = {}
    with open(projects_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            url = row.get('Repository URL', '').strip()
            if not url:
                continue
            
            # Get folder name from URL
            folder_name = get_repo_name_from_url(url)
            sanitized = sanitize_name(folder_name)
            
            project_mapping[sanitized] = {
                'name': row.get('Project', '').strip(),
                'url': url,
                'folder': folder_name
            }
    
    # Match missing vulnerable repos to URLs
    repositories = []
    not_found = []
    
    for missing in missing_vulnerable:
        sanitized_missing = sanitize_name(missing)
        
        if sanitized_missing in project_mapping:
            info = project_mapping[sanitized_missing]
            repo_path = repos_dir / info['folder']
            repositories.append({
                'name': info['name'],
                'url': info['url'],
                'path': str(repo_path)
            })
        else:
            not_found.append(missing)
    
    safe_print(f"✅ Matched {len(repositories)} repositories")
    if not_found:
        safe_print(f"⚠️  Could not find URLs for {len(not_found)} projects")
        safe_print(f"   First 5: {', '.join(list(not_found)[:5])}\n")
    
    if not repositories:
        safe_print("❌ No repositories to clone!")
        return
    
    safe_print(f"\n🚀 Starting to clone {len(repositories)} repositories...\n")
    safe_print("=" * 80 + "\n")
    
    # Clone in parallel
    success_count = 0
    failed_count = 0
    exists_count = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_repo = {executor.submit(process_repository, repo): repo for repo in repositories}
        
        for i, future in enumerate(as_completed(future_to_repo), 1):
            try:
                name, (success, status) = future.result()
                
                if status == "exists":
                    exists_count += 1
                elif success:
                    success_count += 1
                else:
                    failed_count += 1
                
                if i % 10 == 0 or i == len(repositories):
                    safe_print(f"\n{'─' * 80}")
                    safe_print(f"📈 {i}/{len(repositories)} | ✅ {success_count} | ⏭️  {exists_count} | ❌ {failed_count}")
                    safe_print(f"{'─' * 80}\n")
                    
            except Exception as e:
                safe_print(f"❌ Task error: {str(e)}")
                failed_count += 1
    
    # Summary
    safe_print("\n" + "=" * 80)
    safe_print("\n📊 FINAL SUMMARY\n")
    safe_print("=" * 80)
    safe_print(f"✅ Successfully cloned:  {success_count}")
    safe_print(f"⏭️  Already existed:     {exists_count}")
    safe_print(f"❌ Failed:              {failed_count}")
    
    # Total space
    size_result = subprocess.run(['du', '-sh', 'repos/'], capture_output=True, text=True)
    if size_result.returncode == 0:
        safe_print(f"\n💾 Total repos size: {size_result.stdout.split()[0]}")
    
    safe_print("\n" + "=" * 80)
    safe_print("\n✨ Done!\n")

if __name__ == '__main__':
    main()


