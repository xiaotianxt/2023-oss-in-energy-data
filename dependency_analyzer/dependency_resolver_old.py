"""Recursive dependency resolution for packages."""

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


class DependencyResolver:
    """Resolves transitive (recursive) dependencies for packages."""

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        self.db_path = DATABASE_PATH
        # Ensure CVE tables exist (will be created by CVEScanner, but safe to call again)
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

    def resolve_pypi_dependencies(self, package_name: str,
                                  version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Resolve dependencies for a PyPI package using PyPI JSON API.

        Args:
            package_name: Name of the package
            version: Optional specific version (uses latest if not specified)

        Returns:
            List of dependency dictionaries
        """
        try:
            # Use PyPI JSON API
            if version and version.strip():
                # Clean version string
                clean_version = version.strip().lstrip('>=<~^!=')
                url = f"https://pypi.org/pypi/{package_name}/{clean_version}/json"
            else:
                url = f"https://pypi.org/pypi/{package_name}/json"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                dependencies = []

                # Extract requires_dist
                info = data.get('info', {})
                requires_dist = info.get('requires_dist', [])

                if requires_dist:
                    for req in requires_dist:
                        # Parse requirement string (e.g., "requests (>=2.0.0)")
                        dep_info = self._parse_requirement(req)
                        if dep_info:
                            dependencies.append(dep_info)

                logger.debug(f"Resolved {len(dependencies)} dependencies for {package_name}")
                return dependencies
            else:
                logger.warning(f"PyPI API returned {response.status_code} for {package_name}")
                return []

        except requests.RequestException as e:
            logger.error(f"Error querying PyPI for {package_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error resolving PyPI deps for {package_name}: {e}")
            return []

    def _parse_requirement(self, requirement_string: str) -> Optional[Dict[str, Any]]:
        """Parse a PEP 508 requirement string."""
        import re

        # Remove extras and environment markers
        # Example: "requests[security] (>=2.0.0) ; python_version < '3.0'"
        base_req = requirement_string.split(';')[0].strip()

        # Remove extras
        base_req = re.sub(r'\[.*?\]', '', base_req)

        # Extract package name and version
        match = re.match(r'^([a-zA-Z0-9\-_.]+)\s*(.*)$', base_req)

        if match:
            name = match.group(1)
            version_spec = match.group(2).strip('() ')

            return {
                'name': name,
                'version': version_spec,
                'ecosystem': 'pypi'
            }

        return None

    def resolve_npm_dependencies(self, package_name: str,
                                 version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Resolve dependencies for an npm package using npm registry API.

        Args:
            package_name: Name of the package
            version: Optional specific version

        Returns:
            List of dependency dictionaries
        """
        try:
            url = f"https://registry.npmjs.org/{package_name}"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                dependencies = []

                # Get the latest version or specified version
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

                logger.debug(f"Resolved {len(dependencies)} dependencies for {package_name}")
                return dependencies
            else:
                logger.warning(f"npm registry returned {response.status_code} for {package_name}")
                return []

        except requests.RequestException as e:
            logger.error(f"Error querying npm registry for {package_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error resolving npm deps for {package_name}: {e}")
            return []

    def resolve_maven_dependencies(self, package_name: str,
                                   version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Resolve dependencies for a Maven package.

        Note: This requires access to Maven Central and parsing POM files.
        For simplicity, we'll skip full implementation here.
        """
        logger.warning("Maven dependency resolution not fully implemented")
        return []

    def resolve_go_dependencies(self, package_name: str,
                                version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Resolve dependencies for a Go package.

        Note: Go modules can be resolved using pkg.go.dev API.
        """
        logger.warning("Go dependency resolution not fully implemented")
        return []

    def resolve_dependencies(self, package_name: str, ecosystem: str,
                           version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Resolve dependencies for a package based on ecosystem.

        Args:
            package_name: Name of the package
            ecosystem: Package ecosystem (pypi, npm, maven, etc.)
            version: Optional version specifier

        Returns:
            List of dependencies
        """
        ecosystem_lower = ecosystem.lower()

        if ecosystem_lower == 'pypi':
            return self.resolve_pypi_dependencies(package_name, version)
        elif ecosystem_lower == 'npm':
            return self.resolve_npm_dependencies(package_name, version)
        elif ecosystem_lower == 'maven':
            return self.resolve_maven_dependencies(package_name, version)
        elif ecosystem_lower == 'go':
            return self.resolve_go_dependencies(package_name, version)
        else:
            logger.warning(f"Ecosystem {ecosystem} not supported for dependency resolution")
            return []

    def resolve_recursive(self, package_name: str, ecosystem: str,
                         version: Optional[str] = None,
                         depth: int = 0,
                         visited: Optional[Set[Tuple[str, str]]] = None) -> Dict[str, Any]:
        """
        Recursively resolve all transitive dependencies.

        Args:
            package_name: Name of the package
            ecosystem: Package ecosystem
            version: Optional version specifier
            depth: Current depth in dependency tree
            visited: Set of already visited (package, ecosystem) tuples

        Returns:
            Dictionary containing dependency tree
        """
        if visited is None:
            visited = set()

        # Create unique identifier for this package
        package_id = (package_name, ecosystem)

        # Check if we've already processed this package
        if package_id in visited:
            return {
                'name': package_name,
                'ecosystem': ecosystem,
                'version': version,
                'depth': depth,
                'already_visited': True,
                'dependencies': []
            }

        # Check max depth
        if depth >= self.max_depth:
            logger.debug(f"Max depth reached for {package_name}")
            return {
                'name': package_name,
                'ecosystem': ecosystem,
                'version': version,
                'depth': depth,
                'max_depth_reached': True,
                'dependencies': []
            }

        # Mark as visited
        visited.add(package_id)

        # Resolve direct dependencies
        dependencies = self.resolve_dependencies(package_name, ecosystem, version)

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

        # Recursively resolve each dependency
        resolved_deps = []
        for dep in dependencies:
            resolved_dep = self.resolve_recursive(
                package_name=dep['name'],
                ecosystem=dep['ecosystem'],
                version=dep.get('version'),
                depth=depth + 1,
                visited=visited
            )
            resolved_deps.append(resolved_dep)

        return {
            'name': package_name,
            'ecosystem': ecosystem,
            'version': version,
            'depth': depth,
            'direct_dependencies': len(dependencies),
            'dependencies': resolved_deps
        }

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

    def resolve_all_project_dependencies(self, project_id: int) -> Dict[str, Any]:
        """
        Resolve all transitive dependencies for a project.

        Args:
            project_id: Database ID of the project

        Returns:
            Summary of resolved dependencies
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

        logger.info(f"Resolving transitive dependencies for project {project_id} ({len(dependencies)} direct deps)")

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

        return {
            'project_id': project_id,
            'direct_dependencies': len(dependencies),
            'total_transitive_dependencies': total_transitive,
            'dependency_tree': all_resolved
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

                # Get direct dependencies
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

                    # Add to queue for BFS
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

        This is useful for CVE impact analysis - if a package has a CVE,
        we can find all packages that depend on it.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all packages that directly depend on this package
            cursor.execute("""
                SELECT DISTINCT package_name, ecosystem, version_spec, dependency_depth
                FROM transitive_dependencies
                WHERE depends_on_package = ? AND depends_on_ecosystem = ?
                ORDER BY dependency_depth
            """, (dependency_name, ecosystem))

            affected = [dict(row) for row in cursor.fetchall()]

        logger.info(f"Found {len(affected)} packages affected by {dependency_name}")
        return affected


def main():
    """Main function for dependency resolution."""
    logging.basicConfig(level=logging.INFO)

    resolver = DependencyResolver(max_depth=3)

    # Example: Resolve dependencies for a popular package
    print("="*60)
    print("DEPENDENCY RESOLUTION")
    print("="*60)

    # Test with a well-known package
    test_packages = [
        ('requests', 'pypi'),
        ('express', 'npm'),
    ]

    for package_name, ecosystem in test_packages:
        print(f"\nResolving dependencies for {package_name} ({ecosystem})...")
        result = resolver.resolve_recursive(package_name, ecosystem)

        print(f"  Direct dependencies: {result.get('direct_dependencies', 0)}")
        print(f"  Depth: {result.get('depth', 0)}")

        # Show dependency tree
        def print_tree(node, indent=0):
            if node.get('already_visited'):
                print("  " * indent + f"↻ {node['name']} (already visited)")
                return
            if node.get('max_depth_reached'):
                print("  " * indent + f"⋯ {node['name']} (max depth)")
                return

            print("  " * indent + f"├─ {node['name']} ({node.get('ecosystem', 'unknown')})")
            for dep in node.get('dependencies', []):
                print_tree(dep, indent + 1)

        print_tree(result)


if __name__ == "__main__":
    main()
