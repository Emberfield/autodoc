"""
AST analysis functionality for extracting code entities from Python files.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

console = Console()


@dataclass
class CodeEntity:
    type: str
    name: str
    file_path: str
    line_number: int
    docstring: Optional[str]
    code: str
    embedding: Optional[List[float]] = None

    # Enhanced properties for API detection
    decorators: List[str] = field(default_factory=list)
    http_methods: List[str] = field(default_factory=list)
    route_path: Optional[str] = None
    is_internal: bool = True
    framework: Optional[str] = None
    endpoint_type: Optional[str] = None
    auth_required: bool = False
    parameters: List[Dict] = field(default_factory=list)
    response_type: Optional[str] = None
    external_domain: Optional[str] = None
    external_calls: List[str] = field(default_factory=list)


class SimpleASTAnalyzer:
    """Analyzes Python files using AST to extract code entities."""

    def analyze_file(self, file_path: Path) -> List[CodeEntity]:
        """Analyze a single Python file and extract code entities."""
        entities = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                    entities.append(
                        CodeEntity(
                            type="function",
                            name=node.name,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            docstring=ast.get_docstring(node),
                            code=f"{prefix} {node.name}(...)",
                        )
                    )
                elif isinstance(node, ast.ClassDef):
                    entities.append(
                        CodeEntity(
                            type="class",
                            name=node.name,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            docstring=ast.get_docstring(node),
                            code=f"class {node.name}",
                        )
                    )
        except Exception as e:
            console.print(f"[red]Error analyzing {file_path}: {e}[/red]")
        return entities

    def analyze_directory(self, path: Path) -> List[CodeEntity]:
        """Analyze all Python files in a directory."""
        console.print(f"[blue]Analyzing {path}...[/blue]")

        python_files = list(path.rglob("*.py"))
        python_files = [
            f
            for f in python_files
            if not any(
                skip in f.parts for skip in ["__pycache__", "venv", ".venv", "build", "dist"]
            )
        ]

        console.print(f"Found {len(python_files)} Python files")

        all_entities = []
        for file_path in python_files:
            entities = self.analyze_file(file_path)
            all_entities.extend(entities)

        console.print(f"Found {len(all_entities)} code entities")
        return all_entities


class EnhancedASTAnalyzer(SimpleASTAnalyzer):
    """Extended analyzer with API endpoint detection and internal/external classification."""

    def __init__(self):
        super().__init__()
        self.project_root = None
        self.standard_library_modules = {
            "os",
            "sys",
            "json",
            "urllib",
            "http",
            "socket",
            "datetime",
            "time",
            "logging",
            "threading",
            "multiprocessing",
            "re",
            "collections",
            "itertools",
            "functools",
            "pathlib",
            "typing",
            "dataclasses",
            "asyncio",
            "concurrent",
            "unittest",
            "pytest",
        }

    def analyze_file(self, file_path: Path) -> List[CodeEntity]:
        """Enhanced analysis with API detection."""
        if self.project_root is None:
            self.project_root = self._find_project_root(file_path)

        entities = super().analyze_file(file_path)

        # Enhanced analysis for each entity
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=str(file_path))

            # Extract file-level imports
            file_imports = self._extract_file_imports(tree)

            # Enhance entities with additional analysis
            for entity in entities:
                self._enhance_entity_analysis(entity, tree, file_imports, content)

        except Exception as e:
            console.print(f"[red]Error in enhanced analysis of {file_path}: {e}[/red]")

        return entities

    def _find_project_root(self, file_path: Path) -> Path:
        """Find project root by looking for common markers."""
        current = file_path.parent if file_path.is_file() else file_path

        while current != current.parent:
            # Look for project indicators
            if any(
                (current / marker).exists()
                for marker in [
                    "pyproject.toml",
                    "setup.py",
                    "requirements.txt",
                    ".git",
                    "Pipfile",
                    "poetry.lock",
                    "Makefile",
                ]
            ):
                return current
            current = current.parent

        return file_path.parent  # Fallback

    def _extract_file_imports(self, tree: ast.AST) -> List[str]:
        """Extract all import statements from the AST."""
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

    def _enhance_entity_analysis(
        self, entity: CodeEntity, tree: ast.AST, file_imports: List[str], content: str
    ):
        """Enhance entity with detailed analysis."""
        # Find the corresponding AST node
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == entity.name
                and node.lineno == entity.line_number
            ):

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._analyze_function_node(entity, node, file_imports, content)
                elif isinstance(node, ast.ClassDef):
                    self._analyze_class_node(entity, node, file_imports, content)
                break

    def _analyze_function_node(
        self, entity: CodeEntity, node: ast.FunctionDef, file_imports: List[str], content: str
    ):
        """Analyze function node for API patterns."""
        # Extract decorators
        entity.decorators = self._extract_decorators(node)

        # Detect framework
        entity.framework = self._detect_framework(file_imports, entity.decorators)

        # Detect HTTP methods and routes
        entity.http_methods = self._detect_http_methods(entity.decorators, entity.name)
        entity.route_path = self._extract_route_path(entity.decorators)

        # Classify endpoint type
        entity.endpoint_type = self._classify_endpoint_type(entity)

        # Check authentication requirements
        entity.auth_required = self._detect_auth_requirement(entity.decorators)

        # Analyze external calls
        entity.external_calls = self._find_external_calls(node, file_imports)

        # Determine if internal or external
        entity.is_internal = self._classify_internal_vs_external(entity, file_imports)

        # Extract external domain if applicable
        if not entity.is_internal:
            entity.external_domain = self._extract_external_domain(entity.external_calls)

    def _analyze_class_node(
        self, entity: CodeEntity, node: ast.ClassDef, file_imports: List[str], content: str
    ):
        """Analyze class node for patterns."""
        entity.decorators = self._extract_decorators(node)
        entity.framework = self._detect_framework(file_imports, entity.decorators)
        entity.is_internal = self._classify_internal_vs_external(entity, file_imports)

    def _extract_decorators(self, node) -> List[str]:
        """Extract decorator strings from AST node."""
        decorators = []
        for decorator in node.decorator_list:
            try:
                if isinstance(decorator, ast.Name):
                    decorators.append(f"@{decorator.id}")
                elif isinstance(decorator, ast.Attribute):
                    decorators.append(f"@{ast.unparse(decorator)}")
                elif isinstance(decorator, ast.Call):
                    decorators.append(f"@{ast.unparse(decorator)}")
                else:
                    decorators.append(f"@{ast.unparse(decorator)}")
            except:
                decorators.append("@<decorator>")
        return decorators

    def _detect_framework(self, imports: List[str], decorators: List[str]) -> Optional[str]:
        """Detect web framework from imports and decorators."""
        import_text = " ".join(imports).lower()
        decorator_text = " ".join(decorators).lower()

        frameworks = {
            "flask": ["flask", "@app.route", "@bp.route"],
            "fastapi": ["fastapi", "@app.get", "@app.post", "@router."],
            "django": ["django", "rest_framework"],
            "tornado": ["tornado"],
            "aiohttp": ["aiohttp", "web."],
            "starlette": ["starlette"],
            "sanic": ["sanic"],
        }

        for framework, patterns in frameworks.items():
            if any(pattern in import_text or pattern in decorator_text for pattern in patterns):
                return framework
        return None

    def _detect_http_methods(self, decorators: List[str], function_name: str) -> List[str]:
        """Detect HTTP methods from decorators and function names."""
        methods = []
        decorator_text = " ".join(decorators).lower()

        # Method-specific decorators
        method_patterns = {
            "GET": ["@app.get", "@router.get", "methods=['get'", 'methods=["get"'],
            "POST": ["@app.post", "@router.post", "methods=['post'", 'methods=["post"'],
            "PUT": ["@app.put", "@router.put", "methods=['put'", 'methods=["put"'],
            "DELETE": ["@app.delete", "@router.delete", "methods=['delete'", 'methods=["delete"'],
            "PATCH": ["@app.patch", "@router.patch", "methods=['patch'", 'methods=["patch"'],
        }

        for method, patterns in method_patterns.items():
            if any(pattern in decorator_text for pattern in patterns):
                methods.append(method)

        # Infer from function name if no explicit method found
        if not methods:
            name_lower = function_name.lower()
            if any(prefix in name_lower for prefix in ["get_", "fetch_", "retrieve_"]):
                methods.append("GET")
            elif any(prefix in name_lower for prefix in ["post_", "create_", "add_"]):
                methods.append("POST")
            elif any(prefix in name_lower for prefix in ["put_", "update_", "modify_"]):
                methods.append("PUT")
            elif any(prefix in name_lower for prefix in ["delete_", "remove_"]):
                methods.append("DELETE")

        return methods

    def _extract_route_path(self, decorators: List[str]) -> Optional[str]:
        """Extract route path from decorators."""
        for decorator in decorators:
            # Match route patterns
            patterns = [
                r'@\w+\.route\(["\']([^"\']+)["\']',
                r'@\w+\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                r'route=["\']([^"\']+)["\']',
            ]

            for pattern in patterns:
                match = re.search(pattern, decorator)
                if match:
                    return match.group(-1)  # Last group contains the path
        return None

    def _classify_endpoint_type(self, entity: CodeEntity) -> Optional[str]:
        """Classify the type of endpoint."""
        if entity.http_methods or entity.route_path:
            return "rest_api"
        elif any("api" in dec.lower() for dec in entity.decorators):
            return "api"
        elif "api" in entity.file_path.lower() or "views" in entity.file_path.lower():
            return "handler"
        elif any(prefix in entity.name.lower() for prefix in ["handle_", "endpoint_"]):
            return "handler"
        return None

    def _detect_auth_requirement(self, decorators: List[str]) -> bool:
        """Check if authentication is required."""
        auth_patterns = [
            "login_required",
            "auth_required",
            "jwt_required",
            "require_auth",
            "authenticated",
            "permission_required",
            "oauth",
            "token_required",
        ]
        decorator_text = " ".join(decorators).lower()
        return any(pattern in decorator_text for pattern in auth_patterns)

    def _find_external_calls(self, node: ast.FunctionDef, file_imports: List[str]) -> List[str]:
        """Find external API calls within the function."""
        external_calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = None
                try:
                    call_str = ast.unparse(child)
                except:
                    continue

                # Look for HTTP client patterns
                if any(
                    pattern in call_str.lower()
                    for pattern in ["requests.", "httpx.", "aiohttp.", "urllib.", "http.client"]
                ):
                    external_calls.append(call_str)

                # Look for SDK calls
                elif any(
                    pattern in call_str.lower() for pattern in [".api.", "_client.", "client."]
                ):
                    external_calls.append(call_str)

        return external_calls

    def _classify_internal_vs_external(self, entity: CodeEntity, file_imports: List[str]) -> bool:
        """Classify if entity represents internal or external functionality."""
        # If it has external calls, it might be external
        if entity.external_calls:
            return False

        # Check if it's a wrapper around external services
        if any(
            keyword in entity.name.lower()
            for keyword in ["github", "stripe", "aws", "gcp", "azure", "api_client", "external"]
        ):
            return False

        # Check file path for external integration patterns
        file_path_lower = entity.file_path.lower()
        if any(
            pattern in file_path_lower
            for pattern in ["integrations", "external", "clients", "adapters", "third_party"]
        ):
            return False

        # Check imports for external service SDKs
        import_text = " ".join(file_imports).lower()
        external_services = [
            "github",
            "stripe",
            "boto3",
            "google.cloud",
            "azure",
            "requests",
            "httpx",
            "openai",
        ]

        if any(service in import_text for service in external_services):
            # Only mark as external if the entity name suggests it's a wrapper
            if any(service in entity.name.lower() for service in external_services):
                return False

        return True  # Default to internal

    def _extract_external_domain(self, external_calls: List[str]) -> Optional[str]:
        """Extract domain from external API calls."""
        domain_patterns = [
            r'https?://([^/\s"\']+)',
            r"api\.([a-zA-Z0-9.-]+)",
            r"client.*\.([a-zA-Z0-9.-]+)",
        ]

        for call in external_calls:
            for pattern in domain_patterns:
                match = re.search(pattern, call)
                if match:
                    domain = match.group(1)
                    if "." in domain and not domain.startswith("localhost"):
                        return domain
        return None
