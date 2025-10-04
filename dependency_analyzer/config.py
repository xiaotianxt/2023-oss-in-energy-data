"""Configuration settings for the dependency analyzer."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "dependencies.db"
PROJECTS_YAML_PATH = PROJECT_ROOT.parent / "projects.yaml"

# GitHub API settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_BASE_URL = "https://api.github.com"
RATE_LIMIT_DELAY = 1  # seconds between requests

# Supported dependency files by language
DEPENDENCY_FILES = {
    "python": [
        "requirements.txt",
        "requirements-dev.txt", 
        "requirements-test.txt",
        "setup.py",
        "pyproject.toml",
        "Pipfile",
        "conda.yml",
        "environment.yml"
    ],
    "javascript": [
        "package.json",
        "package-lock.json",
        "yarn.lock"
    ],
    "java": [
        "pom.xml",
        "build.gradle",
        "gradle.properties"
    ],
    "r": [
        "DESCRIPTION",
        "renv.lock"
    ],
    "rust": [
        "Cargo.toml",
        "Cargo.lock"
    ],
    "go": [
        "go.mod",
        "go.sum"
    ],
    "php": [
        "composer.json",
        "composer.lock"
    ]
}

# Analysis settings
MAX_WORKERS = 5  # for concurrent processing
BATCH_SIZE = 50  # projects per batch

