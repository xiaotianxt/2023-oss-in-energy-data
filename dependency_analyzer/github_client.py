"""GitHub API client for repository access and dependency file extraction."""

import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urlparse
import base64

from github import Github, Repository, GithubException
import requests

from config import GITHUB_TOKEN, RATE_LIMIT_DELAY, DEPENDENCY_FILES

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API to extract repository information."""
    
    def __init__(self, token: str = GITHUB_TOKEN):
        if not token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")
        
        self.github = Github(token)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        })
    
    def parse_github_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Parse GitHub URL to extract owner and repo name."""
        try:
            parsed = urlparse(url)
            if 'github.com' not in parsed.netloc:
                return None
            
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                # Remove .git suffix if present
                if repo.endswith('.git'):
                    repo = repo[:-4]
                return owner, repo
        except Exception as e:
            logger.error(f"Error parsing GitHub URL {url}: {e}")
        
        return None
    
    def get_repository_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get basic repository information."""
        parsed = self.parse_github_url(url)
        if not parsed:
            logger.warning(f"Invalid GitHub URL: {url}")
            return None
        
        owner, repo_name = parsed
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Detect primary language
            languages = repo.get_languages()
            primary_language = max(languages.keys(), key=languages.get) if languages else 'unknown'
            
            return {
                'name': repo.name,
                'url': url,
                'full_name': repo.full_name,
                'description': repo.description,
                'language': primary_language.lower(),
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'last_updated': repo.updated_at.isoformat() if repo.updated_at else None,
                'default_branch': repo.default_branch,
                'archived': repo.archived,
                'languages': languages
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return None
    
    def find_dependency_files(self, url: str) -> List[Dict[str, Any]]:
        """Find all dependency files in a repository."""
        parsed = self.parse_github_url(url)
        if not parsed:
            return []
        
        owner, repo_name = parsed
        dependency_files = []
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Get repository language to determine which files to look for
            languages = repo.get_languages()
            primary_language = max(languages.keys(), key=languages.get).lower() if languages else 'unknown'
            
            # Determine which dependency files to search for
            files_to_search = []
            if primary_language in DEPENDENCY_FILES:
                files_to_search.extend(DEPENDENCY_FILES[primary_language])
            
            # Also search for common files regardless of language
            common_files = ['requirements.txt', 'package.json', 'pom.xml', 'Cargo.toml', 'go.mod']
            files_to_search.extend(common_files)
            
            # Remove duplicates
            files_to_search = list(set(files_to_search))
            
            for file_name in files_to_search:
                try:
                    # Try to get file from root directory
                    file_content = self._get_file_content(repo, file_name)
                    if file_content:
                        dependency_files.append({
                            'path': file_name,
                            'type': self._get_file_type(file_name),
                            'content': file_content,
                            'ecosystem': self._get_ecosystem(file_name)
                        })
                    
                    # Also check common subdirectories
                    for subdir in ['src', 'app', 'backend', 'frontend']:
                        subpath = f"{subdir}/{file_name}"
                        file_content = self._get_file_content(repo, subpath)
                        if file_content:
                            dependency_files.append({
                                'path': subpath,
                                'type': self._get_file_type(file_name),
                                'content': file_content,
                                'ecosystem': self._get_ecosystem(file_name)
                            })
                
                except Exception as e:
                    logger.debug(f"File {file_name} not found in {repo.full_name}: {e}")
                    continue
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
        except GithubException as e:
            logger.error(f"GitHub API error finding files in {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding files in {url}: {e}")
        
        return dependency_files
    
    def _get_file_content(self, repo: Repository, file_path: str) -> Optional[str]:
        """Get content of a specific file."""
        try:
            file_content = repo.get_contents(file_path)
            if file_content.encoding == 'base64':
                return base64.b64decode(file_content.content).decode('utf-8')
            else:
                return file_content.decoded_content.decode('utf-8')
        except GithubException:
            return None
        except Exception as e:
            logger.debug(f"Error reading file {file_path}: {e}")
            return None
    
    def _get_file_type(self, file_name: str) -> str:
        """Determine file type based on filename."""
        file_type_mapping = {
            'requirements.txt': 'pip_requirements',
            'requirements-dev.txt': 'pip_requirements_dev',
            'requirements-test.txt': 'pip_requirements_test',
            'setup.py': 'python_setup',
            'pyproject.toml': 'python_pyproject',
            'Pipfile': 'pipenv',
            'conda.yml': 'conda',
            'environment.yml': 'conda',
            'package.json': 'npm',
            'package-lock.json': 'npm_lock',
            'yarn.lock': 'yarn_lock',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'DESCRIPTION': 'r_description',
            'renv.lock': 'r_renv',
            'Cargo.toml': 'cargo',
            'Cargo.lock': 'cargo_lock',
            'go.mod': 'go_mod',
            'go.sum': 'go_sum',
            'composer.json': 'composer',
            'composer.lock': 'composer_lock'
        }
        return file_type_mapping.get(file_name, 'unknown')
    
    def _get_ecosystem(self, file_name: str) -> str:
        """Determine package ecosystem based on filename."""
        ecosystem_mapping = {
            'requirements.txt': 'pypi',
            'requirements-dev.txt': 'pypi',
            'requirements-test.txt': 'pypi',
            'setup.py': 'pypi',
            'pyproject.toml': 'pypi',
            'Pipfile': 'pypi',
            'conda.yml': 'conda',
            'environment.yml': 'conda',
            'package.json': 'npm',
            'package-lock.json': 'npm',
            'yarn.lock': 'npm',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'DESCRIPTION': 'cran',
            'renv.lock': 'cran',
            'Cargo.toml': 'crates',
            'Cargo.lock': 'crates',
            'go.mod': 'go',
            'go.sum': 'go',
            'composer.json': 'packagist',
            'composer.lock': 'packagist'
        }
        return ecosystem_mapping.get(file_name, 'unknown')
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status."""
        rate_limit = self.github.get_rate_limit()
        return {
            'core': {
                'remaining': rate_limit.core.remaining,
                'limit': rate_limit.core.limit,
                'reset': rate_limit.core.reset.timestamp()
            },
            'search': {
                'remaining': rate_limit.search.remaining,
                'limit': rate_limit.search.limit,
                'reset': rate_limit.search.reset.timestamp()
            }
        }
