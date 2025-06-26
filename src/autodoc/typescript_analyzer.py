"""
TypeScript analysis functionality for extracting code entities from TypeScript files.
Uses tree-sitter for fast and accurate parsing.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console

from .analyzer import CodeEntity

console = Console()

# Optional tree-sitter import
try:
    from tree_sitter_languages import get_language, get_parser
    
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class TypeScriptEntity(CodeEntity):
    """Extended CodeEntity for TypeScript-specific properties."""
    
    # TypeScript-specific properties
    is_async: bool = False
    is_exported: bool = False
    is_default_export: bool = False
    return_type: Optional[str] = None
    parameters: List[Dict] = None
    generic_params: Optional[str] = None
    access_modifier: Optional[str] = None  # public, private, protected
    is_static: bool = False
    is_abstract: bool = False
    implements_interfaces: List[str] = None
    extends_class: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.implements_interfaces is None:
            self.implements_interfaces = []


class TypeScriptAnalyzer:
    """Analyzes TypeScript files using tree-sitter to extract code entities."""
    
    def __init__(self):
        self.parser = None
        self.language = None
        self._initialize_parser()
        
        # TypeScript framework patterns
        self.framework_patterns = {
            'express': ['express', 'app.get', 'app.post', 'app.put', 'app.delete', 'Router()'],
            'nestjs': ['@Controller', '@Get', '@Post', '@Put', '@Delete', '@Injectable', 'NestFactory'],
            'fastify': ['fastify', 'server.get', 'server.post'],
            'koa': ['koa', 'ctx.body', 'ctx.request'],
            'next': ['Next', 'getServerSideProps', 'getStaticProps', 'NextApiRequest'],
            'angular': ['@Component', '@Injectable', '@NgModule', 'Angular'],
            'react': ['React', 'useState', 'useEffect', 'Component'],
            'vue': ['Vue', 'defineComponent', 'setup()', '@vue/composition-api']
        }
        
        # External service patterns for classification
        self.external_service_patterns = {
            'aws': ['aws-sdk', '@aws-sdk', 'AWS.', 'amazon'],
            'google': ['googleapis', '@google-cloud', 'gcp'],
            'stripe': ['stripe', '@stripe/stripe-js'],
            'github': ['@octokit', 'github-api'],
            'auth0': ['auth0', '@auth0'],
            'firebase': ['firebase', '@firebase'],
            'mongodb': ['mongodb', 'mongoose'],
            'postgres': ['pg', 'postgres', 'prisma'],
            'redis': ['redis', 'ioredis'],
            'elasticsearch': ['@elastic/elasticsearch'],
            'docker': ['dockerode', 'docker'],
            'kubernetes': ['@kubernetes/client-node']
        }
    
    def _initialize_parser(self):
        """Initialize tree-sitter parser for TypeScript."""
        if not TREE_SITTER_AVAILABLE:
            console.print("[yellow]Warning: tree-sitter-languages not available. Using fallback parser.[/yellow]")
            self._use_fallback_parser()
            return
        
        try:
            self.language = get_language('typescript')
            self.parser = get_parser('typescript')
            console.print("[green]TypeScript parser initialized successfully[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: TypeScript tree-sitter parser failed ({e}). Using fallback parser.[/yellow]")
            self._use_fallback_parser()
    
    def _use_fallback_parser(self):
        """Use regex-based fallback parser when tree-sitter is not available."""
        self.parser = "fallback"
        self.language = "typescript"
    
    def is_available(self) -> bool:
        """Check if TypeScript parsing is available."""
        return self.parser is not None and self.language is not None
    
    def analyze_file(self, file_path: Path) -> List[TypeScriptEntity]:
        """Analyze a single TypeScript file and extract code entities."""
        if not self.is_available():
            console.print(f"[red]TypeScript parsing not available for {file_path}[/red]")
            return []
        
        entities = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if self.parser == "fallback":
                # Use regex-based fallback parser
                imports = self._extract_imports_fallback(content)
                entities.extend(self._analyze_content_fallback(content, str(file_path), imports))
            else:
                # Parse the file with tree-sitter
                tree = self.parser.parse(bytes(content, 'utf8'))
                root_node = tree.root_node
                
                # Extract imports for framework detection
                imports = self._extract_imports(root_node, content)
                
                # Analyze all nodes in the tree
                entities.extend(self._analyze_node(root_node, content, str(file_path), imports))
            
        except Exception as e:
            console.print(f"[red]Error analyzing TypeScript file {file_path}: {e}[/red]")
        
        return entities
    
    def analyze_directory(self, path: Path) -> List[TypeScriptEntity]:
        """Analyze all TypeScript files in a directory."""
        if not self.is_available():
            console.print("[red]TypeScript parsing not available[/red]")
            return []
        
        console.print(f"[blue]Analyzing TypeScript files in {path}...[/blue]")
        
        # Find TypeScript files
        ts_files = list(path.rglob("*.ts")) + list(path.rglob("*.tsx"))
        ts_files = [
            f for f in ts_files
            if not any(skip in f.parts for skip in [
                'node_modules', '.git', 'dist', 'build', 'coverage', 
                '.next', '.nuxt', '.output', '__pycache__'
            ])
        ]
        
        console.print(f"Found {len(ts_files)} TypeScript files")
        
        all_entities = []
        for file_path in ts_files:
            entities = self.analyze_file(file_path)
            all_entities.extend(entities)
        
        console.print(f"Found {len(all_entities)} TypeScript entities")
        return all_entities
    
    def _analyze_node(self, node, content: str, file_path: str, imports: List[str]) -> List[TypeScriptEntity]:
        """Recursively analyze a tree-sitter node and extract entities."""
        entities = []
        
        node_type = node.type
        
        if node_type == 'function_declaration':
            entity = self._analyze_function(node, content, file_path, imports)
            if entity:
                entities.append(entity)
        
        elif node_type == 'method_definition':
            entity = self._analyze_method(node, content, file_path, imports)
            if entity:
                entities.append(entity)
        
        elif node_type == 'class_declaration':
            entity = self._analyze_class(node, content, file_path, imports)
            if entity:
                entities.append(entity)
        
        elif node_type == 'interface_declaration':
            entity = self._analyze_interface(node, content, file_path, imports)
            if entity:
                entities.append(entity)
        
        elif node_type == 'type_alias_declaration':
            entity = self._analyze_type_alias(node, content, file_path, imports)
            if entity:
                entities.append(entity)
        
        elif node_type == 'variable_declaration':
            # Check if it's a function assignment (arrow function, etc.)
            entity = self._analyze_variable_function(node, content, file_path, imports)
            if entity:
                entities.append(entity)
        
        # Recursively analyze child nodes
        for child in node.children:
            entities.extend(self._analyze_node(child, content, file_path, imports))
        
        return entities
    
    def _analyze_function(self, node, content: str, file_path: str, imports: List[str]) -> Optional[TypeScriptEntity]:
        """Analyze a function declaration node."""
        # Extract function name
        name_node = None
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = self._get_node_text(name_node, content)
        
        # Create entity
        entity = TypeScriptEntity(
            type='function',
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            docstring=self._extract_jsdoc_comment(node, content),
            code=self._get_node_text(node, content)[:200] + "..." if len(self._get_node_text(node, content)) > 200 else self._get_node_text(node, content),
            is_async=self._is_async_function(node, content),
            is_exported=self._is_exported(node),
            parameters=self._extract_function_parameters(node, content),
            return_type=self._extract_return_type(node, content),
            generic_params=self._extract_generic_parameters(node, content)
        )
        
        # Detect framework and API patterns
        self._enhance_with_api_detection(entity, imports, content)
        
        return entity
    
    def _analyze_method(self, node, content: str, file_path: str, imports: List[str]) -> Optional[TypeScriptEntity]:
        """Analyze a method definition node."""
        # Extract method name
        name_node = None
        for child in node.children:
            if child.type == 'property_identifier':
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = self._get_node_text(name_node, content)
        
        entity = TypeScriptEntity(
            type='method',
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            docstring=self._extract_jsdoc_comment(node, content),
            code=self._get_node_text(node, content)[:200] + "..." if len(self._get_node_text(node, content)) > 200 else self._get_node_text(node, content),
            is_async=self._is_async_function(node, content),
            parameters=self._extract_function_parameters(node, content),
            return_type=self._extract_return_type(node, content),
            access_modifier=self._extract_access_modifier(node, content),
            is_static=self._is_static_method(node, content)
        )
        
        self._enhance_with_api_detection(entity, imports, content)
        
        return entity
    
    def _analyze_class(self, node, content: str, file_path: str, imports: List[str]) -> Optional[TypeScriptEntity]:
        """Analyze a class declaration node."""
        # Extract class name
        name_node = None
        for child in node.children:
            if child.type == 'type_identifier':
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = self._get_node_text(name_node, content)
        
        entity = TypeScriptEntity(
            type='class',
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            docstring=self._extract_jsdoc_comment(node, content),
            code=f"class {name}",
            is_exported=self._is_exported(node),
            extends_class=self._extract_extends_class(node, content),
            implements_interfaces=self._extract_implements_interfaces(node, content),
            is_abstract=self._is_abstract_class(node, content),
            generic_params=self._extract_generic_parameters(node, content)
        )
        
        self._enhance_with_api_detection(entity, imports, content)
        
        return entity
    
    def _analyze_interface(self, node, content: str, file_path: str, imports: List[str]) -> Optional[TypeScriptEntity]:
        """Analyze an interface declaration node."""
        name_node = None
        for child in node.children:
            if child.type == 'type_identifier':
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = self._get_node_text(name_node, content)
        
        entity = TypeScriptEntity(
            type='interface',
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            docstring=self._extract_jsdoc_comment(node, content),
            code=f"interface {name}",
            is_exported=self._is_exported(node),
            extends_class=self._extract_extends_interface(node, content),
            generic_params=self._extract_generic_parameters(node, content)
        )
        
        self._enhance_with_api_detection(entity, imports, content)
        
        return entity
    
    def _analyze_type_alias(self, node, content: str, file_path: str, imports: List[str]) -> Optional[TypeScriptEntity]:
        """Analyze a type alias declaration."""
        name_node = None
        for child in node.children:
            if child.type == 'type_identifier':
                name_node = child
                break
        
        if not name_node:
            return None
        
        name = self._get_node_text(name_node, content)
        
        entity = TypeScriptEntity(
            type='type',
            name=name,
            file_path=file_path,
            line_number=node.start_point[0] + 1,
            docstring=self._extract_jsdoc_comment(node, content),
            code=self._get_node_text(node, content)[:100] + "..." if len(self._get_node_text(node, content)) > 100 else self._get_node_text(node, content),
            is_exported=self._is_exported(node),
            generic_params=self._extract_generic_parameters(node, content)
        )
        
        return entity
    
    def _analyze_variable_function(self, node, content: str, file_path: str, imports: List[str]) -> Optional[TypeScriptEntity]:
        """Analyze variable declarations that might be function assignments."""
        # Look for arrow functions or function expressions
        for child in node.children:
            if child.type == 'variable_declarator':
                for grandchild in child.children:
                    if grandchild.type in ['arrow_function', 'function_expression']:
                        # Extract variable name
                        name_node = None
                        for gc in child.children:
                            if gc.type == 'identifier':
                                name_node = gc
                                break
                        
                        if name_node:
                            name = self._get_node_text(name_node, content)
                            
                            entity = TypeScriptEntity(
                                type='function',
                                name=name,
                                file_path=file_path,
                                line_number=node.start_point[0] + 1,
                                docstring=self._extract_jsdoc_comment(node, content),
                                code=self._get_node_text(child, content)[:200] + "..." if len(self._get_node_text(child, content)) > 200 else self._get_node_text(child, content),
                                is_async=self._is_async_function(grandchild, content),
                                is_exported=self._is_exported(node),
                                parameters=self._extract_function_parameters(grandchild, content),
                                return_type=self._extract_return_type(grandchild, content)
                            )
                            
                            self._enhance_with_api_detection(entity, imports, content)
                            
                            return entity
        
        return None
    
    def _extract_imports(self, root_node, content: str) -> List[str]:
        """Extract import statements from the file."""
        imports = []
        
        def traverse_for_imports(node):
            if node.type == 'import_statement':
                imports.append(self._get_node_text(node, content))
            for child in node.children:
                traverse_for_imports(child)
        
        traverse_for_imports(root_node)
        return imports
    
    def _enhance_with_api_detection(self, entity: TypeScriptEntity, imports: List[str], content: str):
        """Enhance entity with API framework detection and classification."""
        import_text = ' '.join(imports).lower()
        
        # Detect framework
        for framework, patterns in self.framework_patterns.items():
            if any(pattern.lower() in import_text or pattern.lower() in entity.code.lower() for pattern in patterns):
                entity.framework = framework
                break
        
        # Detect HTTP methods and routes from decorators or method calls
        if entity.framework in ['express', 'fastify', 'koa']:
            entity.http_methods = self._extract_http_methods_from_code(entity.code)
            entity.route_path = self._extract_route_path_from_code(entity.code)
            
        elif entity.framework == 'nestjs':
            entity.decorators = self._extract_nestjs_decorators(entity.code)
            entity.http_methods = self._extract_nestjs_http_methods(entity.decorators)
            entity.route_path = self._extract_nestjs_route_path(entity.decorators)
        
        # Classify as API endpoint
        if entity.http_methods or entity.route_path or any(dec.startswith('@') for dec in (entity.decorators or [])):
            entity.endpoint_type = 'rest_api'
        
        # Detect external service calls
        entity.external_calls = self._find_external_calls_in_code(entity.code, imports)
        
        # Classify internal vs external
        entity.is_internal = self._classify_internal_vs_external(entity, imports)
        
        if not entity.is_internal and entity.external_calls:
            entity.external_domain = self._extract_external_domain_from_calls(entity.external_calls)
    
    def _get_node_text(self, node, content: str) -> str:
        """Extract text content from a tree-sitter node."""
        return content[node.start_byte:node.end_byte]
    
    def _extract_jsdoc_comment(self, node, content: str) -> Optional[str]:
        """Extract JSDoc comment preceding a node."""
        # Look for comment nodes before this node
        start_line = node.start_point[0]
        lines = content.split('\n')
        
        comment_lines = []
        for i in range(start_line - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('*') or line.startswith('/**') or line.startswith('*/'):
                comment_lines.insert(0, line)
            elif line.startswith('//'):
                comment_lines.insert(0, line)
            elif not line:  # Empty line
                continue
            else:
                break
        
        if comment_lines:
            # Clean up JSDoc formatting
            comment = '\n'.join(comment_lines)
            comment = re.sub(r'/\*\*|\*/|^\s*\*\s?', '', comment, flags=re.MULTILINE)
            return comment.strip() if comment.strip() else None
        
        return None
    
    def _is_async_function(self, node, content: str) -> bool:
        """Check if a function is async."""
        node_text = self._get_node_text(node, content)
        return 'async ' in node_text
    
    def _is_exported(self, node) -> bool:
        """Check if a declaration is exported."""
        # Check if parent node is an export statement
        parent = node.parent
        while parent:
            if parent.type in ['export_statement', 'export_declaration']:
                return True
            parent = parent.parent
        return False
    
    def _extract_function_parameters(self, node, content: str) -> List[Dict]:
        """Extract function parameters with types."""
        parameters = []
        
        for child in node.children:
            if child.type == 'formal_parameters':
                for param_child in child.children:
                    if param_child.type == 'parameter' or param_child.type == 'required_parameter':
                        param_info = self._parse_parameter(param_child, content)
                        if param_info:
                            parameters.append(param_info)
        
        return parameters
    
    def _parse_parameter(self, param_node, content: str) -> Optional[Dict]:
        """Parse a single parameter node."""
        param_text = self._get_node_text(param_node, content)
        
        # Basic parameter parsing (can be enhanced)
        if ':' in param_text:
            name_part, type_part = param_text.split(':', 1)
            return {
                'name': name_part.strip(),
                'type': type_part.strip(),
                'optional': '?' in name_part
            }
        else:
            return {
                'name': param_text.strip(),
                'type': 'any',
                'optional': False
            }
    
    def _extract_return_type(self, node, content: str) -> Optional[str]:
        """Extract return type annotation."""
        node_text = self._get_node_text(node, content)
        
        # Look for return type annotation
        match = re.search(r':\s*([^{]+?)\s*[{=]', node_text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_generic_parameters(self, node, content: str) -> Optional[str]:
        """Extract generic type parameters."""
        node_text = self._get_node_text(node, content)
        
        # Look for generic parameters
        match = re.search(r'<([^>]+)>', node_text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_access_modifier(self, node, content: str) -> Optional[str]:
        """Extract access modifier (public, private, protected)."""
        node_text = self._get_node_text(node, content)
        
        for modifier in ['private', 'protected', 'public']:
            if modifier in node_text:
                return modifier
        
        return None
    
    def _is_static_method(self, node, content: str) -> bool:
        """Check if method is static."""
        node_text = self._get_node_text(node, content)
        return 'static ' in node_text
    
    def _extract_extends_class(self, node, content: str) -> Optional[str]:
        """Extract extended class name."""
        for child in node.children:
            if child.type == 'class_heritage':
                heritage_text = self._get_node_text(child, content)
                match = re.search(r'extends\s+(\w+)', heritage_text)
                if match:
                    return match.group(1)
        return None
    
    def _extract_implements_interfaces(self, node, content: str) -> List[str]:
        """Extract implemented interface names."""
        interfaces = []
        for child in node.children:
            if child.type == 'class_heritage':
                heritage_text = self._get_node_text(child, content)
                # Look for implements clause
                if 'implements' in heritage_text:
                    implements_part = heritage_text.split('implements')[1]
                    interface_names = [name.strip() for name in implements_part.split(',')]
                    interfaces.extend(interface_names)
        return interfaces
    
    def _extract_extends_interface(self, node, content: str) -> Optional[str]:
        """Extract extended interface name."""
        for child in node.children:
            if child.type == 'extends_clause':
                extends_text = self._get_node_text(child, content)
                match = re.search(r'extends\s+(\w+)', extends_text)
                if match:
                    return match.group(1)
        return None
    
    def _is_abstract_class(self, node, content: str) -> bool:
        """Check if class is abstract."""
        node_text = self._get_node_text(node, content)
        return 'abstract ' in node_text
    
    def _extract_http_methods_from_code(self, code: str) -> List[str]:
        """Extract HTTP methods from Express/Fastify style code."""
        methods = []
        code_lower = code.lower()
        
        method_patterns = {
            'GET': [r'\.get\s*\(', r'app\.get', r'router\.get'],
            'POST': [r'\.post\s*\(', r'app\.post', r'router\.post'],
            'PUT': [r'\.put\s*\(', r'app\.put', r'router\.put'],
            'DELETE': [r'\.delete\s*\(', r'app\.delete', r'router\.delete'],
            'PATCH': [r'\.patch\s*\(', r'app\.patch', r'router\.patch']
        }
        
        for method, patterns in method_patterns.items():
            if any(re.search(pattern, code_lower) for pattern in patterns):
                methods.append(method)
        
        return methods
    
    def _extract_route_path_from_code(self, code: str) -> Optional[str]:
        """Extract route path from Express/Fastify style code."""
        # Look for route patterns like app.get('/api/users', ...)
        match = re.search(r'\.(get|post|put|delete|patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]', code)
        if match:
            return match.group(2)
        
        return None
    
    def _extract_nestjs_decorators(self, code: str) -> List[str]:
        """Extract NestJS decorators."""
        decorators = []
        
        # Find all decorator patterns
        decorator_matches = re.findall(r'@(\w+)(?:\([^)]*\))?', code)
        decorators.extend([f'@{match}' for match in decorator_matches])
        
        return decorators
    
    def _extract_nestjs_http_methods(self, decorators: List[str]) -> List[str]:
        """Extract HTTP methods from NestJS decorators."""
        methods = []
        
        method_mapping = {
            '@Get': 'GET',
            '@Post': 'POST', 
            '@Put': 'PUT',
            '@Delete': 'DELETE',
            '@Patch': 'PATCH'
        }
        
        for decorator in decorators:
            for nest_decorator, http_method in method_mapping.items():
                if decorator.startswith(nest_decorator):
                    methods.append(http_method)
        
        return methods
    
    def _extract_nestjs_route_path(self, decorators: List[str]) -> Optional[str]:
        """Extract route path from NestJS decorators."""
        for decorator in decorators:
            # Look for route paths in decorators like @Get('/users')
            match = re.search(r'@(Get|Post|Put|Delete|Patch)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]\s*\)', decorator)
            if match:
                return match.group(2)
        
        return None
    
    def _find_external_calls_in_code(self, code: str, imports: List[str]) -> List[str]:
        """Find external API calls in the code."""
        external_calls = []
        
        # Common external call patterns
        call_patterns = [
            r'fetch\s*\(',
            r'axios\.',
            r'http\.',
            r'request\.',
            r'client\.',
            r'api\.',
            r'\.get\s*\(',
            r'\.post\s*\(',
            r'\.put\s*\(',
            r'\.delete\s*\('
        ]
        
        for pattern in call_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                external_calls.append(pattern)
        
        return external_calls
    
    def _classify_internal_vs_external(self, entity: TypeScriptEntity, imports: List[str]) -> bool:
        """Classify if entity represents internal or external functionality."""
        # Check if it has external calls
        if entity.external_calls:
            return False
        
        # Check if it's a wrapper around external services
        name_lower = entity.name.lower()
        if any(service in name_lower for service in ['client', 'adapter']) and any(ext in name_lower for ext in ['external', 'third_party', 'api']):
            return False
        
        # Check file path for external integration patterns
        file_path_lower = entity.file_path.lower()
        if any(pattern in file_path_lower for pattern in [
            'clients', 'adapters', 'external', 'integrations', 'services/external'
        ]):
            return False
        
        # Check imports for external service SDKs
        import_text = ' '.join(imports).lower()
        for service_name, patterns in self.external_service_patterns.items():
            if any(pattern in import_text for pattern in patterns):
                if service_name in name_lower or service_name in entity.code.lower():
                    return False
        
        return True  # Default to internal
    
    def _extract_external_domain_from_calls(self, external_calls: List[str]) -> Optional[str]:
        """Extract domain from external API calls."""
        # This would need more sophisticated analysis of the actual code
        # For now, return None - could be enhanced to parse URL literals
        return None
    
    # Fallback parser methods (regex-based)
    def _extract_imports_fallback(self, content: str) -> List[str]:
        """Extract import statements using regex."""
        import_pattern = r'import\s+.*?from\s+[\'"][^\'"]+[\'"]'
        imports = re.findall(import_pattern, content, re.MULTILINE)
        return imports
    
    def _analyze_content_fallback(self, content: str, file_path: str, imports: List[str]) -> List[TypeScriptEntity]:
        """Analyze TypeScript content using regex patterns."""
        entities = []
        lines = content.split('\n')
        
        # Function patterns
        function_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)'
        class_pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)'
        interface_pattern = r'(?:export\s+)?interface\s+(\w+)'
        type_pattern = r'(?:export\s+)?type\s+(\w+)'
        method_pattern = r'(\w+)\s*\([^)]*\)\s*:\s*\w+\s*{'
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//') or line.startswith('*') or line.startswith('/*'):
                continue
            
            # Extract functions
            func_match = re.search(function_pattern, line)
            if func_match:
                entity = TypeScriptEntity(
                    type='function',
                    name=func_match.group(1),
                    file_path=file_path,
                    line_number=line_num,
                    docstring=None,
                    code=line[:100] + "..." if len(line) > 100 else line,
                    is_async='async' in line,
                    is_exported='export' in line
                )
                self._enhance_with_api_detection(entity, imports, content)
                entities.append(entity)
            
            # Extract classes
            class_match = re.search(class_pattern, line)
            if class_match:
                entity = TypeScriptEntity(
                    type='class',
                    name=class_match.group(1),
                    file_path=file_path,
                    line_number=line_num,
                    docstring=None,
                    code=f"class {class_match.group(1)}",
                    is_exported='export' in line,
                    is_abstract='abstract' in line
                )
                self._enhance_with_api_detection(entity, imports, content)
                entities.append(entity)
            
            # Extract interfaces
            interface_match = re.search(interface_pattern, line)
            if interface_match:
                entity = TypeScriptEntity(
                    type='interface',
                    name=interface_match.group(1),
                    file_path=file_path,
                    line_number=line_num,
                    docstring=None,
                    code=f"interface {interface_match.group(1)}",
                    is_exported='export' in line
                )
                self._enhance_with_api_detection(entity, imports, content)
                entities.append(entity)
            
            # Extract type aliases
            type_match = re.search(type_pattern, line)
            if type_match:
                entity = TypeScriptEntity(
                    type='type',
                    name=type_match.group(1),
                    file_path=file_path,
                    line_number=line_num,
                    docstring=None,
                    code=line[:100] + "..." if len(line) > 100 else line,
                    is_exported='export' in line
                )
                entities.append(entity)
            
            # Extract methods (simple pattern)
            method_match = re.search(method_pattern, line)
            if method_match and not func_match:  # Avoid duplicating functions
                entity = TypeScriptEntity(
                    type='method',
                    name=method_match.group(1),
                    file_path=file_path,
                    line_number=line_num,
                    docstring=None,
                    code=line[:100] + "..." if len(line) > 100 else line,
                    is_async='async' in line,
                    access_modifier=self._extract_access_modifier_fallback(line),
                    is_static='static' in line
                )
                self._enhance_with_api_detection(entity, imports, content)
                entities.append(entity)
        
        return entities
    
    def _extract_access_modifier_fallback(self, line: str) -> Optional[str]:
        """Extract access modifier from line using regex."""
        for modifier in ['private', 'protected', 'public']:
            if modifier in line:
                return modifier
        return None