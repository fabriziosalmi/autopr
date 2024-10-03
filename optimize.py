import os
import argparse
import yaml
import subprocess
import sys
from pathlib import Path
from typing import List

def load_config(config_path: str) -> dict:
    """Load and parse the configuration YAML file."""
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def clone_repository(repo_url: str, branch: str, auth_token: str, repo_name: str):
    """Clone the repository from GitHub."""
    clone_url = repo_url.replace("https://", f"https://{auth_token}@")
    target_path = Path(f"./cloned_repos/{repo_name}")
    subprocess.run(['git', 'clone', '-b', branch, clone_url, str(target_path)], check=True)
    return target_path

def install_requirements(requirements_path: Path):
    """Install Python dependencies using pip."""
    if requirements_path.exists():
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_path)], check=True)

def optimize_python_files(target_dir: Path, excluded_files: List[str], max_iterations: int, ignore_failure: bool):
    """Perform optimization on Python files."""
    python_files = list(target_dir.rglob("*.py"))
    
    for file_path in python_files:
        if any(file_path.match(pattern) for pattern in excluded_files):
            print(f"Skipping excluded file: {file_path}")
            continue
        
        for iteration in range(max_iterations):
            try:
                # Here you could integrate an optimization tool (like black, autopep8, etc.)
                subprocess.run(['black', str(file_path)], check=True)
                subprocess.run(['flake8', str(file_path)], check=True)
                print(f"Optimized {file_path} (iteration {iteration + 1})")
                break
            except subprocess.CalledProcessError as e:
                print(f"Optimization failed for {file_path} (iteration {iteration + 1}): {e}")
                if not ignore_failure:
                    raise

def commit_and_create_pr(target_dir: Path, repo_name: str, branch_name: str, auth_token: str):
    """Commit changes and create a pull request."""
    os.chdir(target_dir)
    
    # Create a new branch
    new_branch = f"optimize/{branch_name}"
    subprocess.run(['git', 'checkout', '-b', new_branch], check=True)
    
    # Stage changes and commit
    subprocess.run(['git', 'add', '.'], check=True)
    commit_message = f"Optimized code for repository '{repo_name}' - detailed improvements included"
    subprocess.run(['git', 'commit', '-m', commit_message], check=True)
    
    # Push changes to remote
    repo_url = f"https://{auth_token}@github.com/{repo_name}.git"
    subprocess.run(['git', 'push', '-u', 'origin', new_branch], check=True)
    
    # Create a pull request using GitHub CLI
    pr_title = "Automated Code Optimization"
    pr_body = "This PR contains automated optimizations for the Python code, improving formatting, style, and ensuring compliance with best practices."
    subprocess.run(['gh', 'pr', 'create', '--title', pr_title, '--body', pr_body, '--base', branch_name], check=True)

def main():
    parser = argparse.ArgumentParser(description="Optimize Python files in a repository.")
    parser.add_argument('--config', required=True, help='Path to the configuration YAML file.')
    parser.add_argument('--repo-token', required=False, help='Repository authentication token.')

    args = parser.parse_args()
    auth_token = args.repo_token or os.getenv('DEFAULT_AUTH_TOKEN')

    if not auth_token:
        raise ValueError("Authentication token is required.")

    config = load_config(args.config)

    for repo in config.get("repositories", []):
        try:
            print(f"Processing repository: {repo['name']}")
            repo_url = repo['url']
            branch = repo['branch']
            paths_to_optimize = repo.get('paths_to_optimize', [])
            excluded_files = repo.get('excluded_files', [])
            max_iterations = repo['optimization'].get('max_iterations', config['default_settings']['max_iterations'])
            ignore_failure = repo['optimization'].get('ignore_failure', config['default_settings']['ignore_failure'])

            # Clone repository
            target_path = clone_repository(repo_url, branch, auth_token, repo['name'])

            # Install requirements if any
            for path in paths_to_optimize:
                requirements_path = target_path / path / "requirements.txt"
                install_requirements(requirements_path)

            # Optimize Python files
            for path in paths_to_optimize:
                optimize_python_files(target_path / path, excluded_files, max_iterations, ignore_failure)

            # Commit changes and create PR
            commit_and_create_pr(target_path, repo['name'], branch, auth_token)

        except Exception as e:
            print(f"Failed to process repository '{repo['name']}': {e}")
            if not ignore_failure:
                break

if __name__ == "__main__":
    main()
