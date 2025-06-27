use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Core entity representing a code element (function, class, etc.)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeEntity {
    pub entity_type: String,
    pub name: String,
    pub file_path: PathBuf,
    pub line_number: usize,
    pub docstring: Option<String>,
    pub code: String,
    pub is_async: bool,
    pub decorators: Vec<String>,
    pub parameters: Vec<String>,
    pub return_type: Option<String>,
    pub is_internal: bool,
    pub is_api_endpoint: bool,
    pub endpoint_path: Option<String>,
    pub http_methods: Vec<String>,
    pub complexity_score: u32,
}

impl CodeEntity {
    pub fn new(
        entity_type: String,
        name: String,
        file_path: PathBuf,
        line_number: usize,
    ) -> Self {
        CodeEntity {
            entity_type,
            name,
            file_path,
            line_number,
            docstring: None,
            code: String::new(),
            is_async: false,
            decorators: Vec::new(),
            parameters: Vec::new(),
            return_type: None,
            is_internal: false,
            is_api_endpoint: false,
            endpoint_path: None,
            http_methods: Vec::new(),
            complexity_score: 1,
        }
    }

    /// Calculate complexity score based on various factors
    pub fn calculate_complexity(&mut self) {
        let mut score = 1;
        
        // Add complexity for parameters
        score += self.parameters.len() as u32;
        
        // Add complexity for nested structures
        let nest_count = self.code.matches('{').count() as u32;
        score += nest_count;
        
        // Add complexity for control flow
        let control_flow = ["if ", "for ", "while ", "match ", "loop "];
        for keyword in &control_flow {
            score += self.code.matches(keyword).count() as u32;
        }
        
        // Add complexity for async
        if self.is_async {
            score += 2;
        }
        
        self.complexity_score = score;
    }

    /// Check if this entity is likely an API endpoint
    pub fn detect_api_endpoint(&mut self) {
        let api_decorators = ["route", "get", "post", "put", "delete", "patch", "api"];
        
        self.is_api_endpoint = self.decorators.iter().any(|d| {
            api_decorators.iter().any(|api_d| d.to_lowercase().contains(api_d))
        });
        
        // Extract endpoint path and methods from decorators if possible
        if self.is_api_endpoint {
            for decorator in &self.decorators {
                if let Some(path) = extract_path_from_decorator(decorator) {
                    self.endpoint_path = Some(path);
                }
                
                // Extract HTTP methods
                let methods = extract_http_methods_from_decorator(decorator);
                if !methods.is_empty() {
                    self.http_methods = methods;
                }
            }
            
            // If no methods specified, default to GET
            if self.http_methods.is_empty() {
                self.http_methods = vec!["GET".to_string()];
            }
        }
    }
}

fn extract_path_from_decorator(decorator: &str) -> Option<String> {
    // Simple regex to extract path from decorators like @route("/api/users")
    use regex::Regex;
    let re = Regex::new(r#"["']([^"']+)["']"#).ok()?;
    
    re.captures(decorator)
        .and_then(|cap| cap.get(1))
        .map(|m| m.as_str().to_string())
}

fn extract_http_methods_from_decorator(decorator: &str) -> Vec<String> {
    use regex::Regex;
    let mut methods = Vec::new();
    
    // Check for specific method decorators like @app.get, @app.post
    let method_decorators = ["get", "post", "put", "delete", "patch"];
    for method in &method_decorators {
        if decorator.to_lowercase().contains(&format!(".{}", method)) {
            methods.push(method.to_uppercase());
            return methods;
        }
    }
    
    // Extract methods from methods=[...] parameter
    let re = Regex::new(r#"methods\s*=\s*\[([^\]]+)\]"#).ok();
    if let Some(re) = re {
        if let Some(captures) = re.captures(decorator) {
            if let Some(methods_str) = captures.get(1) {
                for method in methods_str.as_str().split(',') {
                    let method = method.trim().trim_matches('"').trim_matches('\'');
                    if !method.is_empty() {
                        methods.push(method.to_uppercase());
                    }
                }
            }
        }
    }
    
    methods
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_entity_creation() {
        let entity = CodeEntity::new(
            "function".to_string(),
            "test_func".to_string(),
            PathBuf::from("test.py"),
            10,
        );
        
        assert_eq!(entity.entity_type, "function");
        assert_eq!(entity.name, "test_func");
        assert_eq!(entity.line_number, 10);
        assert!(!entity.is_async);
    }

    #[test]
    fn test_complexity_calculation() {
        let mut entity = CodeEntity::new(
            "function".to_string(),
            "complex_func".to_string(),
            PathBuf::from("test.py"),
            10,
        );
        
        entity.parameters = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        entity.code = "def complex_func(a, b, c):\n    if a:\n        for i in b:\n            while c:\n                pass".to_string();
        entity.is_async = true;
        
        entity.calculate_complexity();
        
        assert!(entity.complexity_score > 5);
    }

    #[test]
    fn test_api_endpoint_detection() {
        let mut entity = CodeEntity::new(
            "function".to_string(),
            "get_users".to_string(),
            PathBuf::from("api.py"),
            20,
        );
        
        entity.decorators = vec!["@app.route('/api/users')".to_string()];
        entity.detect_api_endpoint();
        
        assert!(entity.is_api_endpoint);
        assert_eq!(entity.endpoint_path, Some("/api/users".to_string()));
    }
}