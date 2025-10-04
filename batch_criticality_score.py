#!/usr/bin/env python3
"""
Batch Criticality Score Calculator

This script reads GitHub tokens from tokens.env and processes repositories
from a CSV file in parallel using multiple tokens.
"""

import os
import csv
import subprocess
import sys
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple
import threading
import time


# Global variables for graceful shutdown
_results = []
_output_file = "criticality_scores.txt"
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global _shutdown_requested
    print(f"\n\nReceived signal {signum}. Gracefully shutting down...")
    print("Saving partial results...")
    _shutdown_requested = True
    
    if _results:
        save_results(_results, _output_file)
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
        print("  or")
        print("  GITHUB_AUTH_TOKEN=token1,token2,token3")
        sys.exit(1)
    
    print(f"Loaded {len(tokens)} GitHub token(s)")
    return tokens


def load_repos_from_csv(csv_file: str, column_name: str = "Repository URL") -> List[str]:
    """
    Load repository URLs from a CSV file.
    
    Args:
        csv_file: Path to the CSV file
        column_name: Name of the column containing repository URLs
    
    Returns:
        List of repository URLs
    """
    repos = []
    
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        sys.exit(1)
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        
        # Check if column exists
        if column_name not in reader.fieldnames:
            print(f"Error: Column '{column_name}' not found in CSV!")
            print(f"Available columns: {', '.join(reader.fieldnames)}")
            sys.exit(1)
        
        for row in reader:
            repo_url = row[column_name].strip()
            if repo_url and repo_url.startswith('https://github.com/'):
                repos.append(repo_url)
    
    print(f"Loaded {len(repos)} repository URL(s) from {csv_file}")
    return repos


def run_criticality_score(repo_url: str, token: str, worker_id: int) -> Tuple[str, bool, str]:
    """
    Run criticality_score command for a single repository.
    
    Args:
        repo_url: GitHub repository URL
        token: GitHub token to use
        worker_id: Worker thread ID for logging
    
    Returns:
        Tuple of (repo_url, success, output/error)
    """
    try:
        print(f"[Worker {worker_id}] Processing: {repo_url}")
        
        # Set up environment with the token
        env = os.environ.copy()
        env['GITHUB_TOKEN'] = token
        
        # Run criticality_score command
        result = subprocess.run(
            ['criticality_score', '-depsdev-disable', repo_url],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"[Worker {worker_id}] ✓ Success: {repo_url}")
            return (repo_url, True, result.stdout)
        else:
            print(f"[Worker {worker_id}] ✗ Failed: {repo_url}")
            return (repo_url, False, result.stderr)
    
    except subprocess.TimeoutExpired:
        error_msg = f"Timeout after 5 minutes"
        print(f"[Worker {worker_id}] ✗ Timeout: {repo_url}")
        return (repo_url, False, error_msg)
    
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        print(f"[Worker {worker_id}] ✗ Error: {repo_url} - {error_msg}")
        return (repo_url, False, error_msg)


