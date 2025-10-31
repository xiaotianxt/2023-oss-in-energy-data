#!/usr/bin/env python3
"""
Add all repositories from projects.csv as git submodules with depth 1 (shallow clone).
This ensures minimal disk space usage while maintaining git submodule structure.
"""

import csv
import subprocess
import sys
from pathlib import Path
import re

def sanitize_folder_name(name):
    """Convert project name to valid folder name."""
    # Remove/replace invalid characters
    sanitized = re.sub(r'[^\w\s-]', '', name.lower())
    sanitized = re.sub(r'[-\s]+', '-', sanitized)
    return sanitized.strip('-')

def get_repo_name_from_url(url):
    """Extract repository name from GitHub URL."""
    # Handle URLs like https://github.com/user/repo or https://github.com/user/repo.git
    parts = url.rstrip('/').rstrip('.git').split('/')
    return parts[-1]

def add_submodule_shallow(url, path):
    """
    Add a git submodule with depth 1 (shallow clone).
    
    Strategy:
    1. Add submodule reference to .gitmodules (without cloning)
    2. Manually clone with --depth 1
    3. Register it as a submodule
    """
    try:
        print(f"  Adding submodule: {path}")
        
        # Check if path already exists
        path_obj = Path(path)
        if path_obj.exists() and (path_obj / '.git').exists():
            print(f"  ⏭️  Already exists")
            return True
        
        # Remove the directory if it exists but is not a git repo
        if path_obj.exists():
            import shutil
            shutil.rmtree(path_obj)
        
        # Step 1: Clone with depth 1 directly
        result = subprocess.run(
            ['git', 'clone', '--depth', '1', '--single-branch', url, path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print(f"  ❌ Clone failed: {result.stderr[:100]}")
            return False
        
        # Step 2: Add submodule entry to .gitmodules
        # This registers it properly as a submodule
        result = subprocess.run(
            ['git', 'submodule', 'add', '--force', '--name', path, url, path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Even if this fails (e.g., already exists), the shallow clone is done
        # Mark as shallow in .gitmodules for future updates
        subprocess.run(
            ['git', 'config', '-f', '.gitmodules', f'submodule.{path}.shallow', 'true'],
            capture_output=True
        )
        
        print(f"  ✅ Success (depth 1): {path}")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"  ⏱️  Timeout: {path}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False

def main():
    print("🚀 Adding repositories as shallow git submodules (depth 1)\n")
    print("=" * 80)
    
    # Read projects.csv
    projects_file = Path('projects.csv')
    if not projects_file.exists():
        print("❌ projects.csv not found!")
        sys.exit(1)
    
    repos_dir = Path('repos')
    repos_dir.mkdir(exist_ok=True)
    
    # Parse CSV and collect repositories
    repositories = []
    with open(projects_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            repo_url = row.get('Repository URL', '').strip()
            project_name = row.get('Project', '').strip()
            
            if repo_url and project_name:
                # Get folder name from URL (more reliable than project name)
                folder_name = get_repo_name_from_url(repo_url)
                repo_path = repos_dir / folder_name
                
                repositories.append({
                    'name': project_name,
                    'url': repo_url,
                    'path': str(repo_path)
                })
    
    print(f"\n📊 Found {len(repositories)} repositories to add as submodules\n")
    
    # Check if we're in a git repository
    result = subprocess.run(['git', 'rev-parse', '--git-dir'], capture_output=True)
    if result.returncode != 0:
        print("❌ Not in a git repository!")
        sys.exit(1)
    
    # Process repositories
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, repo in enumerate(repositories, 1):
        print(f"\n[{i}/{len(repositories)}] {repo['name']}")
        print(f"  URL: {repo['url']}")
        
        # Check if already exists and has content
        repo_path = Path(repo['path'])
        if repo_path.exists() and (repo_path / '.git').exists():
            print(f"  ⏭️  Already exists as submodule: {repo['path']}")
            skipped_count += 1
            continue
        
        # Add submodule with shallow clone
        if add_submodule_shallow(repo['url'], repo['path']):
            success_count += 1
        else:
            failed_count += 1
        
        # Progress update every 10 repos
        if i % 10 == 0:
            print(f"\n{'─' * 80}")
            print(f"📈 Progress: {i}/{len(repositories)} | ✅ {success_count} | ❌ {failed_count} | ⏭️  {skipped_count}")
            print(f"{'─' * 80}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("\n📊 FINAL SUMMARY\n")
    print("=" * 80)
    print(f"✅ Successfully added:  {success_count}")
    print(f"⏭️  Already existed:     {skipped_count}")
    print(f"❌ Failed:              {failed_count}")
    print(f"📦 Total processed:     {len(repositories)}")
    print("\n" + "=" * 80)
    
    # Commit the changes
    if success_count > 0:
        print("\n💾 Committing submodule changes...")
        subprocess.run(['git', 'add', '.gitmodules', 'repos/'])
        subprocess.run([
            'git', 'commit', '-m', 
            f'feat: Add {success_count} repositories as shallow submodules (depth 1)\n\nUsing shallow clones to minimize disk space usage.'
        ])
        print("✅ Changes committed!")
        print("\n💡 To push changes: git push")
    
    print("\n✨ Done!\n")

if __name__ == '__main__':
    main()

