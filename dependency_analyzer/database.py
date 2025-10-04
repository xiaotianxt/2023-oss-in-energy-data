"""Database models and operations for dependency analysis."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import logging

from config import DATABASE_PATH, DATA_DIR

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for dependency analysis."""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_database()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        DATA_DIR.mkdir(exist_ok=True)
    
    def _init_database(self):
        """Initialize database with required tables."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    category TEXT,
                    language TEXT,
                    stars INTEGER DEFAULT 0,
                    forks INTEGER DEFAULT 0,
                    last_updated TEXT,
                    community_type TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS dependency_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    file_path TEXT,
                    file_type TEXT,
                    content TEXT,
                    parsed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                );
                
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    dependency_name TEXT,
                    version_spec TEXT,
                    dependency_type TEXT,
                    ecosystem TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                );
                
                CREATE TABLE IF NOT EXISTS dependency_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    total_dependencies INTEGER,
                    direct_dependencies INTEGER,
                    unique_dependencies INTEGER,
                    security_issues TEXT,
                    outdated_dependencies TEXT,
                    analysis_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_projects_url ON projects(url);
                CREATE INDEX IF NOT EXISTS idx_dependencies_name ON dependencies(dependency_name);
                CREATE INDEX IF NOT EXISTS idx_dependencies_project ON dependencies(project_id);
            """)
            conn.commit()
    
    def insert_project(self, project_data: Dict[str, Any]) -> int:
        """Insert a new project and return its ID."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO projects 
                (name, url, category, language, stars, forks, last_updated, community_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_data.get('name'),
                project_data.get('url'),
                project_data.get('category'),
                project_data.get('language'),
                project_data.get('stars', 0),
                project_data.get('forks', 0),
                project_data.get('last_updated'),
                project_data.get('community_type')
            ))
            return cursor.lastrowid
    
    def get_project_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get project by URL."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE url = ?", (url,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def insert_dependency_file(self, project_id: int, file_path: str, 
                             file_type: str, content: str) -> int:
        """Insert a dependency file."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dependency_files 
                (project_id, file_path, file_type, content)
                VALUES (?, ?, ?, ?)
            """, (project_id, file_path, file_type, content))
            return cursor.lastrowid
    
    def insert_dependencies(self, dependencies: List[Dict[str, Any]]) -> None:
        """Insert multiple dependencies."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO dependencies 
                (project_id, dependency_name, version_spec, dependency_type, ecosystem)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (dep['project_id'], dep['name'], dep.get('version', ''), 
                 dep.get('type', 'runtime'), dep.get('ecosystem', 'unknown'))
                for dep in dependencies
            ])
            conn.commit()
    
    def get_projects_without_dependencies(self) -> List[Dict[str, Any]]:
        """Get projects that haven't been analyzed for dependencies yet."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.* FROM projects p
                LEFT JOIN dependency_files df ON p.id = df.project_id
                WHERE df.project_id IS NULL
                ORDER BY p.stars DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_dependency_stats(self) -> Dict[str, Any]:
        """Get overall dependency statistics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Total projects
            cursor.execute("SELECT COUNT(*) FROM projects")
            total_projects = cursor.fetchone()[0]
            
            # Projects with dependencies
            cursor.execute("""
                SELECT COUNT(DISTINCT project_id) FROM dependencies
            """)
            projects_with_deps = cursor.fetchone()[0]
            
            # Most common dependencies
            cursor.execute("""
                SELECT dependency_name, COUNT(*) as usage_count
                FROM dependencies
                GROUP BY dependency_name
                ORDER BY usage_count DESC
                LIMIT 20
            """)
            top_dependencies = cursor.fetchall()
            
            # Dependencies by ecosystem
            cursor.execute("""
                SELECT ecosystem, COUNT(*) as count
                FROM dependencies
                GROUP BY ecosystem
                ORDER BY count DESC
            """)
            ecosystem_stats = cursor.fetchall()
            
            return {
                'total_projects': total_projects,
                'projects_with_dependencies': projects_with_deps,
                'top_dependencies': top_dependencies,
                'ecosystem_distribution': ecosystem_stats
            }
    
    def export_to_json(self, output_path: Path) -> None:
        """Export all data to JSON format."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Export projects with their dependencies
            cursor.execute("""
                SELECT p.*, 
                       GROUP_CONCAT(d.dependency_name || ':' || d.version_spec) as dependencies
                FROM projects p
                LEFT JOIN dependencies d ON p.id = d.project_id
                GROUP BY p.id
            """)
            
            projects = []
            for row in cursor.fetchall():
                project = dict(row)
                if project['dependencies']:
                    deps = []
                    for dep_str in project['dependencies'].split(','):
                        name, version = dep_str.split(':', 1)
                        deps.append({'name': name, 'version': version})
                    project['dependencies'] = deps
                else:
                    project['dependencies'] = []
                projects.append(project)
            
            with open(output_path, 'w') as f:
                json.dump(projects, f, indent=2)
            
            logger.info(f"Exported {len(projects)} projects to {output_path}")


# Global database instance
db = DatabaseManager()