def process_repos_parallel(repos: List[str], token_pool: TokenPool, max_workers: int, output_file: str = "criticality_scores.txt") -> List[Tuple[str, bool, str]]:
    """
    Process repositories in parallel using multiple tokens.
    
    Args:
        repos: List of repository URLs
        token_pool: TokenPool instance for token distribution
        max_workers: Number of parallel workers
        output_file: Output file for periodic saves
    
    Returns:
        List of results (repo_url, success, output)
    """
    global _results, _output_file, _shutdown_requested
    _results = []
    _output_file = output_file
    
    results = []
    completed_count = 0
    save_interval = max(10, len(repos) // 20)  # Save every 10 repos or 5% of total, whichever is larger
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_repo = {}
        for i, repo in enumerate(repos):
            if _shutdown_requested:
                break
            token = token_pool.get_next_token()
            worker_id = i % max_workers
            future = executor.submit(run_criticality_score, repo, token, worker_id)
            future_to_repo[future] = repo
        
        # Collect results as they complete
        for future in as_completed(future_to_repo):
            if _shutdown_requested:
                break
                
            repo = future_to_repo[future]
            try:
                result = future.result()
                results.append(result)
                _results = results  # Update global results
                completed_count += 1
                
                # Periodic save
                if completed_count % save_interval == 0:
                    print(f"\n[INFO] Completed {completed_count}/{len(repos)} repositories. Saving intermediate results...")
                    try:
                        save_results(results, f"{output_file}.partial")
                        print(f"[INFO] Intermediate results saved to {output_file}.partial")
                    except Exception as e:
                        print(f"[WARNING] Failed to save intermediate results: {e}")
                
            except Exception as e:
                print(f"Error processing {repo}: {e}")
                error_result = (repo, False, str(e))
                results.append(error_result)
                _results = results  # Update global results
                completed_count += 1
    
    return results


def save_results(results: List[Tuple[str, bool, str]], output_file: str = "criticality_scores.txt"):
    """
    Save results to an output file.
    
    Args:
        results: List of (repo_url, success, output) tuples
        output_file: Output file path
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for repo_url, success, output in results:
            f.write(f"\n{'='*80}\n")
            f.write(f"Repository: {repo_url}\n")
            f.write(f"Status: {'SUCCESS' if success else 'FAILED'}\n")
            f.write(f"{'-'*80}\n")
            f.write(output)
            f.write(f"\n{'='*80}\n")
    
    print(f"\nResults saved to: {output_file}")


def print_summary(results: List[Tuple[str, bool, str]]):
    """Print a summary of the results."""
    total = len(results)
    success = sum(1 for _, s, _ in results if s)
    failed = total - success
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total repositories: {total}")
    print(f"Successful: {success} ({success/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"{'='*80}\n")


def main():
    """Main function."""
    import argparse
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    parser = argparse.ArgumentParser(
        description='Batch process GitHub repositories with criticality_score',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process repos from projects.csv with default settings
  python batch_criticality_score.py projects.csv
  
  # Specify custom column name and output file
  python batch_criticality_score.py projects.csv -c "Repository URL" -o results.txt
  
  # Use custom tokens file and set worker count
  python batch_criticality_score.py projects.csv -t my_tokens.env -w 10
        """
    )
    
    parser.add_argument('csv_file', help='CSV file containing repository URLs')
    parser.add_argument('-c', '--column', default='Repository URL',
                        help='CSV column name containing repo URLs (default: Repository URL)')
    parser.add_argument('-t', '--tokens', default='tokens.env',
                        help='File containing GitHub tokens (default: tokens.env)')
    parser.add_argument('-o', '--output', default='criticality_scores.txt',
                        help='Output file for results (default: criticality_scores.txt)')
    parser.add_argument('-w', '--workers', type=int, default=None,
                        help='Number of parallel workers (default: number of tokens)')
    
    args = parser.parse_args()
    
    results = []
    start_time = time.time()
    
    try:
        # Load tokens
        tokens = load_tokens(args.tokens)
        token_pool = TokenPool(tokens)
        
        # Load repositories
        repos = load_repos_from_csv(args.csv_file, args.column)
        
        if not repos:
            print("No repositories to process!")
            sys.exit(1)
        
        # Determine number of workers
        max_workers = args.workers if args.workers else len(tokens)
        print(f"Using {max_workers} parallel worker(s)\n")
        
        # Process repositories
        results = process_repos_parallel(repos, token_pool, max_workers, args.output)
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error occurred: {e}")
        print("Saving partial results...")
    finally:
        # Always try to save results, even if there was an error
        elapsed_time = time.time() - start_time
        
        if results:
            try:
                # Save final results
                save_results(results, args.output)
                print_summary(results)
                print(f"Total time: {elapsed_time:.2f} seconds")
                if len(results) > 0:
                    print(f"Average time per repo: {elapsed_time/len(results):.2f} seconds")
                
                # Clean up partial file if final save was successful
                partial_file = f"{args.output}.partial"
                if os.path.exists(partial_file):
                    try:
                        os.remove(partial_file)
                        print(f"Cleaned up partial file: {partial_file}")
                    except:
                        pass  # Ignore cleanup errors
                        
            except Exception as e:
                print(f"Error saving final results: {e}")
                # Try to save to a backup file
                try:
                    backup_file = f"{args.output}.backup"
                    save_results(results, backup_file)
                    print(f"Results saved to backup file: {backup_file}")
                except Exception as backup_e:
                    print(f"Failed to save backup: {backup_e}")
        else:
            print("No results to save.")
        
        print("\nProcess completed.")


if __name__ == '__main__':
    main()
