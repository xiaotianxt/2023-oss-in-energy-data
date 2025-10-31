#!/usr/bin/env python3
"""
Smart cloning of vulnerable repositories with sparse checkout.
Only clones repositories with vulnerabilities and excludes large data files.
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

def sanitize_folder_name(name):
    """Convert project name to valid folder name."""
    sanitized = re.sub(r'[^\w\s-]', '', name.lower())
    sanitized = re.sub(r'[-\s]+', '-', sanitized)
    return sanitized.strip('-')

def get_repo_name_from_url(url):
    """Extract repository name from GitHub URL."""
    parts = url.rstrip('/').rstrip('.git').split('/')
    return parts[-1]

def load_vulnerable_projects():
    """Load list of projects with vulnerabilities from summary CSV."""
    summary_file = Path('csv-vulnerability/_SUMMARY.csv')
    if not summary_file.exists():
        safe_print("❌ csv-vulnerability/_SUMMARY.csv not found!")
        return set()
    
    vulnerable_projects = set()
    with open(summary_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Status'] == 'vulnerable':
                # Store the sanitized name from _SUMMARY.csv
                vulnerable_projects.add(row['Project'])
    
    return vulnerable_projects

def clone_with_sparse_checkout(url, path, project_name):
    """
    Clone repository with sparse checkout, excluding large data files.
    Uses --depth 1 for shallow clone to save space.
    """
    try:
        path_obj = Path(path)
        
        # Check if already exists
        if path_obj.exists() and (path_obj / '.git').exists():
            safe_print(f"  ⏭️  Already exists: {project_name}")
            return True, "exists"
        
        # Remove if exists but not a git repo
        if path_obj.exists():
            import shutil
            shutil.rmtree(path_obj)
        
        # Initialize git repo with sparse checkout
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Initialize git
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
        
        # Patterns: Include everything EXCEPT large data files
        patterns = """# Include all files by default
/*

# Exclude large data files and datasets
!*.csv
!*.tsv
!*.parquet
!*.feather
!*.hdf5
!*.h5
!*.xlsx
!*.xls

# Exclude large binary data
!*.db
!*.sqlite
!*.sqlite3
!*.pkl
!*.pickle
!*.npy
!*.npz

# Exclude media files
!*.mp4
!*.avi
!*.mov
!*.mkv
!*.mp3
!*.wav
!*.flac
!*.zip
!*.tar
!*.tar.gz
!*.tgz
!*.rar
!*.7z

# Exclude large image datasets
!data/*.png
!data/*.jpg
!data/*.jpeg
!datasets/*.png
!datasets/*.jpg
!datasets/*.jpeg

# But INCLUDE dependency and config files (override exclusions)
!**/requirements*.txt
!**/package*.json
!**/yarn.lock
!**/Pipfile*
!**/poetry.lock
!**/*pom.xml
!**/build.gradle*
!**/Cargo.toml
!**/Cargo.lock
!**/go.mod
!**/go.sum
!**/*.gemspec
!**/Gemfile*
!**/setup.py
!**/setup.cfg
!**/pyproject.toml
!**/*.cabal
!**/stack.yaml
!**/Project.toml
!**/Manifest.toml
!**/shard.yml

# Include all source code files
!**/*.py
!**/*.js
!**/*.ts
!**/*.java
!**/*.c
!**/*.cpp
!**/*.h
!**/*.hpp
!**/*.rs
!**/*.go
!**/*.rb
!**/*.php
!**/*.cs
!**/*.swift
!**/*.kt
!**/*.scala
!**/*.jl
!**/*.r
!**/*.R
!**/*.m
!**/*.sh
!**/*.bash

