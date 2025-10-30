"""SBOM Scraper with Dynamic Programming optimization.

Fetches Software Bill of Materials (SBOM) files from GitHub repositories
and parses them to extract exact dependency information. Uses DP to cache
parsed results and avoid redundant computation.
"""

import logging
import sqlite3
import json
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from pathlib import Path
import time

import requests
from github import Github, GithubException
from packaging.requirements import Requirement, InvalidRequirement
from packaging.version import parse as parse_version

from config import DATABASE_PATH
from database import db

logger = logging.getLogger(__name__)


class SBOMScraperDP:
    """SBOM Scraper with Dynamic Programming optimization."""

    # SBOM file patterns to search for (in priority order)
    SBOM_PATTERNS = {
        'python': [
            'requirements.txt',
            'requirements/base.txt',
            'requirements/production.txt',
            'Pipfile.lock',
            'poetry.lock',
            'pyproject.toml',
            'setup.py',
            'setup.cfg',
        ],
        'javascript': [
            'package-lock.json',
            'yarn.lock',
            'pnpm-lock.yaml',
            'package.json',
        ],
        'rust': [
            'Cargo.lock',
            'Cargo.toml',
        ],
        'go': [
            'go.sum',
            'go.mod',
        ],
        'java': [
            'pom.xml',
            'build.gradle',
            'gradle.lockfile',
        ],
        'ruby': [
            'Gemfile.lock',
            'Gemfile',
        ],
    }

    def __init__(self, github_token: Optional[str] = None, cache_hours: int = 24):
        """Initialize SBOM scraper with DP caching.

        Args:
            github_token: GitHub API token for authentication
            cache_hours: Hours to cache SBOM data (default 24)
        """
        self.github_token = github_token
        self.github_client = Github(github_token) if github_token else None
        self.cache_hours = cache_hours

        # Dynamic Programming caches (in-memory for this session)
        self.sbom_cache: Dict[str, Dict[str, Any]] = {}  # repo_url -> parsed SBOM
        self.file_content_cache: Dict[Tuple[str, str], str] = {}  # (repo_url, file_path) -> content
        self.dependency_parse_cache: Dict[str, List[Dict[str, Any]]] = {}  # content_hash -> parsed deps

        self._init_sbom_tables()
        self._load_cache_from_db()

    def _init_sbom_tables(self):
        """Initialize database tables for SBOM caching."""
        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sbom_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    repo_url TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    ecosystem TEXT,
                    content_hash TEXT,
                    raw_content TEXT,
                    parsed_dependencies TEXT,
                    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    UNIQUE(repo_url, file_path)
                );

                CREATE TABLE IF NOT EXISTS sbom_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sbom_file_id INTEGER,
                    project_id INTEGER,
                    package_name TEXT NOT NULL,
                    version_spec TEXT,
                    exact_version TEXT,
                    ecosystem TEXT NOT NULL,
                    dependency_type TEXT DEFAULT 'runtime',
                    is_direct BOOLEAN DEFAULT 1,
                    extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sbom_file_id) REFERENCES sbom_files (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                );

                CREATE INDEX IF NOT EXISTS idx_sbom_files_repo ON sbom_files(repo_url);
                CREATE INDEX IF NOT EXISTS idx_sbom_files_project ON sbom_files(project_id);
                CREATE INDEX IF NOT EXISTS idx_sbom_deps_package ON sbom_dependencies(package_name);
                CREATE INDEX IF NOT EXISTS idx_sbom_deps_project ON sbom_dependencies(project_id);
            """)
            conn.commit()
        logger.info("Initialized SBOM tables")

    def _load_cache_from_db(self):
        """Load cached SBOM data from database (DP: avoid re-fetching)."""
        cache_cutoff = (datetime.now() - timedelta(hours=self.cache_hours)).isoformat()

        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load cached SBOM files
            cursor.execute("""
                SELECT repo_url, file_path, file_type, ecosystem,
                       raw_content, parsed_dependencies, fetched_at
                FROM sbom_files
                WHERE fetched_at > ?
            """, (cache_cutoff,))

            for row in cursor.fetchall():
                repo_url = row['repo_url']
                file_path = row['file_path']

                # Cache file content
                self.file_content_cache[(repo_url, file_path)] = row['raw_content']

                # Cache parsed dependencies
                if row['parsed_dependencies']:
                    try:
                        parsed = json.loads(row['parsed_dependencies'])
                        if repo_url not in self.sbom_cache:
                            self.sbom_cache[repo_url] = {
                                'files': {},
                                'dependencies': [],
                                'ecosystem': row['ecosystem'],
                            }
                        self.sbom_cache[repo_url]['files'][file_path] = parsed
                        self.sbom_cache[repo_url]['dependencies'].extend(parsed)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse cached dependencies for {repo_url}/{file_path}")

        logger.info(f"Loaded {len(self.sbom_cache)} cached SBOMs from database")

    def fetch_sbom_for_project(self, project_data: Dict[str, Any],
                               force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch and parse SBOM files for a project.

        Args:
            project_data: Project dictionary with 'url', 'id', 'language'
            force_refresh: Force re-fetch even if cached

        Returns:
            Dictionary with parsed SBOM data or None if no SBOM found
        """
        repo_url = project_data['url']
        project_id = project_data['id']
        language = (project_data.get('language') or '').lower()

        # DP: Check cache first
        if not force_refresh and repo_url in self.sbom_cache:
            logger.info(f"Using cached SBOM for {repo_url}")
            return self.sbom_cache[repo_url]

        logger.info(f"Fetching SBOM for {repo_url} (language: {language})")

        # Determine which SBOM files to look for based on language
        sbom_patterns = self._get_sbom_patterns(language)

        # Try to fetch SBOM files
        sbom_data = {
            'repo_url': repo_url,
            'project_id': project_id,
            'language': language,
            'files': {},
            'dependencies': [],
            'ecosystem': self._language_to_ecosystem(language),
        }

        for file_pattern in sbom_patterns:
            content = self._fetch_file_from_github(repo_url, file_pattern)
            if content:
                logger.info(f"Found SBOM file: {file_pattern} in {repo_url}")

                # Parse the SBOM file
                parsed_deps = self._parse_sbom_file(content, file_pattern, language)

                if parsed_deps:
                    sbom_data['files'][file_pattern] = parsed_deps
                    sbom_data['dependencies'].extend(parsed_deps)

                    # Save to database
                    self._save_sbom_to_db(project_id, repo_url, file_pattern,
                                         content, parsed_deps, sbom_data['ecosystem'])

        if sbom_data['dependencies']:
            # Cache in memory (DP)
            self.sbom_cache[repo_url] = sbom_data
            logger.info(f"Extracted {len(sbom_data['dependencies'])} dependencies from SBOM for {repo_url}")
            return sbom_data

        logger.warning(f"No SBOM files found for {repo_url}")
        return None

    def _get_sbom_patterns(self, language: str) -> List[str]:
        """Get SBOM file patterns for a language."""
        patterns = []

        # Try language-specific patterns first
        if language in self.SBOM_PATTERNS:
            patterns.extend(self.SBOM_PATTERNS[language])

        # Always include Python patterns as fallback (most common in this dataset)
        if language != 'python':
            patterns.extend(self.SBOM_PATTERNS['python'])

        return patterns

    def _language_to_ecosystem(self, language: str) -> str:
        """Map language to package ecosystem."""
        mapping = {
            'python': 'pypi',
            'javascript': 'npm',
            'typescript': 'npm',
            'rust': 'crates',  # Fixed: OSV uses 'crates' not 'crates.io'
            'go': 'go',
            'java': 'maven',
            'ruby': 'rubygems',
        }
        return mapping.get(language.lower(), 'unknown')

    def _fetch_file_from_github(self, repo_url: str, file_path: str) -> Optional[str]:
        """Fetch file content from GitHub.

        Args:
            repo_url: GitHub repository URL
            file_path: Path to file in repository

        Returns:
            File content as string, or None if not found
        """
        # DP: Check file content cache first
        cache_key = (repo_url, file_path)
        if cache_key in self.file_content_cache:
            return self.file_content_cache[cache_key]

        try:
            # Extract owner and repo from URL
            # URL format: https://github.com/owner/repo
            parts = repo_url.rstrip('/').split('/')
            if len(parts) < 2:
                logger.warning(f"Invalid GitHub URL: {repo_url}")
                return None

            owner = parts[-2]
            repo_name = parts[-1]

            if self.github_client:
                # Use PyGithub (authenticated, higher rate limit)
                try:
                    repo = self.github_client.get_repo(f"{owner}/{repo_name}")
                    content_file = repo.get_contents(file_path)

                    if isinstance(content_file, list):
                        # It's a directory, not a file
                        return None

                    content = content_file.decoded_content.decode('utf-8')

                    # Cache the content (DP)
                    self.file_content_cache[cache_key] = content
                    return content

                except GithubException as e:
                    if e.status == 404:
                        logger.debug(f"File not found: {file_path} in {repo_url}")
                    else:
                        logger.warning(f"GitHub API error fetching {file_path}: {e}")
                    return None
            else:
                # Use raw GitHub URL (unauthenticated, lower rate limit)
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/master/{file_path}"

                # Try master branch first, then main
                for branch in ['master', 'main']:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/{file_path}"
                    response = requests.get(raw_url, timeout=10)

                    if response.status_code == 200:
                        content = response.text
                        # Cache the content (DP)
                        self.file_content_cache[cache_key] = content
                        return content
                    elif response.status_code == 404:
                        continue
                    else:
                        logger.warning(f"HTTP {response.status_code} fetching {raw_url}")
                        return None

                logger.debug(f"File not found: {file_path} in {repo_url}")
                return None

        except Exception as e:
            logger.error(f"Error fetching {file_path} from {repo_url}: {e}")
            return None

    def _parse_sbom_file(self, content: str, file_name: str,
                        language: str) -> List[Dict[str, Any]]:
        """Parse SBOM file content to extract dependencies.

        Args:
            content: File content
            file_name: Name of SBOM file
            language: Programming language

        Returns:
            List of dependency dictionaries
        """
        # DP: Check parse cache (hash content to avoid re-parsing identical files)
        content_hash = str(hash(content))
        if content_hash in self.dependency_parse_cache:
            logger.debug(f"Using cached parse for {file_name}")
            return self.dependency_parse_cache[content_hash]

        dependencies = []

        try:
            if file_name == 'requirements.txt' or file_name.endswith('/requirements.txt') or \
               file_name.endswith('requirements/base.txt') or file_name.endswith('requirements/production.txt'):
                dependencies = self._parse_requirements_txt(content)

            elif file_name == 'Pipfile.lock':
                dependencies = self._parse_pipfile_lock(content)

            elif file_name == 'poetry.lock':
                dependencies = self._parse_poetry_lock(content)

            elif file_name == 'package-lock.json':
                dependencies = self._parse_package_lock_json(content)

            elif file_name == 'yarn.lock':
                dependencies = self._parse_yarn_lock(content)

            elif file_name == 'Cargo.lock':
                dependencies = self._parse_cargo_lock(content)

            elif file_name == 'go.sum':
                dependencies = self._parse_go_sum(content)

            elif file_name == 'Gemfile.lock':
                dependencies = self._parse_gemfile_lock(content)

            else:
                logger.warning(f"No parser implemented for {file_name}")

        except Exception as e:
            logger.error(f"Error parsing {file_name}: {e}")
            return []

        # Cache parsed result (DP)
        if dependencies:
            self.dependency_parse_cache[content_hash] = dependencies

        return dependencies

    def _parse_requirements_txt(self, content: str) -> List[Dict[str, Any]]:
        """Parse requirements.txt file."""
        dependencies = []

        for line in content.split('\n'):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Skip URLs and VCS references (not in PyPI)
            if line.startswith(('http://', 'https://', 'git+', 'hg+', 'svn+', 'bzr+')):
                continue

            # Skip -r/-e flags
            if line.startswith(('-r ', '-e ', '--')):
                continue

            try:
                # Parse using packaging library
                req = Requirement(line)

                dep = {
                    'package_name': req.name.lower(),
                    'version_spec': str(req.specifier) if req.specifier else '',
                    'exact_version': self._extract_exact_version(str(req.specifier)),
                    'ecosystem': 'pypi',
                    'dependency_type': 'runtime',
                    'is_direct': True,
                }
                dependencies.append(dep)

            except InvalidRequirement:
                # Try simple regex as fallback
                match = re.match(r'^([a-zA-Z0-9_-]+)([>=<\!~\s].*)?$', line)
                if match:
                    package_name = match.group(1).lower()
                    version_spec = match.group(2).strip() if match.group(2) else ''

                    dependencies.append({
                        'package_name': package_name,
                        'version_spec': version_spec,
                        'exact_version': self._extract_exact_version(version_spec),
                        'ecosystem': 'pypi',
                        'dependency_type': 'runtime',
                        'is_direct': True,
                    })

        return dependencies

    def _parse_pipfile_lock(self, content: str) -> List[Dict[str, Any]]:
        """Parse Pipfile.lock (JSON format)."""
        dependencies = []

        try:
            data = json.loads(content)

            # Parse default (runtime) dependencies
            for package_name, info in data.get('default', {}).items():
                dependencies.append({
                    'package_name': package_name.lower(),
                    'version_spec': info.get('version', ''),
                    'exact_version': info.get('version', '').lstrip('='),
                    'ecosystem': 'pypi',
                    'dependency_type': 'runtime',
                    'is_direct': True,
                })

            # Parse develop (dev) dependencies
            for package_name, info in data.get('develop', {}).items():
                dependencies.append({
                    'package_name': package_name.lower(),
                    'version_spec': info.get('version', ''),
                    'exact_version': info.get('version', '').lstrip('='),
                    'ecosystem': 'pypi',
                    'dependency_type': 'development',
                    'is_direct': True,
                })

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Pipfile.lock: {e}")

        return dependencies

    def _parse_poetry_lock(self, content: str) -> List[Dict[str, Any]]:
        """Parse poetry.lock (TOML format)."""
        dependencies = []

        try:
            import toml
            data = toml.loads(content)

            for package in data.get('package', []):
                dependencies.append({
                    'package_name': package.get('name', '').lower(),
                    'version_spec': f"=={package.get('version', '')}",
                    'exact_version': package.get('version', ''),
                    'ecosystem': 'pypi',
                    'dependency_type': package.get('category', 'runtime'),
                    'is_direct': True,
                })

        except Exception as e:
            logger.error(f"Failed to parse poetry.lock: {e}")

        return dependencies

    def _parse_package_lock_json(self, content: str) -> List[Dict[str, Any]]:
        """Parse package-lock.json (npm)."""
        dependencies = []

        try:
            data = json.loads(content)

            # npm v1/v2 format
            if 'dependencies' in data:
                for package_name, info in data['dependencies'].items():
                    dependencies.append({
                        'package_name': package_name,
                        'version_spec': f"=={info.get('version', '')}",
                        'exact_version': info.get('version', ''),
                        'ecosystem': 'npm',
                        'dependency_type': 'runtime',
                        'is_direct': not info.get('dev', False),
                    })

            # npm v3+ format (packages)
            if 'packages' in data:
                for package_path, info in data['packages'].items():
                    if package_path == '':  # Root package
                        continue

                    # Extract package name from path (node_modules/package-name)
                    package_name = package_path.split('node_modules/')[-1]

                    dependencies.append({
                        'package_name': package_name,
                        'version_spec': f"=={info.get('version', '')}",
                        'exact_version': info.get('version', ''),
                        'ecosystem': 'npm',
                        'dependency_type': 'runtime',
                        'is_direct': not info.get('dev', False),
                    })

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse package-lock.json: {e}")

        return dependencies

    def _parse_yarn_lock(self, content: str) -> List[Dict[str, Any]]:
        """Parse yarn.lock."""
        dependencies = []

        # Simple regex-based parser for yarn.lock
        pattern = r'^"?([^"@\n]+)@.*"?:\s*\n\s+version\s+"([^"]+)"'

        for match in re.finditer(pattern, content, re.MULTILINE):
            package_name = match.group(1)
            version = match.group(2)

            dependencies.append({
                'package_name': package_name,
                'version_spec': f"=={version}",
                'exact_version': version,
                'ecosystem': 'npm',
                'dependency_type': 'runtime',
                'is_direct': True,
            })

        return dependencies

    def _parse_cargo_lock(self, content: str) -> List[Dict[str, Any]]:
        """Parse Cargo.lock (Rust)."""
        dependencies = []

        try:
            import toml
            data = toml.loads(content)

            packages = data.get('package', [])
            if not isinstance(packages, list):
                logger.error(f"Cargo.lock 'package' field is not a list: {type(packages)}")
                return []

            for package in packages:
                if not isinstance(package, dict):
                    continue

                dependencies.append({
                    'package_name': package.get('name', ''),
                    'version_spec': f"=={package.get('version', '')}",
                    'exact_version': package.get('version', ''),
                    'ecosystem': 'crates',  # Fixed: use 'crates' not 'crates.io'
                    'dependency_type': 'runtime',
                    'is_direct': True,
                })

        except Exception as e:
            logger.error(f"Failed to parse Cargo.lock: {e}")

        return dependencies

    def _parse_go_sum(self, content: str) -> List[Dict[str, Any]]:
        """Parse go.sum (Go modules)."""
        dependencies = []
        seen = set()

        # go.sum format: module version hash
        for line in content.split('\n'):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 2:
                module_name = parts[0]
                version = parts[1]

                # Deduplicate (go.sum has multiple entries per module)
                key = (module_name, version)
                if key not in seen:
                    seen.add(key)
                    dependencies.append({
                        'package_name': module_name,
                        'version_spec': version,
                        'exact_version': version.lstrip('v'),
                        'ecosystem': 'go',
                        'dependency_type': 'runtime',
                        'is_direct': True,
                    })

        return dependencies

    def _parse_gemfile_lock(self, content: str) -> List[Dict[str, Any]]:
        """Parse Gemfile.lock (Ruby)."""
        dependencies = []

        # Simple regex parser for Gemfile.lock
        in_gems_section = False

        for line in content.split('\n'):
            line = line.strip()

            if line == 'GEM' or line.startswith('specs:'):
                in_gems_section = True
                continue

            if in_gems_section and line and not line.startswith(' '):
                # End of GEM section
                in_gems_section = False

            if in_gems_section:
                # Parse gem line: "    gem-name (version)"
                match = re.match(r'\s+([a-zA-Z0-9_-]+)\s+\(([^\)]+)\)', line)
                if match:
                    gem_name = match.group(1)
                    version = match.group(2)

                    dependencies.append({
                        'package_name': gem_name,
                        'version_spec': f"=={version}",
                        'exact_version': version,
                        'ecosystem': 'rubygems',
                        'dependency_type': 'runtime',
                        'is_direct': True,
                    })

        return dependencies

    def _extract_exact_version(self, version_spec: str) -> Optional[str]:
        """Extract exact version from version specifier."""
        if not version_spec:
            return None

        # Match patterns like ==1.2.3, =1.2.3
        match = re.match(r'^==?\s*([0-9][0-9a-zA-Z\.\-\+]*)', version_spec)
        if match:
            return match.group(1)

        return None

    def _save_sbom_to_db(self, project_id: int, repo_url: str, file_path: str,
                        raw_content: str, parsed_deps: List[Dict[str, Any]],
                        ecosystem: str):
        """Save SBOM data to database for caching."""
        content_hash = str(hash(raw_content))

        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            cursor = conn.cursor()

            # Insert/update SBOM file
            cursor.execute("""
                INSERT OR REPLACE INTO sbom_files
                (project_id, repo_url, file_path, file_type, ecosystem,
                 content_hash, raw_content, parsed_dependencies, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, repo_url, file_path, Path(file_path).suffix,
                ecosystem, content_hash, raw_content, json.dumps(parsed_deps),
                datetime.now().isoformat()
            ))

            sbom_file_id = cursor.lastrowid

            # Insert dependencies
            for dep in parsed_deps:
                cursor.execute("""
                    INSERT INTO sbom_dependencies
                    (sbom_file_id, project_id, package_name, version_spec,
                     exact_version, ecosystem, dependency_type, is_direct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sbom_file_id, project_id, dep['package_name'], dep['version_spec'],
                    dep['exact_version'], dep['ecosystem'], dep['dependency_type'],
                    dep['is_direct']
                ))

            conn.commit()

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects from database."""
        with sqlite3.connect(str(DATABASE_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY stars DESC")
            return [dict(row) for row in cursor.fetchall()]

    def scrape_all_sboms(self, limit: Optional[int] = None,
                        force_refresh: bool = False) -> Dict[str, Any]:
        """Scrape SBOMs for all projects.

        Args:
            limit: Maximum number of projects to process
            force_refresh: Force re-fetch even if cached

        Returns:
            Summary statistics
        """
        projects = self.get_all_projects()

        if limit:
            projects = projects[:limit]

        stats = {
            'total_projects': len(projects),
            'projects_with_sbom': 0,
            'projects_without_sbom': 0,
            'total_dependencies': 0,
            'unique_packages': set(),
            'by_ecosystem': {},
        }

        logger.info(f"Starting SBOM scrape for {len(projects)} projects")

        for i, project in enumerate(projects, 1):
            logger.info(f"[{i}/{len(projects)}] Processing {project['name']}")

            sbom_data = self.fetch_sbom_for_project(project, force_refresh)

            if sbom_data:
                stats['projects_with_sbom'] += 1
                stats['total_dependencies'] += len(sbom_data['dependencies'])

                for dep in sbom_data['dependencies']:
                    stats['unique_packages'].add((dep['package_name'], dep['ecosystem']))

                    ecosystem = dep['ecosystem']
                    if ecosystem not in stats['by_ecosystem']:
                        stats['by_ecosystem'][ecosystem] = 0
                    stats['by_ecosystem'][ecosystem] += 1
            else:
                stats['projects_without_sbom'] += 1

            # Rate limiting (if using unauthenticated requests)
            if not self.github_token and i % 10 == 0:
                logger.info("Rate limiting: sleeping 5 seconds")
                time.sleep(5)

        stats['unique_packages'] = len(stats['unique_packages'])

        logger.info(f"SBOM scrape complete: {stats}")
        return stats


# Singleton instance
sbom_scraper: Optional[SBOMScraperDP] = None


def get_sbom_scraper(github_token: Optional[str] = None) -> SBOMScraperDP:
    """Get or create singleton SBOM scraper instance."""
    global sbom_scraper

    if sbom_scraper is None:
        sbom_scraper = SBOMScraperDP(github_token)

    return sbom_scraper
