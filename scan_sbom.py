#!/usr/bin/env python3
"""
Script to scan all projects from projects.csv using Syft and generate SBOMs
"""

import csv
import subprocess
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

def sanitize_filename(name):
    """Sanitize project name to create valid filename"""
    # Remove or replace invalid characters
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()

def get_repo_identifier(repo_url):
    """Extract org/repo from GitHub URL"""
    if not repo_url or repo_url == '':
        return None
    
    # Parse URL
    parsed = urlparse(repo_url)
    path = parsed.path.strip('/')
    
    # Remove .git suffix if present
    if path.endswith('.git'):
        path = path[:-4]
    
    return path

def scan_repository(project_name, repo_url, output_dir, temp_dir):
    """Scan a repository using Syft"""
    if not repo_url or repo_url.strip() == '':
        print(f"⚠️  Skipping {project_name}: No repository URL")
        return None
    
    # Create safe filename
    safe_name = sanitize_filename(project_name)
    repo_id = get_repo_identifier(repo_url)
    
    if not repo_id:
        print(f"⚠️  Skipping {project_name}: Invalid repository URL: {repo_url}")
        return None
    
    output_file = output_dir / f"{safe_name}.json"
    
    # Check if already scanned
    if output_file.exists():
        print(f"⏭️  Skipping {project_name}: Already scanned")
        return True
    
    print(f"🔍 Scanning {project_name} ({repo_url})...")
    
    # Create a temporary directory for this repo
    repo_temp_dir = temp_dir / safe_name
    
    try:
        # Clone the repository (shallow clone to save time and space)
        print(f"  📥 Cloning repository...")
        clone_result = subprocess.run(
            ['git', 'clone', '--depth', '1', repo_url, str(repo_temp_dir)],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes for cloning
        )
        
        if clone_result.returncode != 0:
            print(f"❌ Failed to clone {project_name}: {clone_result.stderr[:150]}")
            return False
        
        # Scan the cloned repository
        print(f"  🔎 Analyzing with Syft...")
        result = subprocess.run(
            ['syft', f'dir:{repo_temp_dir}', '-o', f'json={output_file}'],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes for scanning
        )
        
        if result.returncode == 0:
            print(f"✅ Successfully scanned {project_name}")
            return True
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            print(f"❌ Failed to scan {project_name}: {error_msg}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout scanning {project_name}")
        return False
    except Exception as e:
        print(f"❌ Error scanning {project_name}: {str(e)}")
        return False
    finally:
        # Clean up the cloned repository
        if repo_temp_dir.exists():
            try:
                shutil.rmtree(repo_temp_dir)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not clean up temp dir: {e}")

def main():
    # Setup paths
    base_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data')
    csv_file = base_dir / 'projects.csv'
    output_dir = base_dir / 'sbom'
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Create temporary directory for cloning repos
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        print(f"📂 Using temporary directory: {temp_dir}\n")
        
        # Read CSV and scan projects
        successful = 0
        failed = 0
        skipped = 0
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            # CSV uses semicolon as delimiter
            reader = csv.DictReader(f, delimiter=';')
            
            projects = list(reader)
            total = len(projects)
            
            print(f"📊 Found {total} projects to scan\n")
            
            for idx, row in enumerate(projects, 1):
                project_name = row.get('Project', '').strip()
                repo_url = row.get('Repository URL', '').strip()
                
                if not project_name:
                    continue
                    
                print(f"\n[{idx}/{total}] ", end='')
                
                result = scan_repository(project_name, repo_url, output_dir, temp_dir)
                
                if result is True:
                    successful += 1
                elif result is False:
                    failed += 1
                else:  # result is None
                    skipped += 1
        
        # Summary
        print("\n" + "="*60)
        print("📈 Scan Summary:")
        print(f"   Total projects: {total}")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️  Skipped: {skipped}")
        print(f"\n📁 SBOMs saved to: {output_dir}")
        print("="*60)

if __name__ == '__main__':
    main()

