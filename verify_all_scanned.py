#!/usr/bin/env python3
"""
Verify which projects from CSV have been scanned and which are missing
"""

import csv
import re
from pathlib import Path

def sanitize_name(name):
    """Sanitize project name to create valid directory name"""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '-', name)
    return name.strip('-').lower()

def main():
    base_dir = Path('/Users/tian/Develop.localized/2023-oss-in-energy-data')
    csv_file = base_dir / 'projects.csv'
    sbom_dir = base_dir / 'sbom'
    repos_dir = base_dir / 'repos'
    
    # Read all projects from CSV
    projects = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            project_name = row.get('Project', '').strip()
            repo_url = row.get('Repository URL', '').strip()
            if project_name:
                projects.append({
                    'name': project_name,
                    'url': repo_url,
                    'safe_name': sanitize_name(project_name)
                })
    
    print(f"📊 Total projects in CSV: {len(projects)}\n")
    
    # Check which have SBOMs
    scanned = []
    not_scanned = []
    no_url = []
    
    for proj in projects:
        sbom_file = sbom_dir / f"{proj['safe_name']}.json"
        
        if not proj['url']:
            no_url.append(proj)
        elif sbom_file.exists():
            # Check if file is not empty
            if sbom_file.stat().st_size > 10:
                scanned.append(proj)
            else:
                not_scanned.append(proj)
        else:
            not_scanned.append(proj)
    
    # Check which repos are cloned
    cloned = []
    for proj in projects:
        repo_path = repos_dir / proj['safe_name']
        if repo_path.exists() and (repo_path / '.git').exists():
            cloned.append(proj)
    
    print("="*70)
    print("📈 Summary:")
    print(f"   ✅ Successfully scanned: {len(scanned)}")
    print(f"   ⏳ Not yet scanned: {len(not_scanned)}")
    print(f"   ⚠️  No repository URL: {len(no_url)}")
    print(f"   📁 Repositories cloned: {len(cloned)}")
    print("="*70)
    
    # Show projects without URLs
    if no_url:
        print(f"\n⚠️  Projects without repository URL ({len(no_url)}):")
        for proj in no_url[:20]:
            print(f"   - {proj['name']}")
        if len(no_url) > 20:
            print(f"   ... and {len(no_url) - 20} more")
    
    # Show some not scanned projects
    if not_scanned:
        print(f"\n⏳ Some projects not yet scanned ({len(not_scanned)} total):")
        for proj in not_scanned[:20]:
            repo_path = repos_dir / proj['safe_name']
            status = "📁 cloned" if repo_path.exists() else "📥 pending"
            print(f"   {status} - {proj['name']}")
        if len(not_scanned) > 20:
            print(f"   ... and {len(not_scanned) - 20} more")
    
    # Calculate completion percentage
    if projects:
        completion = (len(scanned) / len(projects)) * 100
        print(f"\n📊 Completion: {completion:.1f}%")
    
    # Show scan success rate (excluding projects without URLs)
    scannable = len(projects) - len(no_url)
    if scannable > 0:
        success_rate = (len(scanned) / scannable) * 100
        print(f"✅ Success rate (excluding no-URL): {success_rate:.1f}%")
    
    # List all projects that need scanning
    needs_scanning = [p for p in not_scanned if p['url']]
    if needs_scanning:
        output_file = base_dir / 'pending_projects.txt'
        with open(output_file, 'w') as f:
            f.write(f"Projects pending scan: {len(needs_scanning)}\n")
            f.write("="*70 + "\n\n")
            for proj in needs_scanning:
                f.write(f"{proj['name']}\n")
                f.write(f"  URL: {proj['url']}\n")
                f.write(f"  Safe name: {proj['safe_name']}\n\n")
        print(f"\n📝 Full list of pending projects saved to: {output_file}")

if __name__ == '__main__':
    main()