# Include documentation
!**/*.md
!**/*.rst
!**/*.txt
!LICENSE*
!README*

# Include configuration files
!**/*.yml
!**/*.yaml
!**/*.toml
!**/*.ini
!**/*.cfg
!**/*.conf
!**/*.json
!**/Makefile
!**/makefile
!**/Dockerfile
!**/.gitignore
!**/.dockerignore
"""
        
        with open(sparse_checkout_file, 'w') as f:
            f.write(patterns)
        
        # Add remote
        subprocess.run(
            ['git', 'remote', 'add', 'origin', url],
            cwd=path,
            capture_output=True
        )
        
        # Fetch with depth 1 (shallow)
        safe_print(f"  📥 Fetching (shallow): {project_name}")
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
        
        # Get actual size
        size_result = subprocess.run(
            ['du', '-sh', path],
            capture_output=True,
            text=True
        )
        size = size_result.stdout.split()[0] if size_result.returncode == 0 else "?"
        
        safe_print(f"  ✅ Success: {project_name} ({size})")
        return True, "success"
        
    except subprocess.TimeoutExpired:
        safe_print(f"  ⏱️  Timeout: {project_name}")
        return False, "timeout"
    except Exception as e:
        safe_print(f"  ❌ Error: {project_name} - {str(e)[:50]}")
        return False, "error"

def process_repository(repo_info):
    """Process a single repository (for parallel execution)."""
    return (
        repo_info['name'],
        clone_with_sparse_checkout(
            repo_info['url'],
            repo_info['path'],
            repo_info['name']
        )
    )

def main():
    safe_print("🚀 Smart Cloning of Vulnerable Repositories\n")
    safe_print("=" * 80)
    safe_print("Features:")
    safe_print("  • Only clones repositories with known vulnerabilities")
    safe_print("  • Uses shallow clone (--depth 1) to save space")
    safe_print("  • Excludes large data files (CSV, databases, media)")
    safe_print("  • Keeps all source code, configs, and dependency files")
    safe_print("=" * 80 + "\n")
    
    # Load vulnerable projects
    safe_print("📊 Loading vulnerability data...")
    vulnerable_projects = load_vulnerable_projects()
    safe_print(f"   Found {len(vulnerable_projects)} projects with vulnerabilities\n")
    
    if not vulnerable_projects:
        safe_print("❌ No vulnerable projects found. Run scan_vulnerabilities.py first.")
        sys.exit(1)
    
    # Load project URLs
    projects_file = Path('projects.csv')
    if not projects_file.exists():
        safe_print("❌ projects.csv not found!")
        sys.exit(1)
    
    # Create repos directory
    repos_dir = Path('repos')
    repos_dir.mkdir(exist_ok=True)
    
    # Collect repositories to clone
    repositories = []
    with open(projects_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            project_name = row.get('Project', '').strip()
            repo_url = row.get('Repository URL', '').strip()
            
            if not repo_url or not project_name:
                continue
            
            # Get the sanitized folder name (same as used in _SUMMARY.csv)
            folder_name = get_repo_name_from_url(repo_url)
            
            # Check if this repo (by folder name) is vulnerable
            # The _SUMMARY.csv uses sanitized names which match folder names
            if folder_name not in vulnerable_projects:
                continue
            
            repo_path = repos_dir / folder_name
            
            repositories.append({
                'name': project_name,
                'url': repo_url,
                'path': str(repo_path)
            })
    
    safe_print(f"🎯 Will clone {len(repositories)} vulnerable repositories\n")
    safe_print("=" * 80 + "\n")
    
    # Process repositories in parallel
    success_count = 0
    failed_count = 0
    exists_count = 0
    
    # Use ThreadPoolExecutor for parallel cloning
    max_workers = 5  # Limit concurrent clones to avoid overwhelming the system
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_repo = {
            executor.submit(process_repository, repo): repo 
            for repo in repositories
        }
        
        # Process completed tasks
        for i, future in enumerate(as_completed(future_to_repo), 1):
            repo = future_to_repo[future]
            try:
                name, (success, status) = future.result()
                
                if status == "exists":
                    exists_count += 1
                elif success:
                    success_count += 1
                else:
                    failed_count += 1
                
                # Progress update
                if i % 10 == 0 or i == len(repositories):
                    safe_print(f"\n{'─' * 80}")
                    safe_print(f"📈 Progress: {i}/{len(repositories)} | ✅ {success_count} | ⏭️  {exists_count} | ❌ {failed_count}")
                    safe_print(f"{'─' * 80}\n")
                    
            except Exception as e:
                safe_print(f"❌ Task failed: {str(e)}")
                failed_count += 1
    
    # Final summary
    safe_print("\n" + "=" * 80)
    safe_print("\n📊 FINAL SUMMARY\n")
    safe_print("=" * 80)
    safe_print(f"✅ Successfully cloned:  {success_count}")
    safe_print(f"⏭️  Already existed:     {exists_count}")
    safe_print(f"❌ Failed:              {failed_count}")
    safe_print(f"📦 Total processed:     {len(repositories)}")
    
    # Show space usage
    safe_print("\n💾 Disk Space Usage:")
    size_result = subprocess.run(
        ['du', '-sh', 'repos/'],
        capture_output=True,
        text=True
    )
    if size_result.returncode == 0:
        size = size_result.stdout.split()[0]
        safe_print(f"   Total repos size: {size}")
    
    safe_print("\n" + "=" * 80)
    safe_print("\n✨ Done!\n")
    safe_print("💡 Tips:")
    safe_print("   • Repos are shallow clones (depth 1) to save space")
    safe_print("   • Large data files are excluded via sparse-checkout")
    safe_print("   • To update: cd repos/<name> && git pull")
    safe_print("")

if __name__ == '__main__':
    main()

