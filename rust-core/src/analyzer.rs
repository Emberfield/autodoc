use anyhow::{Result, Context};
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;
use glob::Pattern;

use crate::entity::CodeEntity;
use crate::parser::PythonParser;

/// High-performance Rust analyzer for Python codebases
pub struct RustAnalyzer {
    parser: PythonParser,
    exclude_patterns: Vec<Pattern>,
}

impl RustAnalyzer {
    pub fn new() -> Self {
        let default_excludes = vec![
            "__pycache__", "venv", ".venv", "build", "dist", 
            "node_modules", ".git", "*.egg-info"
        ];
        
        let exclude_patterns = default_excludes
            .iter()
            .filter_map(|p| Pattern::new(p).ok())
            .collect();
        
        RustAnalyzer {
            parser: PythonParser::new(),
            exclude_patterns,
        }
    }

    /// Analyze a single Python file
    pub fn analyze_file(&self, file_path: &Path) -> Result<Vec<CodeEntity>> {
        if !file_path.exists() {
            return Err(anyhow::anyhow!("File does not exist: {:?}", file_path));
        }
        
        if !file_path.extension().map_or(false, |ext| ext == "py") {
            return Err(anyhow::anyhow!("Not a Python file: {:?}", file_path));
        }
        
        self.parser.parse_file(file_path)
            .with_context(|| format!("Failed to analyze file: {:?}", file_path))
    }

    /// Analyze all Python files in a directory (parallel processing)
    pub fn analyze_directory(&self, dir_path: &Path) -> Result<Vec<CodeEntity>> {
        let python_files = self.collect_python_files(dir_path)?;
        
        
        
        // Process files in parallel using Rayon
        let results: Vec<Result<Vec<CodeEntity>>> = python_files
            .par_iter()
            .map(|file_path| self.analyze_file(file_path))
            .collect();
        
        // Collect all entities, skipping failed files
        let mut all_entities = Vec::new();
        let mut errors = Vec::new();
        
        for (path, result) in python_files.iter().zip(results.into_iter()) {
            match result {
                Ok(entities) => all_entities.extend(entities),
                Err(e) => errors.push(format!("{}: {}", path.display(), e)),
            }
        }
        
        
        
        Ok(all_entities)
    }

    /// Collect all Python files in a directory, respecting exclude patterns
    fn collect_python_files(&self, dir_path: &Path) -> Result<Vec<PathBuf>> {
        let mut python_files = Vec::new();
        
        for entry in WalkDir::new(dir_path)
            .follow_links(false)
            .into_iter()
            .filter_entry(|e| !self.should_exclude(e.path())) 
        {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_file() && path.extension().map_or(false, |ext| ext == "py") {
                python_files.push(path.to_path_buf());
            }
        }
        
        Ok(python_files)
    }

    /// Check if a path should be excluded
    fn should_exclude(&self, path: &Path) -> bool {
        for component in path.components() {
            if let Some(name) = component.as_os_str().to_str() {
                for pattern in &self.exclude_patterns {
                    if pattern.matches(name) {
                        return true;
                    }
                }
            }
        }
        false
    }

    /// Analyze with custom exclude patterns
    pub fn with_excludes(mut self, patterns: Vec<&str>) -> Self {
        for pattern_str in patterns {
            if let Ok(pattern) = Pattern::new(pattern_str) {
                self.exclude_patterns.push(pattern);
            }
        }
        self
    }
}

/// Performance benchmarking utilities
pub mod benchmark {
    use super::*;
    use std::time::Instant;

    pub struct AnalyzerBenchmark;

    impl AnalyzerBenchmark {
        /// Benchmark directory analysis
        pub fn benchmark_directory(dir_path: &Path) -> Result<BenchmarkResult> {
            let analyzer = RustAnalyzer::new();
            
            let start = Instant::now();
            let entities = analyzer.analyze_directory(dir_path)?;
            let duration = start.elapsed();
            
            let files_count = entities.iter()
                .map(|e| &e.file_path)
                .collect::<std::collections::HashSet<_>>()
                .len();
            
            Ok(BenchmarkResult {
                duration_ms: duration.as_millis() as u64,
                files_analyzed: files_count,
                entities_found: entities.len(),
                entities_per_second: (entities.len() as f64 / duration.as_secs_f64()) as u64,
            })
        }
    }

    #[derive(Debug)]
    pub struct BenchmarkResult {
        pub duration_ms: u64,
        pub files_analyzed: usize,
        pub entities_found: usize,
        pub entities_per_second: u64,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    #[test]
    fn test_analyze_single_file() {
        let temp_dir = TempDir::new().unwrap();
        let file_path = temp_dir.path().join("test.py");
        
        fs::write(&file_path, "def hello(): pass").unwrap();
        
        let analyzer = RustAnalyzer::new();
        let entities = analyzer.analyze_file(&file_path).unwrap();
        
        assert_eq!(entities.len(), 1);
        assert_eq!(entities[0].name, "hello");
    }

    #[test]
    fn test_analyze_directory() {
        let temp_dir = TempDir::new().unwrap();
        
        // Create some Python files
        fs::write(temp_dir.path().join("file1.py"), "def func1(): pass").unwrap();
        fs::write(temp_dir.path().join("file2.py"), "class MyClass: pass").unwrap();
        
        // Create a file that should be excluded
        let pycache = temp_dir.path().join("__pycache__");
        fs::create_dir(&pycache).unwrap();
        fs::write(pycache.join("test.py"), "def excluded(): pass").unwrap();
        
        let analyzer = RustAnalyzer::new();
        let entities = analyzer.analyze_directory(temp_dir.path()).unwrap();
        
        assert_eq!(entities.len(), 2);
        assert!(entities.iter().any(|e| e.name == "func1"));
        assert!(entities.iter().any(|e| e.name == "MyClass"));
        assert!(!entities.iter().any(|e| e.name == "excluded"));
    }

    #[test]
    fn test_parallel_performance() {
        // This test would create many files and verify parallel processing
        // is faster than sequential
    }
}