"""Optimized dependency resolver with full dynamic programming (memoization)."""

import logging
import requests
import sqlite3
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import json
from collections import defaultdict, deque

from database import db
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class DependencyResolverOptimized:
    """
    Optimized resolver with full dynamic programming.

    Key improvements:
    1. Memoization cache stores fully resolved dependency trees
    2. API results are cached to avoid redundant network calls
    3. Shared nodes reuse computation instead of re-resolving
    4. Database queries check for already-resolved dependencies
    """

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self.db_path = DATABASE_PATH

        # Memoization caches
        self.resolved_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}  # Full resolution results
        self.api_cache: Dict[Tuple[str, str, Optional[str]], List[Dict[str, Any]]] = {}  # API call results

        self._init_tables()

    def _init_tables(self):
        """Ensure transitive dependency tables exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transitive_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_name TEXT NOT NULL,
                    ecosystem TEXT NOT NULL,
                    version_spec TEXT,
                    depends_on_package TEXT NOT NULL,
                    depends_on_ecosystem TEXT NOT NULL,
                    depends_on_version TEXT,
                    dependency_depth INTEGER DEFAULT 1,
                    resolved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(package_name, ecosystem, depends_on_package, depends_on_ecosystem)
                )
            """)
            conn.commit()

    def _get_from_cache_or_api(self, package_name: str, ecosystem: str,
                               version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get dependencies from cache or API (with caching).

        This is the key optimization - we never make the same API call twice.
        """
        cache_key = (package_name, ecosystem, version)

        # Check in-memory cache first
        if cache_key in self.api_cache:
            logger.debug(f"Cache hit for {package_name} ({ecosystem})")
            return self.api_cache[cache_key]

        # Check database cache
        db_cached = self._get_from_db_cache(package_name, ecosystem)
        if db_cached is not None:
            logger.debug(f"Database cache hit for {package_name} ({ecosystem})")
            self.api_cache[cache_key] = db_cached
            return db_cached

        # Make API call
        logger.debug(f"API call for {package_name} ({ecosystem})")
        dependencies = self._resolve_from_api(package_name, ecosystem, version)

        # Store in cache
        self.api_cache[cache_key] = dependencies

        return dependencies

    def _get_from_db_cache(self, package_name: str, ecosystem: str) -> Optional[List[Dict[str, Any]]]:
        """Get previously resolved dependencies from database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT depends_on_package, depends_on_ecosystem, depends_on_version
                FROM transitive_dependencies
                WHERE package_name = ? AND ecosystem = ? AND dependency_depth = 1
            """, (package_name, ecosystem))

            rows = cursor.fetchall()

        if not rows:
            return None

        return [
            {
                'name': row['depends_on_package'],
                'ecosystem': row['depends_on_ecosystem'],
                'version': row['depends_on_version']
            }
            for row in rows
        ]

    def _resolve_from_api(self, package_name: str, ecosystem: str,
                         version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Resolve dependencies from package registry APIs."""
        ecosystem_lower = ecosystem.lower()

        if ecosystem_lower == 'pypi':
            return self._resolve_pypi_dependencies(package_name, version)
        elif ecosystem_lower == 'npm':
            return self._resolve_npm_dependencies(package_name, version)
        elif ecosystem_lower == 'maven':
            return self._resolve_maven_dependencies(package_name, version)
        elif ecosystem_lower == 'go':
            return self._resolve_go_dependencies(package_name, version)
        else:
            logger.warning(f"Ecosystem {ecosystem} not supported for dependency resolution")
            return []

    def _resolve_pypi_dependencies(self, package_name: str,
                                   version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Resolve dependencies for a PyPI package."""
        try:
            if version and version.strip():
                clean_version = version.strip().lstrip('>=<~^!=')
                url = f"https://pypi.org/pypi/{package_name}/{clean_version}/json"
            else:
                url = f"https://pypi.org/pypi/{package_name}/json"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                dependencies = []

                info = data.get('info', {})
                requires_dist = info.get('requires_dist', [])

                if requires_dist:
                    for req in requires_dist:
                        dep_info = self._parse_requirement(req)
                        if dep_info:
                            dependencies.append(dep_info)

                return dependencies
            else:
                logger.warning(f"PyPI API returned {response.status_code} for {package_name}")
                return []

        except Exception as e:
            logger.error(f"Error resolving PyPI deps for {package_name}: {e}")
            return []

    def _parse_requirement(self, requirement_string: str) -> Optional[Dict[str, Any]]:
        """Parse a PEP 508 requirement string."""
        import re
        base_req = requirement_string.split(';')[0].strip()
        base_req = re.sub(r'\[.*?\]', '', base_req)
        match = re.match(r'^([a-zA-Z0-9\-_.]+)\s*(.*)$', base_req)

        if match:
            return {
                'name': match.group(1),
                'version': match.group(2).strip('() '),
                'ecosystem': 'pypi'
            }
        return None

    def _resolve_npm_dependencies(self, package_name: str,
                                  version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Resolve dependencies for an npm package."""
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                dependencies = []

                if version and version.strip():
                    clean_version = version.strip().lstrip('^~>=<')
                    version_data = data.get('versions', {}).get(clean_version)
                else:
                    latest_version = data.get('dist-tags', {}).get('latest')
                    version_data = data.get('versions', {}).get(latest_version)

                if version_data:
                    deps = version_data.get('dependencies', {})
                    for dep_name, dep_version in deps.items():
                        dependencies.append({
                            'name': dep_name,
                            'version': dep_version,
                            'ecosystem': 'npm'
                        })

                return dependencies
            else:
                return []

        except Exception as e:
            logger.error(f"Error resolving npm deps for {package_name}: {e}")
            return []

    def _resolve_maven_dependencies(self, package_name: str,
                                    version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Resolve dependencies for a Maven package (stub)."""
        logger.warning("Maven dependency resolution not fully implemented")
        return []

    def _resolve_go_dependencies(self, package_name: str,
                                 version: Optional[str] = None) -> List[Dict[str, Any]]:
        """Resolve dependencies for a Go package (stub)."""
        logger.warning("Go dependency resolution not fully implemented")
        return []

    def resolve_recursive(self, package_name: str, ecosystem: str,
                         version: Optional[str] = None,
                         depth: int = 0) -> Dict[str, Any]:
        """
        Recursively resolve all transitive dependencies with full memoization.

        This is the key method with dynamic programming optimization.
        Every unique (package, ecosystem) pair is resolved exactly once.

        Args:
            package_name: Name of the package
            ecosystem: Package ecosystem
            version: Optional version specifier
            depth: Current depth in dependency tree

        Returns:
            Dictionary containing fully resolved dependency tree
        """
        # Create unique identifier
        package_id = (package_name, ecosystem)

        # Check memoization cache FIRST - this is the DP optimization
        if package_id in self.resolved_cache:
            cached_result = self.resolved_cache[package_id].copy()
            cached_result['depth'] = depth  # Update depth for this context
            cached_result['from_cache'] = True
            logger.debug(f"Reusing cached resolution for {package_name}")
            return cached_result

        # Check max depth
        if depth >= self.max_depth:
            result = {
                'name': package_name,
                'ecosystem': ecosystem,
                'version': version,
                'depth': depth,
                'max_depth_reached': True,
                'dependencies': []
            }
            # Don't cache depth-limited results
            return result

        # Resolve direct dependencies (using API cache)
        dependencies = self._get_from_cache_or_api(package_name, ecosystem, version)

        # Store transitive dependencies in database
        for dep in dependencies:
            self._store_transitive_dependency(
                package_name=package_name,
                ecosystem=ecosystem,
                version_spec=version,
                depends_on_package=dep['name'],
                depends_on_ecosystem=dep['ecosystem'],
                depends_on_version=dep.get('version'),
                depth=depth + 1
            )

        # Recursively resolve each dependency (they will use cache if already resolved)
        resolved_deps = []
        for dep in dependencies:
            resolved_dep = self.resolve_recursive(
                package_name=dep['name'],
                ecosystem=dep['ecosystem'],
                version=dep.get('version'),
                depth=depth + 1
            )
            resolved_deps.append(resolved_dep)

        # Build result
        result = {
            'name': package_name,
            'ecosystem': ecosystem,
            'version': version,
            'depth': depth,
            'direct_dependencies': len(dependencies),
            'dependencies': resolved_deps,
            'from_cache': False
        }

        # Cache the result (this is the memoization)
        self.resolved_cache[package_id] = result.copy()

        logger.info(f"Resolved {package_name}: {len(dependencies)} direct deps, "
                   f"{len(resolved_deps)} total in tree")

        return result

    def _store_transitive_dependency(self, package_name: str, ecosystem: str,
                                    version_spec: Optional[str],
                                    depends_on_package: str,
                                    depends_on_ecosystem: str,
                                    depends_on_version: Optional[str],
                                    depth: int):
        """Store a transitive dependency relationship."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO transitive_dependencies
                (package_name, ecosystem, version_spec, depends_on_package,
                 depends_on_ecosystem, depends_on_version, dependency_depth, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                package_name, ecosystem, version_spec,
                depends_on_package, depends_on_ecosystem, depends_on_version,
                depth, datetime.now().isoformat()
            ))
            conn.commit()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cache usage (useful for debugging)."""
        return {
            'resolved_packages_cached': len(self.resolved_cache),
            'api_calls_cached': len(self.api_cache),
            'cache_hit_rate': self._calculate_cache_hit_rate()
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate if we're tracking it."""
        # This is a simplified version - you could add counters for hits/misses
        return 0.0

    def clear_cache(self):
        """Clear in-memory caches (useful for testing or memory management)."""
        self.resolved_cache.clear()
        self.api_cache.clear()
        logger.info("Caches cleared")

    def resolve_all_project_dependencies(self, project_id: int) -> Dict[str, Any]:
        """
        Resolve all transitive dependencies for a project with full DP optimization.

        Args:
            project_id: Database ID of the project

        Returns:
            Summary of resolved dependencies with cache statistics
        """
        # Get project's direct dependencies
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dependency_name, ecosystem, version_spec
                FROM dependencies
                WHERE project_id = ?
            """, (project_id,))
            dependencies = [dict(row) for row in cursor.fetchall()]

        logger.info(f"Resolving transitive dependencies for project {project_id} "
                   f"({len(dependencies)} direct deps)")

        all_resolved = []
        total_transitive = 0

        for dep in dependencies:
            logger.info(f"Resolving {dep['dependency_name']} ({dep['ecosystem']})...")
            resolved = self.resolve_recursive(
                package_name=dep['dependency_name'],
                ecosystem=dep['ecosystem'],
                version=dep.get('version_spec')
            )
            all_resolved.append(resolved)

            # Count transitive dependencies
            transitive_count = self._count_dependencies(resolved)
            total_transitive += transitive_count

        cache_stats = self.get_cache_stats()

        return {
            'project_id': project_id,
            'direct_dependencies': len(dependencies),
            'total_transitive_dependencies': total_transitive,
            'dependency_tree': all_resolved,
            'cache_stats': cache_stats
        }

    def _count_dependencies(self, dep_tree: Dict[str, Any]) -> int:
        """Recursively count all dependencies in a tree."""
        count = len(dep_tree.get('dependencies', []))
        for child in dep_tree.get('dependencies', []):
            count += self._count_dependencies(child)
        return count

    def get_all_transitive_dependencies(self, package_name: str,
                                       ecosystem: str) -> List[Dict[str, Any]]:
        """
        Get all known transitive dependencies for a package from the database.

        This performs a breadth-first search through the transitive_dependencies table.
        """
        all_deps = []
        visited = set()
        queue = deque([(package_name, ecosystem, 0)])

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            while queue:
                current_pkg, current_eco, depth = queue.popleft()
                pkg_id = (current_pkg, current_eco)

                if pkg_id in visited or depth > self.max_depth:
                    continue

                visited.add(pkg_id)

                cursor = conn.cursor()
                cursor.execute("""
                    SELECT depends_on_package, depends_on_ecosystem, depends_on_version, dependency_depth
                    FROM transitive_dependencies
                    WHERE package_name = ? AND ecosystem = ?
                """, (current_pkg, current_eco))

                rows = cursor.fetchall()
                for row in rows:
                    dep_info = dict(row)
                    all_deps.append({
                        'package_name': dep_info['depends_on_package'],
                        'ecosystem': dep_info['depends_on_ecosystem'],
                        'version': dep_info['depends_on_version'],
                        'depth': depth + 1
                    })

                    queue.append((
                        dep_info['depends_on_package'],
                        dep_info['depends_on_ecosystem'],
                        depth + 1
                    ))

        return all_deps

    def find_packages_affected_by_dependency(self, dependency_name: str,
                                            ecosystem: str) -> List[Dict[str, Any]]:
        """
        Find all packages that depend on a given package (reverse dependency lookup).

        This is useful for CVE impact analysis.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT package_name, ecosystem, version_spec, dependency_depth
                FROM transitive_dependencies
                WHERE depends_on_package = ? AND depends_on_ecosystem = ?
                ORDER BY dependency_depth
            """, (dependency_name, ecosystem))

            affected = [dict(row) for row in cursor.fetchall()]

        logger.info(f"Found {len(affected)} packages affected by {dependency_name}")
        return affected


# For backward compatibility, create an alias
DependencyResolver = DependencyResolverOptimized
