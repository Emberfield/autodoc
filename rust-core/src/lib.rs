// High-performance Rust core for Autodoc

use pyo3::prelude::*;
use pyo3::exceptions::PyException;
use std::path::Path;

pub mod analyzer;
pub mod entity;
pub mod parser;

use entity::CodeEntity;
use analyzer::RustAnalyzer;

// Create a custom Python exception for Rust errors
pyo3::create_exception!(autodoc_core, RustAnalysisError, PyException);

/// Main entry point for Python bindings
#[pymodule]
fn autodoc_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCodeEntity>()?;
    m.add_class::<PyRustAnalyzer>()?;
    m.add("RustAnalysisError", m.py().get_type_bound::<RustAnalysisError>())?;
    Ok(())
}

/// Python-compatible wrapper for CodeEntity
#[pyclass(name = "CodeEntity")]
#[derive(Clone)]
pub struct PyCodeEntity {
    #[pyo3(get)]
    pub entity_type: String,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub file_path: String,
    #[pyo3(get)]
    pub line_number: usize,
    #[pyo3(get)]
    pub docstring: Option<String>,
    #[pyo3(get)]
    pub code: String,
    #[pyo3(get)]
    pub is_async: bool,
    #[pyo3(get)]
    pub decorators: Vec<String>,
    #[pyo3(get)]
    pub parameters: Vec<String>,
    #[pyo3(get)]
    pub return_type: Option<String>,
    #[pyo3(get)]
    pub is_internal: bool,
    #[pyo3(get)]
    pub is_api_endpoint: bool,
    #[pyo3(get)]
    pub route_path: Option<String>,
    #[pyo3(get)]
    pub http_methods: Vec<String>,
    #[pyo3(get)]
    pub complexity_score: u32,
}

#[pymethods]
impl PyCodeEntity {
    #[new]
    fn new(
        entity_type: String,
        name: String,
        file_path: String,
        line_number: usize,
    ) -> Self {
        PyCodeEntity {
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
            route_path: None,
            http_methods: Vec::new(),
            complexity_score: 1,
        }
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = pyo3::types::PyDict::new_bound(py);
        dict.set_item("type", &self.entity_type)?;
        dict.set_item("name", &self.name)?;
        dict.set_item("file_path", &self.file_path)?;
        dict.set_item("line_number", &self.line_number)?;
        dict.set_item("docstring", &self.docstring)?;
        dict.set_item("code", &self.code)?;
        dict.set_item("is_async", &self.is_async)?;
        dict.set_item("decorators", &self.decorators)?;
        dict.set_item("parameters", &self.parameters)?;
        dict.set_item("return_type", &self.return_type)?;
        dict.set_item("is_internal", &self.is_internal)?;
        dict.set_item("is_api_endpoint", &self.is_api_endpoint)?;
        dict.set_item("route_path", &self.route_path)?;
        dict.set_item("http_methods", &self.http_methods)?;
        dict.set_item("complexity_score", &self.complexity_score)?;
        Ok(dict.into())
    }
}

/// Python-compatible wrapper for RustAnalyzer
#[pyclass(name = "RustAnalyzer")]
pub struct PyRustAnalyzer {
    analyzer: RustAnalyzer,
}

#[pymethods]
impl PyRustAnalyzer {
    #[new]
    #[pyo3(signature = (exclude_patterns=None))]
    fn new(exclude_patterns: Option<Vec<String>>) -> Self {
        let mut analyzer = RustAnalyzer::new();
        if let Some(patterns) = exclude_patterns {
            let pattern_refs: Vec<&str> = patterns.iter().map(|s| s.as_str()).collect();
            analyzer = analyzer.with_excludes(pattern_refs);
        }
        PyRustAnalyzer {
            analyzer,
        }
    }

    fn analyze_file(&self, file_path: &str) -> PyResult<Vec<PyCodeEntity>> {
        let entities = self.analyzer.analyze_file(Path::new(file_path))
            .map_err(|e| RustAnalysisError::new_err(e.to_string()))?;
        
        Ok(entities.into_iter().map(|e| e.into()).collect())
    }

    fn analyze_directory(&self, dir_path: &str) -> PyResult<Vec<PyCodeEntity>> {
        let entities = self.analyzer.analyze_directory(Path::new(dir_path))
            .map_err(|e| RustAnalysisError::new_err(e.to_string()))?;
        
        Ok(entities.into_iter().map(|e| e.into()).collect())
    }
}



impl From<CodeEntity> for PyCodeEntity {
    fn from(entity: CodeEntity) -> Self {
        PyCodeEntity {
            entity_type: entity.entity_type,
            name: entity.name,
            file_path: entity.file_path.to_string_lossy().to_string(),
            line_number: entity.line_number,
            docstring: entity.docstring,
            code: entity.code,
            is_async: entity.is_async,
            decorators: entity.decorators,
            parameters: entity.parameters,
            return_type: entity.return_type,
            is_internal: entity.is_internal,
            is_api_endpoint: entity.is_api_endpoint,
            route_path: entity.endpoint_path,
            http_methods: entity.http_methods,
            complexity_score: entity.complexity_score,
        }
    }
}
