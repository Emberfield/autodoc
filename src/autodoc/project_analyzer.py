"""
Project configuration analysis for build systems, testing, and CI/CD.
"""

from pathlib import Path
from typing import Any, Dict, List

from .analyzer import CodeEntity


class ProjectAnalyzer:
    """Analyzes project configuration, build systems, testing, and CI/CD setup."""

    def __init__(self, entities: List[CodeEntity]):
        self.entities = entities

    def analyze_build_system(self) -> Dict[str, Any]:
        """Analyze build system configuration and tools."""
        build_info = {
            "build_tools": [],
            "package_managers": [],
            "configuration_files": [],
            "build_commands": [],
            "dependencies": {},
            "scripts": {},
        }

        cwd = Path.cwd()

        # Check for common Python build files
        build_files = {
            "pyproject.toml": "Modern Python packaging (PEP 518)",
            "setup.py": "Traditional Python setup",
            "setup.cfg": "Setup configuration",
            "requirements.txt": "Pip requirements",
            "requirements-dev.txt": "Development requirements",
            "Pipfile": "Pipenv configuration",
            "poetry.lock": "Poetry lock file",
            "hatch.toml": "Hatch configuration",
            "tox.ini": "Tox testing configuration",
            "Makefile": "Make build system",
            "noxfile.py": "Nox testing configuration",
        }

        for filename, description in build_files.items():
            file_path = cwd / filename
            if file_path.exists():
                build_info["configuration_files"].append(
                    {"file": filename, "description": description, "size": file_path.stat().st_size}
                )

        # Detect build tools and package managers
        if (cwd / "pyproject.toml").exists():
            build_info["build_tools"].append("setuptools/build")
            build_info["package_managers"].append("pip")

            # Parse pyproject.toml for more details
            try:
                try:
                    import tomllib
                except ImportError:
                    tomllib = None
                if tomllib:
                    with open(cwd / "pyproject.toml", "rb") as f:
                        pyproject = tomllib.load(f)

                    if "tool" in pyproject:
                        if "hatch" in pyproject["tool"]:
                            build_info["build_tools"].append("hatch")
                        if "poetry" in pyproject["tool"]:
                            build_info["build_tools"].append("poetry")
                            build_info["package_managers"].append("poetry")
                        if "flit" in pyproject["tool"]:
                            build_info["build_tools"].append("flit")
                        if "setuptools" in pyproject["tool"]:
                            build_info["build_tools"].append("setuptools")

                    # Extract scripts and commands
                    if "project" in pyproject and "scripts" in pyproject["project"]:
                        build_info["scripts"] = pyproject["project"]["scripts"]

                    # Extract dependencies
                    if "project" in pyproject and "dependencies" in pyproject["project"]:
                        build_info["dependencies"]["runtime"] = pyproject["project"]["dependencies"]

            except Exception:
                pass

        if (cwd / "setup.py").exists():
            build_info["build_tools"].append("setuptools")
            build_info["package_managers"].append("pip")

        if (cwd / "Pipfile").exists():
            build_info["package_managers"].append("pipenv")

        if (cwd / "poetry.lock").exists():
            build_info["build_tools"].append("poetry")
            build_info["package_managers"].append("poetry")

        # Check for common build commands in scripts or documentation
        common_commands = [
            "python -m build",
            "pip install -e .",
            "hatch build",
            "poetry build",
            "make build",
            "python setup.py build",
            "python setup.py sdist bdist_wheel",
        ]

        # Look for commands in common files
        command_files = ["Makefile", "README.md", "README.rst", "DEVELOPMENT.md", "CONTRIBUTING.md"]
        for cmd_file in command_files:
            if (cwd / cmd_file).exists():
                try:
                    with open(cwd / cmd_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        for cmd in common_commands:
                            if cmd.lower() in content:
                                build_info["build_commands"].append(cmd)
                except Exception:
                    pass

        return build_info

    def analyze_test_system(self) -> Dict[str, Any]:
        """Analyze testing configuration and framework."""
        test_info = {
            "test_frameworks": [],
            "test_runners": [],
            "configuration_files": [],
            "test_commands": [],
            "test_directories": [],
            "coverage_tools": [],
            "test_files_count": 0,
            "test_functions_count": 0,
        }

        cwd = Path.cwd()

        # Count test files and functions from already analyzed entities
        test_files = set()
        for entity in self.entities:
            file_path = Path(entity.file_path)
            if (
                "test" in file_path.name.lower()
                or "test" in str(file_path.parent).lower()
                or entity.name.startswith("test_")
            ):
                test_files.add(entity.file_path)
                if entity.name.startswith("test_"):
                    test_info["test_functions_count"] += 1

        test_info["test_files_count"] = len(test_files)

        # Find test directories
        for test_file in test_files:
            test_dir = str(Path(test_file).parent)
            if test_dir not in test_info["test_directories"]:
                test_info["test_directories"].append(test_dir)

        # Check for testing configuration files
        test_config_files = {
            "pytest.ini": "pytest configuration",
            "pyproject.toml": "pytest/testing configuration",
            "tox.ini": "tox multi-environment testing",
            "noxfile.py": "nox testing sessions",
            ".coveragerc": "coverage.py configuration",
            "coverage.ini": "coverage configuration",
            "conftest.py": "pytest fixtures and configuration",
        }

        for filename, description in test_config_files.items():
            file_path = cwd / filename
            if file_path.exists():
                test_info["configuration_files"].append(
                    {"file": filename, "description": description}
                )

        # Check imports and code for framework usage
        for entity in self.entities:
            if entity.type == "function" and entity.name.startswith("test_"):
                # This suggests pytest or unittest
                if "pytest" not in test_info["test_frameworks"]:
                    test_info["test_frameworks"].append("pytest")  # Default assumption

        # Check for specific files that indicate frameworks
        if (cwd / "conftest.py").exists() or (cwd / "pytest.ini").exists():
            test_info["test_frameworks"].append("pytest")
            test_info["test_runners"].append("pytest")

        if (cwd / "tox.ini").exists():
            test_info["test_runners"].append("tox")

        if (cwd / "noxfile.py").exists():
            test_info["test_runners"].append("nox")

        # Check for coverage tools
        coverage_files = [".coveragerc", "coverage.ini"]
        for cov_file in coverage_files:
            if (cwd / cov_file).exists():
                test_info["coverage_tools"].append("coverage.py")
                break

        # Common test commands
        common_test_commands = [
            "pytest",
            "python -m pytest",
            "hatch run test",
            "poetry run pytest",
            "tox",
            "nox",
            "python -m unittest",
            "make test",
        ]

        # Look for test commands in documentation and scripts
        command_files = ["Makefile", "README.md", "README.rst", "pyproject.toml", "DEVELOPMENT.md"]
        for cmd_file in command_files:
            if (cwd / cmd_file).exists():
                try:
                    with open(cwd / cmd_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        for cmd in common_test_commands:
                            if cmd.lower() in content and cmd not in test_info["test_commands"]:
                                test_info["test_commands"].append(cmd)
                except Exception:
                    pass

        return test_info

    def analyze_ci_configuration(self) -> Dict[str, Any]:
        """Analyze CI/CD configuration."""
        ci_info = {
            "has_ci": False,
            "platforms": [],
            "workflows": [],
            "configuration_files": [],
            "triggers": [],
            "jobs": [],
            "environments": [],
        }

        cwd = Path.cwd()

        # GitHub Actions
        github_workflows_dir = cwd / ".github" / "workflows"
        if github_workflows_dir.exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("GitHub Actions")

            workflow_files = list(github_workflows_dir.glob("*.yml")) + list(
                github_workflows_dir.glob("*.yaml")
            )
            for workflow_file in workflow_files:
                ci_info["configuration_files"].append(
                    {
                        "file": str(workflow_file.relative_to(cwd)),
                        "platform": "GitHub Actions",
                        "name": workflow_file.stem,
                    }
                )

                # Try to parse workflow file for more details
                try:
                    import yaml

                    with open(workflow_file, "r", encoding="utf-8") as f:
                        workflow_data = yaml.safe_load(f)

                    if isinstance(workflow_data, dict):
                        # Extract workflow info
                        workflow_info = {
                            "name": workflow_data.get("name", workflow_file.stem),
                            "triggers": (
                                list(workflow_data.get("on", {}).keys())
                                if isinstance(workflow_data.get("on"), dict)
                                else [workflow_data.get("on", "unknown")]
                            ),
                            "jobs": list(workflow_data.get("jobs", {}).keys()),
                        }
                        ci_info["workflows"].append(workflow_info)

                        # Collect triggers
                        for trigger in workflow_info["triggers"]:
                            if trigger not in ci_info["triggers"]:
                                ci_info["triggers"].append(trigger)

                        # Collect jobs
                        for job in workflow_info["jobs"]:
                            if job not in ci_info["jobs"]:
                                ci_info["jobs"].append(job)

                except Exception:
                    # If YAML parsing fails, still record the file
                    ci_info["workflows"].append(
                        {"name": workflow_file.stem, "triggers": ["unknown"], "jobs": ["unknown"]}
                    )

        # GitLab CI
        gitlab_ci_file = cwd / ".gitlab-ci.yml"
        if gitlab_ci_file.exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("GitLab CI")
            ci_info["configuration_files"].append(
                {"file": ".gitlab-ci.yml", "platform": "GitLab CI"}
            )

        # Travis CI
        travis_files = [".travis.yml", ".travis.yaml"]
        for travis_file in travis_files:
            if (cwd / travis_file).exists():
                ci_info["has_ci"] = True
                ci_info["platforms"].append("Travis CI")
                ci_info["configuration_files"].append(
                    {"file": travis_file, "platform": "Travis CI"}
                )
                break

        # Circle CI
        circle_ci_dir = cwd / ".circleci"
        if circle_ci_dir.exists() and (circle_ci_dir / "config.yml").exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("Circle CI")
            ci_info["configuration_files"].append(
                {"file": ".circleci/config.yml", "platform": "Circle CI"}
            )

        # Azure Pipelines
        azure_files = ["azure-pipelines.yml", "azure-pipelines.yaml", ".azure-pipelines.yml"]
        for azure_file in azure_files:
            if (cwd / azure_file).exists():
                ci_info["has_ci"] = True
                ci_info["platforms"].append("Azure Pipelines")
                ci_info["configuration_files"].append(
                    {"file": azure_file, "platform": "Azure Pipelines"}
                )
                break

        # Jenkins
        jenkins_file = cwd / "Jenkinsfile"
        if jenkins_file.exists():
            ci_info["has_ci"] = True
            ci_info["platforms"].append("Jenkins")
            ci_info["configuration_files"].append({"file": "Jenkinsfile", "platform": "Jenkins"})

        return ci_info

    def analyze_deployment_configuration(self) -> Dict[str, Any]:
        """Analyze deployment and distribution configuration."""
        deploy_info = {
            "deployment_platforms": [],
            "containerization": [],
            "configuration_files": [],
            "package_distribution": [],
            "hosting_indicators": [],
        }

        cwd = Path.cwd()

        # Docker
        docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", ".dockerignore"]
        for docker_file in docker_files:
            if (cwd / docker_file).exists():
                if "Docker" not in deploy_info["containerization"]:
                    deploy_info["containerization"].append("Docker")
                deploy_info["configuration_files"].append(
                    {"file": docker_file, "type": "containerization", "platform": "Docker"}
                )

        # Kubernetes
        k8s_patterns = ["*.yaml", "*.yml"]
        for pattern in k8s_patterns:
            for yaml_file in cwd.glob(pattern):
                if yaml_file.name.startswith(("k8s", "kubernetes")) or "k8s" in str(
                    yaml_file.parent
                ):
                    if "Kubernetes" not in deploy_info["containerization"]:
                        deploy_info["containerization"].append("Kubernetes")
                    break

        # Heroku
        heroku_files = ["Procfile", "app.json", "runtime.txt"]
        for heroku_file in heroku_files:
            if (cwd / heroku_file).exists():
                if "Heroku" not in deploy_info["deployment_platforms"]:
                    deploy_info["deployment_platforms"].append("Heroku")
                deploy_info["configuration_files"].append(
                    {"file": heroku_file, "type": "deployment", "platform": "Heroku"}
                )

        # Vercel
        vercel_files = ["vercel.json", "now.json"]
        for vercel_file in vercel_files:
            if (cwd / vercel_file).exists():
                if "Vercel" not in deploy_info["deployment_platforms"]:
                    deploy_info["deployment_platforms"].append("Vercel")
                deploy_info["configuration_files"].append(
                    {"file": vercel_file, "type": "deployment", "platform": "Vercel"}
                )

        # Package distribution
        if (cwd / "pyproject.toml").exists() or (cwd / "setup.py").exists():
            deploy_info["package_distribution"].append("PyPI")

        # Look for publishing workflows in CI
        github_workflows_dir = cwd / ".github" / "workflows"
        if github_workflows_dir.exists():
            for workflow_file in github_workflows_dir.glob("*.yml"):
                try:
                    with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        if "pypi" in content or "twine" in content or "python -m build" in content:
                            if "PyPI" not in deploy_info["package_distribution"]:
                                deploy_info["package_distribution"].append("PyPI")
                        if "docker" in content and "push" in content:
                            if "Docker Registry" not in deploy_info["package_distribution"]:
                                deploy_info["package_distribution"].append("Docker Registry")
                except Exception:
                    pass

        return deploy_info
