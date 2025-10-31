#!/usr/bin/env python3
"""
Analyze vulnerability data and generate comprehensive statistics for visualization.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict, Counter

def load_csv_files(csv_dir):
    """Load all vulnerability CSV files."""
    vulnerabilities = []
    csv_dir = Path(csv_dir)
    
    for csv_file in csv_dir.glob('*.csv'):
        if csv_file.name == '_SUMMARY.csv':
            continue
            
        project_name = csv_file.stem
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['project'] = project_name
                    vulnerabilities.append(row)
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
    
    return vulnerabilities

def load_summary(csv_dir):
    """Load the summary CSV."""
    summary_file = Path(csv_dir) / '_SUMMARY.csv'
    projects = []
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            projects.append(row)
    
    return projects

def load_projects_metadata(csv_file):
    """Load project metadata from projects.csv."""
    projects_meta = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if 'Repository URL' in row and row['Repository URL']:
                # Extract project name from URL
                url = row['Repository URL'].strip()
                if url:
                    project_name = url.rstrip('/').split('/')[-1].lower()
                    projects_meta[project_name] = {
                        'name': row.get('Project', ''),
                        'category': row.get('Category', 'Unknown'),
                        'languages': row.get('Languages', ''),
                        'license': row.get('License', ''),
                        'description': row.get('Description', ''),
                        'repo_url': url,
                    }
    
    return projects_meta

def analyze_vulnerabilities(vulnerabilities, projects, projects_meta):
    """Generate comprehensive analysis."""
    
    # Package vulnerability counts
    package_vulns = defaultdict(lambda: {'count': 0, 'projects': set(), 'severities': []})
    
    # Project categories
    category_vulns = defaultdict(int)
    category_projects = defaultdict(set)
    
    # Severity distribution
    severity_counts = Counter()
    
    # Language analysis
    language_vulns = defaultdict(int)
    
    # Package type distribution
    package_types = Counter()
    
    # Vulnerability IDs
    vuln_ids = Counter()
    
    # Project vulnerability details
    project_details = {}
    
    for vuln in vulnerabilities:
        package = vuln.get('Package', '').strip('"')
        version = vuln.get('Version', '').strip('"')
        vuln_id = vuln.get('Vulnerability ID', '').strip('"')
        severity = vuln.get('Severity', '').strip('"')
        pkg_type = vuln.get('Type', '').strip('"')
        project = vuln.get('project', '')
        
        # Package analysis
        pkg_key = f"{package}@{version}"
        package_vulns[pkg_key]['count'] += 1
        package_vulns[pkg_key]['projects'].add(project)
        package_vulns[pkg_key]['severities'].append(severity)
        package_vulns[pkg_key]['type'] = pkg_type
        package_vulns[pkg_key]['package'] = package
        package_vulns[pkg_key]['version'] = version
        
        # Severity
        severity_counts[severity] += 1
        
        # Package type
        package_types[pkg_type] += 1
        
        # Vulnerability ID
        vuln_ids[vuln_id] += 1
        
        # Project details
        if project not in project_details:
            project_details[project] = {
                'vulnerabilities': [],
                'severity_counts': Counter(),
                'package_types': Counter(),
                'packages': set()
            }
        
        project_details[project]['vulnerabilities'].append(vuln)
        project_details[project]['severity_counts'][severity] += 1
        project_details[project]['package_types'][pkg_type] += 1
        project_details[project]['packages'].add(package)
        
        # Category analysis
        meta = projects_meta.get(project, {})
        category = meta.get('category', 'Unknown')
        category_vulns[category] += 1
        category_projects[category].add(project)
        
        # Language analysis
        languages = meta.get('languages', '').split(',')
        for lang in languages:
            lang = lang.strip()
            if lang:
                language_vulns[lang] += 1
    
    # Prepare data for visualization
    
    # 1. Top vulnerable packages (with project count)
    top_packages = []
    for pkg_key, data in sorted(package_vulns.items(), key=lambda x: x[1]['count'], reverse=True)[:50]:
        top_packages.append({
            'package': data['package'],
            'version': data['version'],
            'vulnerabilities': data['count'],
            'projects_affected': len(data['projects']),
            'type': data['type'],
            'severity_distribution': dict(Counter(data['severities']))
        })
    
    # 2. Project vulnerability distribution
    project_vuln_dist = []
    for proj in projects:
        name = proj['Project']
        vuln_count = int(proj['Vulnerability Count'])
        status = proj['Status']
        
        meta = projects_meta.get(name, {})
        
        project_vuln_dist.append({
            'project': name,
            'vulnerabilities': vuln_count,
            'status': status,
            'category': meta.get('category', 'Unknown'),
            'languages': meta.get('languages', ''),
            'repo_url': meta.get('repo_url', ''),
            'details': {
                'severity_counts': dict(project_details.get(name, {}).get('severity_counts', {})),
                'package_types': dict(project_details.get(name, {}).get('package_types', {})),
                'unique_packages': len(project_details.get(name, {}).get('packages', set()))
            }
        })
    
    # 3. Category analysis
    category_analysis = []
    for category, vuln_count in category_vulns.items():
        category_analysis.append({
            'category': category,
            'vulnerabilities': vuln_count,
            'projects': len(category_projects[category]),
            'avg_vulns_per_project': vuln_count / len(category_projects[category]) if category_projects[category] else 0
        })
    
    # 4. Severity distribution
    severity_data = [
        {'severity': sev, 'count': count}
        for sev, count in severity_counts.most_common()
    ]
    
    # 5. Language analysis
    language_data = [
        {'language': lang, 'vulnerabilities': count}
        for lang, count in sorted(language_vulns.items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    
    # 6. Package type distribution
    package_type_data = [
        {'type': pkg_type, 'count': count}
        for pkg_type, count in package_types.most_common()
    ]
    
    # 7. Most common vulnerabilities
    top_vulns = [
        {'vuln_id': vuln_id, 'occurrences': count}
        for vuln_id, count in vuln_ids.most_common(30)
    ]
    
    # 8. Security health score by category
    category_health = []
    for cat in category_analysis:
        total_projects = len([p for p in projects if projects_meta.get(p['Project'], {}).get('category') == cat['category']])
        vulnerable_projects = cat['projects']
        clean_projects = total_projects - vulnerable_projects
        
        health_score = (clean_projects / total_projects * 100) if total_projects > 0 else 100
        
        category_health.append({
            'category': cat['category'],
            'health_score': round(health_score, 1),
            'total_projects': total_projects,
            'vulnerable': vulnerable_projects,
            'clean': clean_projects,
            'total_vulns': cat['vulnerabilities']
        })
    
    # 9. Dependency risk network (top packages and their impact)
    dependency_network = []
    for pkg in top_packages[:30]:
        dependency_network.append({
            'id': f"{pkg['package']}@{pkg['version']}",
            'package': pkg['package'],
            'version': pkg['version'],
            'vulnerabilities': pkg['vulnerabilities'],
            'projects_affected': pkg['projects_affected'],
            'risk_score': pkg['vulnerabilities'] * pkg['projects_affected'],
            'type': pkg['type']
        })
    
    return {
        'overview': {
            'total_projects': len(projects),
            'vulnerable_projects': len([p for p in projects if p['Status'] == 'vulnerable']),
            'clean_projects': len([p for p in projects if p['Status'] == 'clean']),
            'total_vulnerabilities': len(vulnerabilities),
            'unique_packages': len(package_vulns),
            'unique_vulns': len(vuln_ids)
        },
        'top_packages': top_packages,
        'project_distribution': sorted(project_vuln_dist, key=lambda x: x['vulnerabilities'], reverse=True),
        'category_analysis': sorted(category_analysis, key=lambda x: x['vulnerabilities'], reverse=True),
        'severity_distribution': severity_data,
        'language_analysis': language_data,
        'package_types': package_type_data,
        'top_vulnerabilities': top_vulns,
        'category_health': sorted(category_health, key=lambda x: x['health_score']),
        'dependency_network': sorted(dependency_network, key=lambda x: x['risk_score'], reverse=True)
    }

def main():
    csv_dir = '/Users/tian/Develop.localized/2023-oss-in-energy-data/csv-vulnerability'
    projects_csv = '/Users/tian/Develop.localized/2023-oss-in-energy-data/projects.csv'
    output_file = '/Users/tian/Develop.localized/2023-oss-in-energy-data/energy-security-viz/public/vulnerability-data.json'
    
    print("📊 Loading vulnerability data...")
    vulnerabilities = load_csv_files(csv_dir)
    print(f"   Loaded {len(vulnerabilities)} vulnerability records")
    
    print("📋 Loading project summary...")
    projects = load_summary(csv_dir)
    print(f"   Loaded {len(projects)} projects")
    
    print("📁 Loading project metadata...")
    projects_meta = load_projects_metadata(projects_csv)
    print(f"   Loaded metadata for {len(projects_meta)} projects")
    
    print("🔍 Analyzing vulnerabilities...")
    analysis = analyze_vulnerabilities(vulnerabilities, projects, projects_meta)
    
    print(f"\n✅ Analysis complete!")
    print(f"   Total vulnerabilities: {analysis['overview']['total_vulnerabilities']}")
    print(f"   Unique packages: {analysis['overview']['unique_packages']}")
    print(f"   Vulnerable projects: {analysis['overview']['vulnerable_projects']}")
    
    print(f"\n💾 Saving to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print("✨ Done!\n")

if __name__ == '__main__':
    main()


