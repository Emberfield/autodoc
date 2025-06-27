use anyhow::{Result, Context};
use rustpython_parser::{ast, Parse};
use std::path::Path;
use std::fs;

use crate::entity::CodeEntity;

/// Parser for Python source files using RustPython's parser
pub struct PythonParser;

impl PythonParser {
    pub fn new() -> Self {
        PythonParser
    }

    /// Parse a Python file and extract code entities
    pub fn parse_file(&self, file_path: &Path) -> Result<Vec<CodeEntity>> {
        let source = fs::read_to_string(file_path)
            .with_context(|| format!("Failed to read file: {:?}", file_path))?;
        
        self.parse_source(&source, file_path)
    }

    /// Parse Python source code and extract entities
    pub fn parse_source(&self, source: &str, file_path: &Path) -> Result<Vec<CodeEntity>> {
        let ast = ast::Suite::parse(source, "<embedded>")
            .map_err(|e| anyhow::anyhow!("Parse error: {:?}", e))?;
        
        let mut entities = Vec::new();
        let mut visitor = EntityVisitor::new(file_path);
        
        for stmt in ast {
            visitor.visit_stmt(&stmt, &mut entities);
        }
        
        Ok(entities)
    }
}

/// Visitor for extracting entities from AST
struct EntityVisitor<'a> {
    file_path: &'a Path,
    class_context: Vec<String>,
}

impl<'a> EntityVisitor<'a> {
    fn new(file_path: &'a Path) -> Self {
        EntityVisitor {
            file_path,
            class_context: Vec::new(),
        }
    }

    fn visit_stmt(&mut self, stmt: &ast::Stmt, entities: &mut Vec<CodeEntity>) {
        use ast::Stmt;
        
        match stmt {
            Stmt::FunctionDef(func) => self.visit_function(func, entities),
            Stmt::AsyncFunctionDef(func) => self.visit_async_function(func, entities),
            Stmt::ClassDef(class) => self.visit_class(class, entities),
            _ => {}
        }
    }

    fn visit_function(&mut self, func: &ast::StmtFunctionDef, entities: &mut Vec<CodeEntity>) {
        let mut entity = CodeEntity::new(
            if self.class_context.is_empty() { "function" } else { "method" }.to_string(),
            func.name.to_string(),
            self.file_path.to_path_buf(),
            1, // TODO: Calculate line number from TextSize
        );

        // Extract docstring
        entity.docstring = extract_docstring(&func.body);
        
        // Extract decorators
        entity.decorators = func.decorator_list.iter()
            .map(|d| expr_to_string(d))
            .collect();
        
        // Extract parameters
        entity.parameters = extract_parameters(&func.args);
        
        // Extract return type
        entity.return_type = func.returns.as_ref().map(|r| expr_to_string(r));
        
        // Set code (simplified - in real implementation would extract actual code)
        entity.code = format!("def {}(...): ...", func.name);
        
        // Detect API endpoints
        entity.detect_api_endpoint();
        
        // Calculate complexity
        entity.calculate_complexity();
        
        entities.push(entity);
    }

    fn visit_async_function(&mut self, func: &ast::StmtAsyncFunctionDef, entities: &mut Vec<CodeEntity>) {
        let mut entity = CodeEntity::new(
            if self.class_context.is_empty() { "function" } else { "method" }.to_string(),
            func.name.to_string(),
            self.file_path.to_path_buf(),
            1, // TODO: Calculate line number from TextSize
        );

        entity.is_async = true;
        entity.docstring = extract_docstring(&func.body);
        entity.decorators = func.decorator_list.iter()
            .map(|d| expr_to_string(d))
            .collect();
        entity.parameters = extract_parameters(&func.args);
        entity.return_type = func.returns.as_ref().map(|r| expr_to_string(r));
        entity.code = format!("async def {}(...): ...", func.name);
        entity.detect_api_endpoint();
        entity.calculate_complexity();
        
        entities.push(entity);
    }

    fn visit_class(&mut self, class: &ast::StmtClassDef, entities: &mut Vec<CodeEntity>) {
        let mut entity = CodeEntity::new(
            "class".to_string(),
            class.name.to_string(),
            self.file_path.to_path_buf(),
            1, // TODO: Calculate line number from TextSize
        );

        entity.docstring = extract_docstring(&class.body);
        entity.decorators = class.decorator_list.iter()
            .map(|d| expr_to_string(d))
            .collect();
        
        entities.push(entity);
        
        // Visit methods within the class
        self.class_context.push(class.name.to_string());
        for stmt in &class.body {
            self.visit_stmt(stmt, entities);
        }
        self.class_context.pop();
    }
}

/// Extract docstring from function/class body
fn extract_docstring(body: &[ast::Stmt]) -> Option<String> {
    use ast::{Stmt, Expr};
    
    if let Some(Stmt::Expr(expr_stmt)) = body.first() {
        if let Expr::Constant(constant) = &*expr_stmt.value {
            if let ast::Constant::Str(s) = &constant.value {
                return Some(s.to_string());
            }
        }
    }
    None
}

/// Extract parameter names from function arguments
fn extract_parameters(args: &ast::Arguments) -> Vec<String> {
    let mut params = Vec::new();
    
    // Regular args
    for arg in &args.args {
        params.push(arg.def.arg.to_string());
    }
    
    // *args
    if let Some(vararg) = &args.vararg {
        params.push(format!("*{}", vararg.arg));
    }
    
    // **kwargs
    if let Some(kwarg) = &args.kwarg {
        params.push(format!("**{}", kwarg.arg));
    }
    
    params
}

/// Convert expression to string representation
fn expr_to_string(expr: &ast::Expr) -> String {
    // Simplified - in real implementation would handle all expression types
    match expr {
        ast::Expr::Name(name) => name.id.to_string(),
        ast::Expr::Attribute(attr) => {
            format!("{}.{}", expr_to_string(&attr.value), attr.attr)
        }
        ast::Expr::Call(call) => {
            format!("{}(...)", expr_to_string(&call.func))
        }
        _ => "...".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_parse_function() {
        let source = r#"
def hello_world(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"
"#;
        
        let parser = PythonParser::new();
        let entities = parser.parse_source(source, Path::new("test.py")).unwrap();
        
        assert_eq!(entities.len(), 1);
        assert_eq!(entities[0].name, "hello_world");
        assert_eq!(entities[0].entity_type, "function");
        assert_eq!(entities[0].parameters, vec!["name"]);
        assert_eq!(entities[0].return_type, Some("str".to_string()));
        assert_eq!(entities[0].docstring, Some("Say hello to someone.".to_string()));
    }

    #[test]
    fn test_parse_class() {
        let source = r#"
class MyClass:
    """A sample class."""
    
    def method(self):
        pass
"#;
        
        let parser = PythonParser::new();
        let entities = parser.parse_source(source, Path::new("test.py")).unwrap();
        
        assert_eq!(entities.len(), 2);
        assert_eq!(entities[0].name, "MyClass");
        assert_eq!(entities[0].entity_type, "class");
        assert_eq!(entities[1].name, "method");
        assert_eq!(entities[1].entity_type, "method");
    }

    #[test]
    fn test_parse_async_function() {
        let source = r#"
async def fetch_data():
    """Fetch data asynchronously."""
    pass
"#;
        
        let parser = PythonParser::new();
        let entities = parser.parse_source(source, Path::new("test.py")).unwrap();
        
        assert_eq!(entities.len(), 1);
        assert_eq!(entities[0].name, "fetch_data");
        assert!(entities[0].is_async);
    }
}