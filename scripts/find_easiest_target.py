import sqlite3
from datetime import datetime

conn = sqlite3.connect('dependency_analyzer/data/dependencies.db')
c = conn.cursor()

print('=' * 80)
print('EASIEST TO COMPROMISE - REPOSITORY ANALYSIS')
print('=' * 80)
print()

# Query repositories with exploitability scoring
c.execute('''
    SELECT
        p.name,
        p.url,
        p.stars,
        COUNT(DISTINCT d.dependency_name) as dep_count,
        COUNT(DISTINCT pc.cve_id) as total_cves,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%CRITICAL%' THEN pc.cve_id END) as critical_cves,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%HIGH%' THEN pc.cve_id END) as high_cves,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%AC:L%' THEN pc.cve_id END) as low_complexity,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%PR:N%' THEN pc.cve_id END) as no_privs_required,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%UI:N%' THEN pc.cve_id END) as no_user_interaction
    FROM projects p
    LEFT JOIN dependencies d ON p.id = d.project_id
    LEFT JOIN package_cves pc ON d.dependency_name = pc.package_name
    WHERE d.dependency_name IS NOT NULL
    GROUP BY p.id
    HAVING total_cves > 0
''')

repositories = c.fetchall()

# Calculate exploitability scores
scored_repos = []
for repo in repositories:
    name, url, stars, deps, total_cves, critical, high, low_complexity, no_privs, no_ui = repo

    # Exploitability score calculation
    # Higher score = easier to exploit
    score = 0

    # No privileges required (most important)
    if total_cves > 0:
        no_privs_ratio = (no_privs / total_cves) * 100
        score += no_privs_ratio * 3  # Weight: 3x

    # No user interaction required
    if total_cves > 0:
        no_ui_ratio = (no_ui / total_cves) * 100
        score += no_ui_ratio * 2.5  # Weight: 2.5x

    # Low attack complexity
    if total_cves > 0:
        low_complexity_ratio = (low_complexity / total_cves) * 100
        score += low_complexity_ratio * 2  # Weight: 2x

    # Critical CVEs present
    if total_cves > 0:
        critical_ratio = (critical / total_cves) * 100
        score += critical_ratio * 1.5  # Weight: 1.5x

    # High CVE count (more attack surface)
    if total_cves > 100:
        score += 50
    elif total_cves > 50:
        score += 30
    elif total_cves > 20:
        score += 15

    scored_repos.append({
        'name': name,
        'url': url,
        'stars': stars,
        'deps': deps,
        'total_cves': total_cves,
        'critical': critical,
        'high': high,
        'low_complexity': low_complexity,
        'no_privs': no_privs,
        'no_ui': no_ui,
        'exploitability_score': round(score, 1)
    })

# Sort by exploitability score (highest = easiest to exploit)
scored_repos.sort(key=lambda x: x['exploitability_score'], reverse=True)

print('TOP 10 EASIEST TO COMPROMISE REPOSITORIES')
print('(Ranked by exploitability score - higher = easier to exploit)')
print('-' * 80)
print()

for i, repo in enumerate(scored_repos[:10], 1):
    print(f"{i}. {repo['name']}")
    print(f"   URL: {repo['url']}")
    print(f"   Stars: {repo['stars']}")
    print(f"   Exploitability Score: {repo['exploitability_score']}/1000")
    print(f"   Total CVEs: {repo['total_cves']}")
    print(f"   Critical CVEs: {repo['critical']}")
    print(f"   High CVEs: {repo['high']}")
    print()
    print(f"   Easy Exploit Indicators:")
    print(f"     - No privileges required: {repo['no_privs']} CVEs ({repo['no_privs']/repo['total_cves']*100:.1f}%)")
    print(f"     - No user interaction: {repo['no_ui']} CVEs ({repo['no_ui']/repo['total_cves']*100:.1f}%)")
    print(f"     - Low attack complexity: {repo['low_complexity']} CVEs ({repo['low_complexity']/repo['total_cves']*100:.1f}%)")
    print()
    print('-' * 80)

# Detailed analysis of #1 easiest target
print()
print('=' * 80)
print('DETAILED ANALYSIS: EASIEST TARGET')
print('=' * 80)
print()

