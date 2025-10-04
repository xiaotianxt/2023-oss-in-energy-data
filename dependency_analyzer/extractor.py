"""Main dependency extraction pipeline."""

import logging
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import yaml

from tqdm import tqdm

from database import db
from github_client import GitHubClient
from parsers import DependencyParserFactory
from config import MAX_WORKERS, BATCH_SIZE, PROJECTS_YAML_PATH

logger = logging.getLogger(__name__)


class DependencyExtractor:
    """Main class for extracting dependencies from energy sector projects."""
    
    def __init__(self):
        self.github_client = GitHubClient()
        self.parser_factory = DependencyParserFactory()
    
    def load_projects_from_yaml(self, yaml_path: Path = PROJECTS_YAML_PATH) -> List[Dict[str, Any]]:
        """Load projects from YAML file and convert to list format."""
        projects = []
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Convert YAML structure to flat list
            for category, category_projects in data.items():
                if isinstance(category_projects, list):
                    for project in category_projects:
                        if isinstance(project, dict) and 'repository' in project:
                            projects.append({
                                'name': project.get('name', ''),
                                'url': project.get('repository', ''),
                                'category': category,
                                'description': project.get('description', ''),
                                'homepage': project.get('homepage', ''),
                                'license': project.get('license', ''),
                                'languages': project.get('languages', [])
                            })
            
            logger.info(f"Loaded {len(projects)} projects from {yaml_path}")
            return projects
            
        except Exception as e:
            logger.error(f"Error loading projects from {yaml_path}: {e}")
            return []
    
    def extract_single_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract dependencies for a single project."""
        url = project_data.get('url', '')
        
        try:
            # Get repository information
            repo_info = self.github_client.get_repository_info(url)
            if not repo_info:
                return {'url': url, 'status': 'failed', 'error': 'Could not fetch repository info'}
            
            # Merge project data with repo info
            merged_data = {**project_data, **repo_info}
            
            # Insert/update project in database
            project_id = db.insert_project(merged_data)
            
            # Find dependency files
            dependency_files = self.github_client.find_dependency_files(url)
            
            if not dependency_files:
                return {
                    'url': url, 
                    'status': 'no_dependencies', 
                    'project_id': project_id,
                    'message': 'No dependency files found'
                }
            
            # Parse dependencies from each file
            all_dependencies = []
            
            for dep_file in dependency_files:
                # Store dependency file
                file_id = db.insert_dependency_file(
                    project_id=project_id,
                    file_path=dep_file['path'],
                    file_type=dep_file['type'],
                    content=dep_file['content']
                )
                
                # Parse dependencies
                dependencies = self.parser_factory.parse_dependencies(
                    content=dep_file['content'],
                    file_type=dep_file['type'],
                    file_path=dep_file['path']
                )
                
                # Add project_id to each dependency
                for dep in dependencies:
                    dep['project_id'] = project_id
                
                all_dependencies.extend(dependencies)
            
            # Store dependencies in database
            if all_dependencies:
                db.insert_dependencies(all_dependencies)
            
            return {
                'url': url,
                'status': 'success',
                'project_id': project_id,
                'dependency_files': len(dependency_files),
                'dependencies': len(all_dependencies)
            }
            
        except Exception as e:
            logger.error(f"Error extracting dependencies for {url}: {e}")
            return {'url': url, 'status': 'error', 'error': str(e)}
    
    def extract_batch(self, projects: List[Dict[str, Any]], 
                     max_workers: int = MAX_WORKERS) -> List[Dict[str, Any]]:
        """Extract dependencies for a batch of projects using parallel processing."""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_project = {
                executor.submit(self.extract_single_project, project): project 
                for project in projects
            }
            
            # Process completed tasks with progress bar
            with tqdm(total=len(projects), desc="Extracting dependencies") as pbar:
                for future in as_completed(future_to_project):
                    result = future.result()
                    results.append(result)
                    pbar.update(1)
                    
                    # Log progress
                    if result['status'] == 'success':
                        logger.info(f"✓ {result['url']}: {result.get('dependencies', 0)} dependencies")
                    elif result['status'] == 'no_dependencies':
                        logger.info(f"- {result['url']}: No dependency files found")
                    else:
                        logger.warning(f"✗ {result['url']}: {result.get('error', 'Unknown error')}")
        
        return results
    
    def extract_all_projects(self, resume: bool = True) -> Dict[str, Any]:
        """Extract dependencies for all projects in the YAML file."""
        # Load projects from YAML
        all_projects = self.load_projects_from_yaml()
        
        if not all_projects:
            logger.error("No projects loaded from YAML file")
            return {'status': 'error', 'message': 'No projects to process'}
        
        # Filter projects if resuming
        if resume:
            processed_urls = {p['url'] for p in db.get_projects_without_dependencies()}
            projects_to_process = [p for p in all_projects if p['url'] not in processed_urls]
            logger.info(f"Resuming: {len(projects_to_process)} projects remaining")
        else:
            projects_to_process = all_projects
            logger.info(f"Processing all {len(projects_to_process)} projects")
        
        if not projects_to_process:
            logger.info("All projects have been processed")
            return {'status': 'complete', 'message': 'All projects already processed'}
        
        # Process in batches
        total_results = []
        total_projects = len(projects_to_process)
        
        for i in range(0, total_projects, BATCH_SIZE):
            batch = projects_to_process[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (total_projects + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} projects)")
            
            # Check rate limit before processing batch
            try:
                rate_limit = self.github_client.check_rate_limit()
                remaining = rate_limit['core']['remaining']
                
                if remaining < len(batch) * 10:  # Conservative estimate
                    logger.warning(f"Low rate limit remaining: {remaining}. Consider waiting.")
                    time.sleep(60)  # Wait 1 minute
            except Exception as e:
                logger.warning(f"Could not check rate limit: {e}. Continuing with extraction...")
            
            batch_results = self.extract_batch(batch)
            total_results.extend(batch_results)
            
            # Summary for this batch
            success_count = sum(1 for r in batch_results if r['status'] == 'success')
            logger.info(f"Batch {batch_num} complete: {success_count}/{len(batch)} successful")
        
        # Final summary
        success_count = sum(1 for r in total_results if r['status'] == 'success')
        no_deps_count = sum(1 for r in total_results if r['status'] == 'no_dependencies')
        error_count = sum(1 for r in total_results if r['status'] in ['failed', 'error'])
        
        summary = {
            'status': 'complete',
            'total_projects': len(total_results),
            'successful': success_count,
            'no_dependencies': no_deps_count,
            'errors': error_count,
            'results': total_results
        }
        
        logger.info(f"Extraction complete: {success_count} successful, "
                   f"{no_deps_count} no dependencies, {error_count} errors")
        
        return summary
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about the extraction process."""
        return db.get_dependency_stats()


def main():
    """Main function for running the extraction."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    extractor = DependencyExtractor()
    
    # Run extraction
    results = extractor.extract_all_projects(resume=True)
    
    # Print final statistics
    stats = extractor.get_extraction_stats()
    print("\n" + "="*50)
    print("EXTRACTION SUMMARY")
    print("="*50)
    print(f"Total projects in database: {stats['total_projects']}")
    print(f"Projects with dependencies: {stats['projects_with_dependencies']}")
    print(f"\nTop 10 most used dependencies:")
    for dep, count in stats['top_dependencies'][:10]:
        print(f"  {dep}: {count} projects")
    
    print(f"\nDependencies by ecosystem:")
    for ecosystem, count in stats['ecosystem_distribution']:
        print(f"  {ecosystem}: {count} dependencies")


if __name__ == "__main__":
    main()
