import os
import argparse
import yaml
import subprocess
import sys
from pathlib import Path
from typing import List, Callable, Optional
import concurrent.futures
import logging
import shutil


# =========================== Setup Logging ===========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =========================== Helper Functions ===========================
def load_config(config_path: str) -> dict:
    """Load and parse the configuration YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config


def clone_repository(repo_url: str, branch: str, auth_token: str, repo_name: str) -> Path:
    """Clone the repository from GitHub."""
    logger.info(f"Cloning repository '{repo_name}'...")
    clone_url = repo_url.replace("https://", f"https://{auth_token}@")
    target_path = Path(f"./cloned_repos/{repo_name}")
    if target_path.exists():
        shutil.rmtree(target_path)  # Clean previous clone if exists

    try:
        subprocess.run(['git', 'clone', '-b', branch, clone_url, str(target_path)], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to clone repository '{repo_name}': {e}")
        raise
    return target_path


def install_requirements(requirements_path: Path) -> None:
    """Install Python dependencies using pip."""
    if requirements_path.exists():
        logger.info(f"Installing requirements from {requirements_path}...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_path)], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install requirements from '{requirements_path}': {e}")
            raise


def execute_custom_script(script_path: Path) -> None:
    """Execute a custom script, if it exists."""
    if script_path.exists():
        logger.info(f"Executing custom script: {script_path}")
        try:
            subprocess.run(['bash', str(script_path)], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute custom script '{script_path}': {e}")
            raise


# =========================== Optimization Functions ===========================
def optimize_python_files(
    target_dir: Path,
    excluded_files: List[str],
    max_iterations: int,
    ignore_failure: bool,
    run_tests_command: Optional[str] = "pytest"
) -> None:
    """Perform optimization on Python files using multiple optimization tools."""
    logger.info(f"Starting optimization in directory: {target_dir}")
    python_files = list(target_dir.rglob("*.py"))

    # Filter out excluded files
    files_to_optimize = [
        file_path for file_path in python_files
        if not any(file_path.match(pattern) for pattern in excluded_files)
    ]

    if not files_to_optimize:
        logger.info(f"No files to optimize in {target_dir}. Exiting optimization.")
        return

    # Define up to 20 optimization strategies
    optimization_strategies = [
        ("Black Formatting", lambda f: subprocess.run(['black', str(f)], check=True)),
        ("Flake8 Linting", lambda f: subprocess.run(['flake8', str(f)], check=True)),
        ("isort Import Sorting", lambda f: subprocess.run(['isort', str(f)], check=True)),
        ("Mypy Type Checking", lambda f: subprocess.run(['mypy', str(f)], check=True)),
        ("Pylint Checking", lambda f: subprocess.run(['pylint', str(f)], check=True)),
        ("Radon Complexity Check", lambda f: subprocess.run(['radon', 'cc', '-a', str(f)], check=True)),
        # Additional optimizers can be defined here
    ]

    def optimize_and_validate(file_path: Path, optimizers: List[Callable[[Path], None]]) -> None:
        """
        Optimize a single file with the provided list of optimizers and validate functionality.
        """
        logger.info(f"Starting optimization for {file_path}")
        original_content = file_path.read_text(encoding='utf-8')  # Save original state for rollback if needed
        successful_optimizations = 0

        for optimizer_name, optimizer in optimizers:
            validation_successful = False

            for iteration in range(max_iterations):
                try:
                    logger.info(f"Applying {optimizer_name} to {file_path} (Iteration {iteration + 1})...")
                    optimizer(file_path)

                    # Run tests to validate changes
                    logger.info(f"Running tests to validate changes after applying {optimizer_name} to {file_path}...")
                    subprocess.run(run_tests_command, shell=True, check=True)

                    validation_successful = True
                    successful_optimizations += 1
                    logger.info(f"Successfully optimized {file_path} with {optimizer_name} (Iteration {iteration + 1})")
                    break

                except subprocess.CalledProcessError as e:
                    logger.warning(f"Optimization or validation failed for {file_path} with {optimizer_name} (Iteration {iteration + 1}): {e}")
                    if iteration == max_iterations - 1 and not validation_successful:
                        logger.warning(f"Restoring original content of {file_path} due to repeated failures.")
                        file_path.write_text(original_content, encoding='utf-8')
                    if not ignore_failure:
                        logger.error(f"Stopping optimization due to failure in {file_path} with {optimizer_name}")
                        raise

        logger.info(f"Completed optimization for {file_path} with {successful_optimizations}/{len(optimizers)} optimizations successfully applied.")

    # Use thread-based parallelism to optimize multiple files concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_file = {executor.submit(optimize_and_validate, file_path, optimization_strategies): file_path for file_path in files_to_optimize}

        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Optimization process failed for {file_path}: {e}")
                if not ignore_failure:
                    logger.error("Terminating further optimization due to error.")
                    break

    logger.info("Optimization process completed for all files.")


# =========================== Git Commit and Pull Request ===========================
def commit_and_create_pr(target_dir: Path, repo_name: str, branch_name: str, auth_token: str) -> None:
    """Commit changes and create a pull request."""
    os.chdir(target_dir)

    new_branch = f"optimize/{branch_name}"
    logger.info(f"Creating new branch '{new_branch}' for optimization...")
    try:
        subprocess.run(['git', 'checkout', '-b', new_branch], check=True)

        # Stage changes and commit
        subprocess.run(['git', 'add', '.'], check=True)
        commit_message = f"Optimized code for repository '{repo_name}' - see details in commit."
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)

        # Push changes to remote
        repo_url = f"https://{auth_token}@github.com/{repo_name}.git"
        subprocess.run(['git', 'push', '-u', 'origin', new_branch], check=True)

        # Create a pull request using GitHub CLI
        pr_title = "Automated Code Optimization"
        pr_body = "This PR contains automated optimizations for the Python code, improving formatting and compliance with best practices."
        subprocess.run(['gh', 'pr', 'create', '--title', pr_title, '--body', pr_body, '--base', branch_name], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to commit or create PR: {e}")
        raise


# =========================== Main Process ===========================
def main() -> None:
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
            logger.info(f"Processing repository: {repo['name']}")
            repo_url = repo['url']
            branch = repo['branch']
            paths_to_optimize = repo.get('paths_to_optimize', config['default_settings'].get('paths_to_optimize', []))
            excluded_files = repo.get('excluded_files', config['default_settings'].get('excluded_files', []))
            max_iterations = repo['optimization'].get('max_iterations', config['default_settings']['optimization']['max_iterations'])
            ignore_failure = repo['optimization'].get('ignore_failure', config['default_settings']['optimization']['ignore_failure'])

            # Clone repository
            target_path = clone_repository(repo_url, branch, auth_token, repo['name'])

            # Execute pre-optimization script if exists
            pre_optimize_script = target_path / "scripts" / "pre_optimize.sh"
            execute_custom_script(pre_optimize_script)

            # Install requirements if any
            for path in paths_to_optimize:
                requirements_path = target_path / path / "requirements.txt"
                install_requirements(requirements_path)

            # Optimize Python files
            for path in paths_to_optimize:
                optimize_python_files(target_path / path, excluded_files, max_iterations, ignore_failure)

            # Execute post-optimization script if exists
            post_optimize_script = target_path / "scripts" / "post_optimize.sh"
            execute_custom_script(post_optimize_script)

            # Commit changes and create PR
            commit_and_create_pr(target_path, repo['name'], branch, auth_token)

        except Exception as e:
            logger.error(f"Failed to process repository '{repo['name']}': {e}")
            if not ignore_failure:
                break


if __name__ == "__main__":
    main()