easiest = scored_repos[0]
print(f"Repository: {easiest['name']}")
print(f"URL: {easiest['url']}")
print(f"Exploitability Score: {easiest['exploitability_score']}/1000")
print()

# Get specific vulnerable packages for easiest target
c.execute('''
    SELECT
        d.dependency_name,
        d.version_spec,
        COUNT(DISTINCT pc.cve_id) as cve_count,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%PR:N%' THEN pc.cve_id END) as no_auth_cves,
        COUNT(DISTINCT CASE WHEN pc.severity LIKE '%CRITICAL%' THEN pc.cve_id END) as critical_cves
    FROM projects p
    JOIN dependencies d ON p.id = d.project_id
    JOIN package_cves pc ON d.dependency_name = pc.package_name
    WHERE p.name = ?
    GROUP BY d.dependency_name, d.version_spec
    ORDER BY no_auth_cves DESC, cve_count DESC
    LIMIT 5
''', (easiest['name'],))

print('TOP 5 MOST EXPLOITABLE PACKAGES:')
print('-' * 80)
for pkg_name, version, cve_count, no_auth, critical in c.fetchall():
    print(f'{pkg_name} {version}')
    print(f'  - Total CVEs: {cve_count}')
    print(f'  - No Authentication Required: {no_auth} CVEs')
    print(f'  - Critical Severity: {critical} CVEs')
    print()

# Get specific no-auth CVEs
c.execute('''
    SELECT DISTINCT
        pc.cve_id,
        pc.severity,
        d.dependency_name
    FROM projects p
    JOIN dependencies d ON p.id = d.project_id
    JOIN package_cves pc ON d.dependency_name = pc.package_name
    WHERE p.name = ?
      AND pc.severity LIKE '%PR:N%'
      AND (pc.severity LIKE '%CRITICAL%' OR pc.severity LIKE '%HIGH%')
    ORDER BY pc.cve_id DESC
    LIMIT 10
''', (easiest['name'],))

no_auth_cves = c.fetchall()

print('SAMPLE NO-AUTHENTICATION EXPLOITS:')
print('-' * 80)
for cve_id, severity, pkg in no_auth_cves[:5]:
    print(f'{cve_id} ({pkg})')
    # Parse severity for key metrics
    if 'CRITICAL' in severity:
        sev_level = 'CRITICAL'
    elif 'HIGH' in severity:
        sev_level = 'HIGH'
    else:
        sev_level = 'MEDIUM'

    print(f'  Severity: {sev_level}')
    print(f'  Authentication: NONE REQUIRED')
    if 'UI:N' in severity:
        print(f'  User Interaction: NONE REQUIRED')
    if 'AC:L' in severity:
        print(f'  Attack Complexity: LOW')
    print()

print('=' * 80)
print('EXPLOITATION DIFFICULTY RATING')
print('=' * 80)
print()

difficulty_score = 100 - (easiest['exploitability_score'] / 10)
if difficulty_score < 20:
    rating = 'TRIVIAL'
    desc = 'Script kiddie level - automated tools available'
elif difficulty_score < 40:
    rating = 'EASY'
    desc = 'Basic security knowledge required'
elif difficulty_score < 60:
    rating = 'MODERATE'
    desc = 'Intermediate attacker skills needed'
elif difficulty_score < 80:
    rating = 'DIFFICULT'
    desc = 'Advanced exploitation techniques required'
else:
    rating = 'VERY DIFFICULT'
    desc = 'Expert-level attacker required'

print(f'Difficulty Rating: {rating}')
print(f'Description: {desc}')
print(f'Estimated Time to Compromise: {round(difficulty_score / 10, 1)} hours')
print()

print('ATTACK SURFACE SUMMARY:')
print(f"  - Total vulnerable dependencies: {easiest['deps']}")
print(f"  - CVEs requiring no authentication: {easiest['no_privs']}")
print(f"  - CVEs requiring no user interaction: {easiest['no_ui']}")
print(f"  - Low complexity attacks available: {easiest['low_complexity']}")
print()

print('=' * 80)

conn.close()
