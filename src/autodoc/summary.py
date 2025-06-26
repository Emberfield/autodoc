"""
Code analysis and summary generation functionality.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .analyzer import CodeEntity


class CodeAnalyzer:
    """Analyzes code entities to extract detailed information and generate summaries."""

    def __init__(self, entities: List[CodeEntity]):
        self.entities = entities

    def extract_purpose(self, entity: CodeEntity) -> str:
        """Extract purpose from function name and docstring."""
        name_lower = entity.name.lower()
        if "test_" in name_lower:
            return "Test function"
        elif "get_" in name_lower or "fetch_" in name_lower:
            return "Retrieves data"
        elif "set_" in name_lower or "update_" in name_lower:
            return "Updates data"
        elif "create_" in name_lower or "make_" in name_lower:
            return "Creates new objects"
        elif "delete_" in name_lower or "remove_" in name_lower:
            return "Removes data"
        elif "is_" in name_lower or "has_" in name_lower:
            return "Checks condition"
        elif entity.docstring:
            return entity.docstring.split("\n")[0]
        else:
            return "General purpose function"

    def extract_signature(self, entity: CodeEntity) -> str:
        """Extract function/method signature."""
        try:
            with open(entity.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            if entity.line_number <= len(lines):
                line = lines[entity.line_number - 1].strip()
                if line.startswith("def ") or line.startswith("async def "):
                    return line
        except Exception:
            pass
        return f"def {entity.name}(...):"

    def extract_decorators(self, entity: CodeEntity) -> List[str]:
        """Extract decorators for functions/methods."""
        try:
            with open(entity.file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            decorators = []
            start_line = max(0, entity.line_number - 5)
            for i in range(start_line, min(entity.line_number, len(lines))):
                line = lines[i].strip()
                if line.startswith("@"):
                    decorators.append(line)

            return decorators
        except Exception:
            return []

    def extract_parameters(self, entity: CodeEntity) -> List[Dict[str, str]]:
        """Extract function parameters."""
        signature = self.extract_signature(entity)
        params = []

        # Extract parameters from signature (basic regex)
        match = re.search(r"\((.*?)\):", signature)
        if match:
            param_str = match.group(1)
            if param_str.strip():
                for param in param_str.split(","):
                    param = param.strip()
                    if param and param != "self" and param != "cls":
                        params.append(
                            {"name": param.split("=")[0].strip(), "default": "=" in param}
                        )

        return params

    def extract_return_type(self, entity: CodeEntity) -> Optional[str]:
        """Extract return type annotation."""
        signature = self.extract_signature(entity)
        match = re.search(r"->\s*([^:]+):", signature)
        return match.group(1).strip() if match else None

    def is_async_function(self, entity: CodeEntity) -> bool:
        """Check if function is async."""
        signature = self.extract_signature(entity)
        return signature.strip().startswith("async def")

    def is_generator(self, entity: CodeEntity) -> bool:
        """Check if function is a generator (simplified)."""
        # Would need AST analysis to detect yield statements
        return False

    def extract_base_classes(self, entity: CodeEntity) -> List[str]:
        """Extract base classes."""
        try:
            with open(entity.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ClassDef)
                    and node.name == entity.name
                    and node.lineno == entity.line_number
                ):
                    return [ast.unparse(base) for base in node.bases]
        except Exception:
            pass
        return []

    def is_static_method(self, entity: CodeEntity) -> bool:
        """Check if method is static."""
        decorators = self.extract_decorators(entity)
        return any("@staticmethod" in dec for dec in decorators)

    def is_class_method(self, entity: CodeEntity) -> bool:
        """Check if method is a class method."""
        decorators = self.extract_decorators(entity)
        return any("@classmethod" in dec for dec in decorators)

    def is_property(self, entity: CodeEntity) -> bool:
        """Check if method is a property."""
        decorators = self.extract_decorators(entity)
        return any("@property" in dec for dec in decorators)

    def is_abstract_class(self, entity: CodeEntity) -> bool:
        """Check if class is abstract."""
        decorators = self.extract_decorators(entity)
        return any("ABC" in dec or "abstractmethod" in dec for dec in decorators)

    def estimate_complexity(self, entity: CodeEntity) -> int:
        """Estimate code complexity based on entity name and context."""
        complexity = 1
        name = entity.name.lower()

        # Add complexity for certain patterns
        if any(pattern in name for pattern in ["_complex", "_handler", "_processor", "_manager"]):
            complexity += 2
        if entity.docstring and len(entity.docstring.split()) > 20:
            complexity += 1
        if any(pattern in name for pattern in ["create", "update", "delete", "process"]):
            complexity += 1

        return complexity

    def get_class_methods_detailed(
        self, class_entity: CodeEntity, file_path: str
    ) -> List[CodeEntity]:
        """Get detailed methods belonging to a class."""
        methods = []
        class_line = class_entity.line_number

        for entity in self.entities:
            if (
                entity.type == "function"
                and entity.file_path == file_path
                and entity.line_number > class_line
            ):
                methods.append(entity)
                if len(methods) > 20:  # Limit to prevent excessive data
                    break

        return methods

    def extract_imports(self, file_path: str) -> List[str]:
        """Extract imports from a file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"from {module} import {alias.name}")

            return imports
        except Exception:
            return []

    def extract_module_docstring(self, file_path: str) -> Optional[str]:
        """Extract module-level docstring."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            if (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            ):
                return tree.body[0].value.value
        except Exception:
            pass
        return None

    def path_to_module(self, file_path: str) -> str:
        """Convert file path to module name."""
        path = Path(file_path)
        parts = path.with_suffix("").parts

        skip = {"src", ".", ".."}
        module_parts = [p for p in parts if p not in skip]

        return ".".join(module_parts) if module_parts else path.stem

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive codebase statistics."""
        stats = {
            "function_count": len([e for e in self.entities if e.type == "function"]),
            "class_count": len([e for e in self.entities if e.type == "class"]),
            "total_entities": len(self.entities),
            "files_analyzed": len(set(e.file_path for e in self.entities)),
            "avg_functions_per_file": 0,
            "avg_classes_per_file": 0,
            "private_functions": len(
                [e for e in self.entities if e.type == "function" and e.name.startswith("_")]
            ),
            "public_functions": len(
                [e for e in self.entities if e.type == "function" and not e.name.startswith("_")]
            ),
            "test_functions": len(
                [e for e in self.entities if e.type == "function" and "test_" in e.name.lower()]
            ),
            "documented_entities": len([e for e in self.entities if e.docstring]),
            "documentation_coverage": 0,
        }

        if stats["files_analyzed"] > 0:
            stats["avg_functions_per_file"] = stats["function_count"] / stats["files_analyzed"]
            stats["avg_classes_per_file"] = stats["class_count"] / stats["files_analyzed"]

        if stats["total_entities"] > 0:
            stats["documentation_coverage"] = stats["documented_entities"] / stats["total_entities"]

        return stats

    def build_enhanced_feature_map(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build enhanced feature map with detailed locations."""
        feature_map = {
            "authentication": [],
            "database": [],
            "api_endpoints": [],
            "data_processing": [],
            "file_operations": [],
            "testing": [],
            "configuration": [],
            "utilities": [],
            "cli_commands": [],
            "async_operations": [],
        }

        for entity in self.entities:
            name_lower = entity.name.lower()
            file_lower = entity.file_path.lower()

            entity_info = {
                "name": entity.name,
                "type": entity.type,
                "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                "module": self.path_to_module(entity.file_path),
                "purpose": self.extract_purpose(entity),
            }

            if any(auth in name_lower for auth in ["auth", "login", "token", "permission"]):
                feature_map["authentication"].append(entity_info)

            if any(db in name_lower for db in ["db", "database", "query", "model", "orm"]):
                feature_map["database"].append(entity_info)

            if any(api in name_lower for api in ["api", "endpoint", "route", "view"]):
                feature_map["api_endpoints"].append(entity_info)

            if any(proc in name_lower for proc in ["process", "transform", "parse", "analyze"]):
                feature_map["data_processing"].append(entity_info)

            if any(file_op in name_lower for file_op in ["read", "write", "save", "load", "file"]):
                feature_map["file_operations"].append(entity_info)

            if "test" in file_lower or "test_" in name_lower:
                feature_map["testing"].append(entity_info)

            if any(conf in file_lower for conf in ["config", "settings", "env"]):
                feature_map["configuration"].append(entity_info)

            if any(util in file_lower for util in ["util", "helper", "common"]):
                feature_map["utilities"].append(entity_info)

            if "cli" in file_lower or any(cli in name_lower for cli in ["command", "click"]):
                feature_map["cli_commands"].append(entity_info)

            if self.is_async_function(entity):
                feature_map["async_operations"].append(entity_info)

        return {k: v for k, v in feature_map.items() if v}

    def identify_key_functions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify the most important functions."""
        key_functions = []

        for entity in self.entities:
            if (
                entity.type == "function"
                and entity.docstring
                and not entity.name.startswith("test_")
                and not entity.name.startswith("_")
            ):

                key_functions.append(
                    {
                        "name": entity.name,
                        "module": self.path_to_module(entity.file_path),
                        "purpose": entity.docstring.split("\n")[0],
                        "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                    }
                )

        return key_functions[:limit]

    def identify_entry_points(self) -> List[Dict[str, Any]]:
        """Identify entry points in the codebase."""
        entry_points = []

        for entity in self.entities:
            if entity.type == "function":
                # Main functions
                if entity.name == "main":
                    entry_points.append(
                        {
                            "type": "main_function",
                            "name": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "module": self.path_to_module(entity.file_path),
                        }
                    )

                # CLI commands
                decorators = self.extract_decorators(entity)
                if any("@click.command" in dec or "@cli.command" in dec for dec in decorators):
                    entry_points.append(
                        {
                            "type": "cli_command",
                            "name": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "module": self.path_to_module(entity.file_path),
                        }
                    )

        return entry_points

    def analyze_data_flows(self) -> List[Dict[str, Any]]:
        """Analyze data flows in the codebase."""
        flows = []

        # Identify common patterns
        for entity in self.entities:
            if entity.type == "function":
                name = entity.name.lower()
                if "load" in name or "read" in name:
                    flows.append(
                        {
                            "type": "data_input",
                            "function": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "purpose": "Loads/reads data",
                        }
                    )
                elif "save" in name or "write" in name:
                    flows.append(
                        {
                            "type": "data_output",
                            "function": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "purpose": "Saves/writes data",
                        }
                    )
                elif "process" in name or "transform" in name:
                    flows.append(
                        {
                            "type": "data_processing",
                            "function": entity.name,
                            "location": f"{Path(entity.file_path).name}:{entity.line_number}",
                            "purpose": "Processes/transforms data",
                        }
                    )

        return flows

    def identify_architecture_patterns(self) -> List[Dict[str, Any]]:
        """Identify architectural patterns in the codebase."""
        patterns = []

        # Check for common patterns
        class_names = [e.name for e in self.entities if e.type == "class"]
        function_names = [e.name for e in self.entities if e.type == "function"]

        # Singleton pattern
        if any("singleton" in name.lower() for name in class_names):
            patterns.append({"pattern": "Singleton", "confidence": "high"})

        # Factory pattern
        if any("factory" in name.lower() for name in class_names + function_names):
            patterns.append({"pattern": "Factory", "confidence": "medium"})

        # Observer pattern
        if any("observer" in name.lower() or "listener" in name.lower() for name in class_names):
            patterns.append({"pattern": "Observer", "confidence": "medium"})

        # Command pattern
        if any("command" in name.lower() for name in class_names):
            patterns.append({"pattern": "Command", "confidence": "medium"})

        return patterns

    def infer_detailed_module_purpose(self, file_path: str, content: Dict[str, Any]) -> str:
        """Infer detailed module purpose."""
        filename = Path(file_path).stem.lower()

        if filename == "__init__":
            return "Package initialization and exports"
        elif filename == "__main__":
            return "Application entry point"
        elif "test" in filename:
            return f"Test module with {len(content['functions'])} test functions"
        elif "config" in filename or "settings" in filename:
            return "Configuration and settings management"
        elif "model" in filename:
            return f"Data models and schemas ({len(content['classes'])} classes)"
        elif "util" in filename or "helper" in filename:
            return f"Utility functions and helpers ({len(content['functions'])} functions)"
        elif "cli" in filename:
            return f"Command-line interface with {len(content['functions'])} commands"
        elif "api" in filename:
            return f"API endpoints and handlers ({len(content['functions'])} endpoints)"
        elif content["classes"]:
            return f"Module defining {len(content['classes'])} classes and {len(content['functions'])} functions"
        elif content["functions"]:
            return f"Function module with {len(content['functions'])} functions"
        else:
            return "General purpose module"


class MarkdownFormatter:
    """Formats code analysis results as detailed Markdown documentation."""

    def format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format comprehensive summary as detailed Markdown optimized for LLM context."""
        md = []

        # Header with metadata
        md.append("# Comprehensive Codebase Documentation")
        md.append(
            f"*Generated on {summary['overview']['analysis_date']} with {summary['overview']['tool_version']}*\n"
        )

        # Executive Summary
        overview = summary["overview"]
        md.append("## Executive Summary")
        md.append(
            f"This codebase contains {overview['total_functions']} functions and {overview['total_classes']} classes across {overview['total_files']} files, written primarily in {overview['main_language']}."
        )
        md.append(f"Total lines analyzed: {overview['total_lines_analyzed']:,}")
        md.append(f"Testing coverage: {'Comprehensive' if overview['has_tests'] else 'Limited'}")

        # Add build system summary
        if summary.get("build_system") and summary["build_system"].get("build_tools"):
            md.append(f"Build system: {', '.join(summary['build_system']['build_tools'])}")

        if summary.get("ci_configuration") and summary["ci_configuration"].get("has_ci"):
            platforms = summary["ci_configuration"].get("platforms", [])
            md.append(f"CI/CD: {', '.join(platforms) if platforms else 'Configured'}")
        else:
            md.append("CI/CD: Not configured")

        # Statistics and Quality Metrics
        if "statistics" in summary:
            stats = summary["statistics"]
            md.append("\n## Codebase Statistics")
            md.append(f"- **Total Entities**: {stats['total_entities']}")
            md.append(f"- **Public Functions**: {stats['public_functions']}")
            md.append(f"- **Private Functions**: {stats['private_functions']}")
            md.append(f"- **Test Functions**: {stats['test_functions']}")
            md.append(f"- **Documentation Coverage**: {stats['documentation_coverage']:.1%}")
            md.append(f"- **Average Functions per File**: {stats['avg_functions_per_file']:.1f}")
            md.append(f"- **Average Classes per File**: {stats['avg_classes_per_file']:.1f}")

        if "code_quality_metrics" in summary:
            quality = summary["code_quality_metrics"]
            md.append("\n### Code Quality Metrics")
            md.append(f"- **Documentation Coverage**: {quality['documentation_coverage']:.1%}")
            md.append(f"- **Average Complexity**: {quality['average_complexity']:.1f}")
            md.append(f"- **Public API Ratio**: {quality['public_api_ratio']:.1%}")

        # Build System and Tooling
        if summary.get("build_system"):
            build = summary["build_system"]
            md.append("\n## Build System and Tooling")

            if build.get("build_tools"):
                md.append(f"**Build Tools**: {', '.join(build['build_tools'])}")

            if build.get("package_managers"):
                md.append(f"**Package Managers**: {', '.join(build['package_managers'])}")

            if build.get("configuration_files"):
                md.append("\n**Configuration Files**:")
                for config in build["configuration_files"]:
                    md.append(f"- `{config['file']}` - {config['description']}")

            if build.get("build_commands"):
                md.append("\n**Build Commands**:")
                for cmd in build["build_commands"]:
                    if isinstance(cmd, dict):
                        # New detailed format
                        if cmd.get("description"):
                            md.append(f"- `{cmd['command']}` - {cmd['description']}")
                        else:
                            md.append(f"- `{cmd['command']}` ({cmd.get('category', 'general')})")
                    else:
                        # Legacy string format
                        md.append(f"- `{cmd}`")
                        
            # Add Makefile targets if available
            if build.get("makefile_categories"):
                md.append("\n**Makefile Targets by Category**:")
                for category, targets in build["makefile_categories"].items():
                    if targets:
                        md.append(f"\n*{category.title()}:*")
                        for target in targets:
                            if target.get("description"):
                                md.append(f"- `{target['command']}` - {target['description']}")
                            else:
                                md.append(f"- `{target['command']}`")

            if build.get("scripts"):
                md.append("\n**Project Scripts**:")
                for script, command in build["scripts"].items():
                    md.append(f"- `{script}`: {command}")

        # Testing System
        if summary.get("test_system"):
            test = summary["test_system"]
            md.append("\n## Testing System")
            md.append(f"**Test Files**: {test.get('test_files_count', 0)} files")
            md.append(f"**Test Functions**: {test.get('test_functions_count', 0)} functions")

            if test.get("test_frameworks"):
                md.append(f"**Testing Frameworks**: {', '.join(test['test_frameworks'])}")

            if test.get("test_runners"):
                md.append(f"**Test Runners**: {', '.join(test['test_runners'])}")

            if test.get("coverage_tools"):
                md.append(f"**Coverage Tools**: {', '.join(test['coverage_tools'])}")

            if test.get("test_commands"):
                md.append("\n**Test Commands**:")
                for cmd in test["test_commands"]:
                    md.append(f"- `{cmd}`")

            if test.get("test_directories"):
                md.append("\n**Test Directories**:")
                for test_dir in test["test_directories"]:
                    md.append(f"- `{test_dir}`")

        # CI/CD Configuration
        if summary.get("ci_configuration"):
            ci = summary["ci_configuration"]
            md.append("\n## CI/CD Configuration")

            if ci.get("has_ci"):
                md.append(f"**CI Platforms**: {', '.join(ci.get('platforms', []))}")

                if ci.get("workflows"):
                    md.append("\n**Workflows**:")
                    for workflow in ci["workflows"]:
                        md.append(f"- **{workflow['name']}**")
                        if workflow.get("triggers"):
                            md.append(f"  - Triggers: {', '.join(workflow['triggers'])}")
                        if workflow.get("jobs"):
                            md.append(f"  - Jobs: {', '.join(workflow['jobs'])}")

                if ci.get("configuration_files"):
                    md.append("\n**CI Configuration Files**:")
                    for config in ci["configuration_files"]:
                        md.append(f"- `{config['file']}` ({config['platform']})")
            else:
                md.append("**CI/CD**: No CI configuration detected")

        # Deployment Configuration
        if summary.get("deployment_info"):
            deploy = summary["deployment_info"]
            md.append("\n## Deployment and Distribution")

            if deploy.get("containerization"):
                md.append(f"**Containerization**: {', '.join(deploy['containerization'])}")

            if deploy.get("deployment_platforms"):
                md.append(f"**Deployment Platforms**: {', '.join(deploy['deployment_platforms'])}")

            if deploy.get("package_distribution"):
                md.append(f"**Package Distribution**: {', '.join(deploy['package_distribution'])}")

            if deploy.get("configuration_files"):
                md.append("\n**Deployment Configuration Files**:")
                for config in deploy["configuration_files"]:
                    md.append(f"- `{config['file']}` ({config['platform']}) - {config['type']}")

        # Add remaining sections (project structure, feature map, etc.)
        self._add_remaining_sections(md, summary)

        # Footer
        md.append("\n---")
        md.append("*This documentation was automatically generated by Autodoc.*")
        md.append(
            "*For the most up-to-date information, regenerate this document after code changes.*"
        )

        return "\n".join(md)

    def _add_remaining_sections(self, md: List[str], summary: Dict[str, Any]) -> None:
        """Add remaining sections like project structure, feature map, etc."""
        # Project Structure
        if "project_structure" in summary:
            structure = summary["project_structure"]
            md.append("\n## Project Structure")
            md.append("### Directory Organization")
            for dir_name, info in sorted(structure["directories"].items()):
                md.append(
                    f"- **`{dir_name}`**: {info['file_count']} files, {info['functions']} functions, {info['classes']} classes"
                )

            md.append("\n### File Types")
            for ext, count in sorted(structure["file_types"].items()):
                md.append(f"- **`{ext}`**: {count} files")

        # Entry Points
        if summary.get("entry_points"):
            md.append("\n## Entry Points")
            md.append("Key entry points for understanding code execution flow:")
            for entry in summary["entry_points"]:
                md.append(
                    f"- **{entry['type'].replace('_', ' ').title()}**: `{entry['name']}` in {entry['location']}"
                )

        # Feature Map - Where to Find Key Functionality
        if summary.get("feature_map"):
            md.append("\n## Feature Map - Where to Find Key Functionality")
            md.append("This section helps you quickly locate code related to specific features:\n")

            for feature, items in summary["feature_map"].items():
                if items:
                    md.append(f"### {feature.replace('_', ' ').title()}")
                    for item in items[:8]:  # Show more items for better context
                        md.append(f"- **`{item['name']}`** ({item['type']}) - {item['purpose']}")
                        md.append(f"  - Location: `{item['location']}`")
                        md.append(f"  - Module: `{item['module']}`")
                    if len(items) > 8:
                        md.append(f"- *...and {len(items) - 8} more related items*")
                    md.append("")

        # Data Flows
        if summary.get("data_flows"):
            md.append("\n## Data Flow Analysis")
            md.append("Understanding how data moves through the system:")

            flow_types = {}
            for flow in summary["data_flows"]:
                flow_type = flow["type"]
                if flow_type not in flow_types:
                    flow_types[flow_type] = []
                flow_types[flow_type].append(flow)

            for flow_type, flows in flow_types.items():
                md.append(f"\n### {flow_type.replace('_', ' ').title()}")
                for flow in flows[:5]:
                    md.append(
                        f"- **`{flow['function']}`** at `{flow['location']}` - {flow['purpose']}"
                    )
