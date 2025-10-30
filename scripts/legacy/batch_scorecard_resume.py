#!/usr/bin/env python3
"""
Batch Scorecard Calculator with Resume Capability

This script reads GitHub tokens from tokens.env and processes repositories
from a CSV file in parallel using multiple tokens to calculate OpenSSF Scorecard scores.
It can resume from previous runs by skipping already processed repositories.
"""

import os
import csv
import subprocess
import sys
import signal
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set
import threading
import time
import re


# Global variables for graceful shutdown
_results = []
_output_file = "scorecard_results.txt"
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global _shutdown_requested
    print(f"\n\nReceived signal {signum}. Gracefully shutting down...")
    print("Saving partial results...")
    _shutdown_requested = True
    
    if _results:
        append_results(_results, _output_file)
        print_summary(_results)
        print("Partial results saved successfully.")
    else:
        print("No results to save.")
    
    sys.exit(0)


class TokenPool:
    """Thread-safe token pool for distributing tokens across workers."""
    
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.lock = threading.Lock()
        self.current_index = 0
    
    def get_next_token(self) -> str:
        """Get the next token in round-robin fashion."""
        with self.lock:
            token = self.tokens[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.tokens)
            return token


def load_tokens(tokens_file: str = "tokens.env") -> List[str]:
    """
    Load GitHub tokens from tokens.env file.
    
    Expected format:
        GITHUB_TOKEN=token1
        GITHUB_TOKEN=token2
        # or
        GITHUB_AUTH_TOKEN=token1,token2,token3
    """
    tokens = []
    
    if not os.path.exists(tokens_file):
        print(f"Error: {tokens_file} not found!")
        sys.exit(1)
    
    with open(tokens_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse environment variable format
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                # Check if it's a GitHub token variable
                if key in ['GITHUB_TOKEN', 'GITHUB_AUTH_TOKEN', 'GH_TOKEN', 'GH_AUTH_TOKEN']:
                    # Handle comma-separated tokens
                    if ',' in value:
                        tokens.extend([t.strip() for t in value.split(',') if t.strip()])
                    elif value:
                        tokens.append(value)
    
    if not tokens:
        print(f"Error: No valid GitHub tokens found in {tokens_file}!")
        print("Expected format:")
        print("  GITHUB_TOKEN=your_token_here")
        print("  # or")
        print("  GITHUB_AUTH_TOKEN=token1,token2,token3")
        sys.exit(1)
    
    print(f"Loaded {len(tokens)} GitHub token(s)")
    return tokens


def load_processed_repositories(output_file: str) -> Set[str]:
    """
    Load already processed repositories from existing output file.
    
    Returns:
        Set of repository URLs that have already been processed
    """
    processed_repos = set()
    
    if not os.path.exists(output_file):
        print(f"No existing output file found. Starting fresh.")
        return processed_repos
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract repository URLs from existing results
        import re
        repo_matches = re.findall(r'Repository: (https?://[^\n]+)', content)
        processed_repos = set(repo_matches)
        
        print(f"Found {len(processed_repos)} already processed repositories")
        
        # Show some examples of processed repos
        if processed_repos:
            print("Examples of already processed repositories:")
            for i, repo in enumerate(list(processed_repos)[:3]):
                print(f"  - {repo}")
            if len(processed_repos) > 3:
                print(f"  ... and {len(processed_repos) - 3} more")
        
    except Exception as e:
        print(f"Warning: Error reading existing output file: {e}")
        print("Starting fresh to avoid data corruption.")
        processed_repos = set()
    
    return processed_repos


def load_repositories(csv_file: str, processed_repos: Set[str]) -> List[Tuple[str, str, str]]:
    """
    Load repositories from CSV file, excluding already processed ones.
    
    Args:
        csv_file: Path to CSV file
        processed_repos: Set of already processed repository URLs
    
    Returns:
        List of tuples: (category, project_name, repo_url) for unprocessed repos
    """
    repositories = []
    skipped_count = 0
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        sys.exit(1)
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Try to detect delimiter
        sample = f.read(1024)
        f.seek(0)
        
        delimiter = ';' if ';' in sample else ','
        reader = csv.DictReader(f, delimiter=delimiter)
        
        for row in reader:
            # Handle different possible column names
            category = row.get('Category', row.get('category', 'Unknown'))
            project = row.get('Project', row.get('project', row.get('Project Name', 'Unknown')))
            repo_url = row.get('Repository URL', row.get('repository_url', row.get('URL', '')))
            
            if repo_url and 'github.com' in repo_url:
                if repo_url in processed_repos:
                    skipped_count += 1
                    print(f"Skipping already processed: {project}")
                else:
                    repositories.append((category, project, repo_url))
    
    print(f"Loaded {len(repositories)} unprocessed repositories from {csv_file}")
    print(f"Skipped {skipped_count} already processed repositories")
    return repositories


def extract_repo_path(repo_url: str) -> str:
    """Extract owner/repo from GitHub URL."""
    # Remove trailing slashes and .git
    repo_url = repo_url.rstrip('/').rstrip('.git')
    
    # Extract owner/repo from various GitHub URL formats
    patterns = [
        r'github\.com/([^/]+/[^/]+)',
        r'github\.com/([^/]+/[^/]+)/',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, repo_url)
        if match:
            return match.group(1)
    
    return repo_url


def run_scorecard(repo_url: str, token: str, timeout: int = 300) -> Dict[str, Any]:
    """
    Run scorecard on a single repository.
    
    Args:
        repo_url: GitHub repository URL
        token: GitHub token for authentication
        timeout: Timeout in seconds
    
    Returns:
        Dictionary containing scorecard results
    """
    repo_path = extract_repo_path(repo_url)
    
    # Prepare environment with token
    env = os.environ.copy()
    env['GITHUB_AUTH_TOKEN'] = token
    
    # Run scorecard command with JSON output
    cmd = [
        'scorecard',
        f'--repo=github.com/{repo_path}',
        '--format=json'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        
        if result.returncode == 0:
            # Parse JSON output
            scorecard_data = json.loads(result.stdout)
            return {
                'status': 'SUCCESS',
                'repo_url': repo_url,
                'repo_path': repo_path,
                'data': scorecard_data
            }
        else:
            return {
                'status': 'ERROR',
                'repo_url': repo_url,
                'repo_path': repo_path,
                'error': result.stderr.strip() or result.stdout.strip()
            }
    
    except subprocess.TimeoutExpired:
        return {
            'status': 'TIMEOUT',
            'repo_url': repo_url,
            'repo_path': repo_path,
            'error': f'Command timed out after {timeout} seconds'
        }
    except json.JSONDecodeError as e:
        return {
            'status': 'JSON_ERROR',
            'repo_url': repo_url,
            'repo_path': repo_path,
            'error': f'Failed to parse JSON output: {str(e)}'
        }
    except Exception as e:
        return {
            'status': 'EXCEPTION',
            'repo_url': repo_url,
            'repo_path': repo_path,
            'error': str(e)
        }


def process_repository(args: Tuple[Tuple[str, str, str], TokenPool, int]) -> Dict[str, Any]:
    """
    Process a single repository with scorecard.
    
    Args:
        args: Tuple containing (repo_info, token_pool, timeout)
    
    Returns:
        Dictionary containing results
    """
    (category, project, repo_url), token_pool, timeout = args
    
    if _shutdown_requested:
        return None
    
    token = token_pool.get_next_token()
    
    print(f"Processing: {project} ({repo_url})")
    
    result = run_scorecard(repo_url, token, timeout)
    result['category'] = category
    result['project'] = project
    
    return result


def format_scorecard_result(result: Dict[str, Any]) -> str:
    """Format a single scorecard result for output."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"Repository: {result['repo_url']}")
    lines.append(f"Project: {result['project']}")
    lines.append(f"Category: {result['category']}")
    lines.append(f"Status: {result['status']}")
    lines.append("-" * 80)
    
    if result['status'] == 'SUCCESS':
        data = result['data']
        
        # Basic repository info
        repo_info = data.get('repo', {})
        lines.append(f"repo.name: {repo_info.get('name', 'N/A')}")
        lines.append(f"repo.commit: {repo_info.get('commit', 'N/A')}")
        
        # Aggregate score
        aggregate_score = data.get('score', 'N/A')
        lines.append(f"aggregate_score: {aggregate_score}")
        
        # Individual check scores
        checks = data.get('checks', [])
        lines.append(f"total_checks: {len(checks)}")
        
        for check in checks:
            check_name = check.get('name', 'Unknown')
            check_score = check.get('score', 'N/A')
            check_reason = check.get('reason', 'N/A')
            lines.append(f"check.{check_name}.score: {check_score}")
            lines.append(f"check.{check_name}.reason: {check_reason}")
        
        # Metadata
        metadata = data.get('metadata', {})
        if metadata:
            lines.append(f"metadata.collected_at: {metadata.get('collected', 'N/A')}")
    
    else:
        lines.append(f"error: {result.get('error', 'Unknown error')}")
    
    lines.append("")
    return "\n".join(lines)


def append_results(results: List[Dict[str, Any]], output_file: str):
    """Append new results to output file."""
    with open(output_file, 'a', encoding='utf-8') as f:
        for result in results:
            if result:  # Skip None results from shutdown
                f.write(format_scorecard_result(result))
                f.write("\n")


def print_summary(results: List[Dict[str, Any]]):
    """Print summary statistics."""
    if not results:
        print("No new results to summarize.")
        return
    
    # Filter out None results
    valid_results = [r for r in results if r is not None]
    
    total = len(valid_results)
    success = len([r for r in valid_results if r['status'] == 'SUCCESS'])
    errors = len([r for r in valid_results if r['status'] == 'ERROR'])
    timeouts = len([r for r in valid_results if r['status'] == 'TIMEOUT'])
    json_errors = len([r for r in valid_results if r['status'] == 'JSON_ERROR'])
    exceptions = len([r for r in valid_results if r['status'] == 'EXCEPTION'])
    
    print(f"\n{'='*60}")
    print("BATCH SCORECARD SUMMARY (NEW RESULTS ONLY)")
    print(f"{'='*60}")
    print(f"New repositories processed: {total}")
    print(f"Successful: {success} ({success/total*100:.1f}%)")
    print(f"Errors: {errors} ({errors/total*100:.1f}%)")
    print(f"Timeouts: {timeouts} ({timeouts/total*100:.1f}%)")
    print(f"JSON parsing errors: {json_errors} ({json_errors/total*100:.1f}%)")
    print(f"Exceptions: {exceptions} ({exceptions/total*100:.1f}%)")
    
    # Score statistics for successful results
    successful_results = [r for r in valid_results if r['status'] == 'SUCCESS']
    if successful_results:
        scores = []
        for result in successful_results:
            score = result['data'].get('score')
            if score is not None and isinstance(score, (int, float)):
                scores.append(score)
        
        if scores:
            print(f"\nScore Statistics for new results (n={len(scores)}):")
            print(f"  Mean score: {sum(scores)/len(scores):.2f}")
            print(f"  Min score: {min(scores):.2f}")
            print(f"  Max score: {max(scores):.2f}")


def main():
    """Main function."""
    global _results, _output_file
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Configuration
    csv_file = "projects.csv"
    tokens_file = "tokens.env"
    max_workers = 4
    timeout = 300  # 5 minutes per repository
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2:
        max_workers = int(sys.argv[2])
    if len(sys.argv) > 3:
        timeout = int(sys.argv[3])
    
    print("Batch Scorecard Calculator (Resume Mode)")
    print("=" * 50)
    print(f"CSV file: {csv_file}")
    print(f"Max workers: {max_workers}")
    print(f"Timeout per repo: {timeout} seconds")
    print(f"Output file: {_output_file}")
    
    # Check if scorecard is installed
    try:
        result = subprocess.run(['scorecard', 'version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Error: scorecard command not found or not working!")
            print("Please install scorecard using: brew install scorecard")
            sys.exit(1)
        # Extract version from output
        version_line = [line for line in result.stdout.split('\n') if 'GitVersion:' in line]
        if version_line:
            version = version_line[0].split(':')[1].strip()
            print(f"Scorecard version: {version}")
        else:
            print("Scorecard is installed and working")
    except FileNotFoundError:
        print("Error: scorecard command not found!")
        print("Please install scorecard using: brew install scorecard")
        sys.exit(1)
    
    # Load tokens and processed repositories
    tokens = load_tokens(tokens_file)
    processed_repos = load_processed_repositories(_output_file)
    repositories = load_repositories(csv_file, processed_repos)
    
    if not repositories:
        print("No unprocessed repositories found!")
        print("All repositories have already been processed.")
        sys.exit(0)
    
    # Create token pool
    token_pool = TokenPool(tokens)
    
    # Prepare arguments for parallel processing
    args_list = [(repo_info, token_pool, timeout) for repo_info in repositories]
    
    # Process repositories in parallel
    print(f"\nStarting parallel processing with {max_workers} workers...")
    print(f"Processing {len(repositories)} remaining repositories...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_repo = {
            executor.submit(process_repository, args): args[0] 
            for args in args_list
        }
        
        # Process completed tasks
        for future in as_completed(future_to_repo):
            if _shutdown_requested:
                break
                
            try:
                result = future.result()
                if result:
                    _results.append(result)
                    
                    # Append result immediately to file
                    append_results([result], _output_file)
                    
                    # Print progress
                    completed = len(_results)
                    total = len(repositories)
                    percentage = (completed / total) * 100
                    print(f"Progress: {completed}/{total} ({percentage:.1f}%) - "
                          f"Latest: {result['project']} ({result['status']})")
                    
            except Exception as e:
                repo_info = future_to_repo[future]
                print(f"Error processing {repo_info[1]}: {e}")
    
    # Print final summary
    if _results:
        print_summary(_results)
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"\nTotal processing time: {duration:.1f} seconds")
        print(f"Average time per repository: {duration/len(_results):.1f} seconds")
        print(f"\nResults appended to: {_output_file}")
        
        # Show total statistics
        try:
            with open(_output_file, 'r') as f:
                content = f.read()
            total_repos = len(re.findall(r'Repository:', content))
            total_success = len(re.findall(r'Status: SUCCESS', content))
            print(f"\nOverall statistics:")
            print(f"Total repositories in file: {total_repos}")
            print(f"Total successful: {total_success}")
            print(f"Overall success rate: {total_success/total_repos*100:.1f}%")
        except:
            pass
    else:
        print("No new results processed.")


if __name__ == "__main__":
    main()
