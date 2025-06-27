// High-performance Rust core for Autodoc

use pyo3::prelude::*;
use std::path::Path;

pub mod analyzer;
pub mod entity;
pub mod parser;

use entity::CodeEntity;
use analyzer::RustAnalyzer;

/// Main entry point for Python bindings
#[pymodule]
fn autodoc_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCodeEntity>()?;
    m.add_class::<PyRustAnalyzer>()?;
    m.add_function(wrap_pyfunction!(analyze_directory_rust, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_file_rust, m)?)?;
    Ok(())
}

/// Python-compatible wrapper for CodeEntity
#[pyclass(name = "CodeEntity")]
#[derive(Clone)]
pub struct PyCodeEntity {
    #[pyo3(get, set)]
    pub entity_type: String,
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub file_path: String,
    #[pyo3(get, set)]
    pub line_number: usize,
    #[pyo3(get, set)]
    pub docstring: Option<String>,
    #[pyo3(get, set)]
    pub code: String,
    #[pyo3(get, set)]
    pub is_async: bool,
    #[pyo3(get, set)]
    pub decorators: Vec<String>,
    #[pyo3(get, set)]
    pub parameters: Vec<String>,
    #[pyo3(get, set)]
    pub return_type: Option<String>,
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
    fn new() -> Self {
        PyRustAnalyzer {
            analyzer: RustAnalyzer::new(),
        }
    }

    fn analyze_file(&self, file_path: &str) -> PyResult<Vec<PyCodeEntity>> {
        let entities = self.analyzer.analyze_file(Path::new(file_path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(entities.into_iter().map(|e| e.into()).collect())
    }

    fn analyze_directory(&self, dir_path: &str) -> PyResult<Vec<PyCodeEntity>> {
        let entities = self.analyzer.analyze_directory(Path::new(dir_path))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        Ok(entities.into_iter().map(|e| e.into()).collect())
    }
}

/// Direct function for analyzing a directory
#[pyfunction]
fn analyze_directory_rust(path: &str) -> PyResult<Vec<PyCodeEntity>> {
    let analyzer = RustAnalyzer::new();
    let entities = analyzer.analyze_directory(Path::new(path))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    Ok(entities.into_iter().map(|e| e.into()).collect())
}

/// Direct function for analyzing a single file
#[pyfunction]
fn analyze_file_rust(path: &str) -> PyResult<Vec<PyCodeEntity>> {
    let analyzer = RustAnalyzer::new();
    let entities = analyzer.analyze_file(Path::new(path))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    
    Ok(entities.into_iter().map(|e| e.into()).collect())
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
        }
    }
}