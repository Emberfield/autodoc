use criterion::{black_box, criterion_group, criterion_main, Criterion};
use autodoc_core::analyzer::RustAnalyzer;
use std::path::Path;

fn benchmark_analyze_file(c: &mut Criterion) {
    let analyzer = RustAnalyzer::new();
    let test_file = Path::new("../src/autodoc/analyzer.py");
    
    c.bench_function("analyze_single_file", |b| {
        b.iter(|| {
            analyzer.analyze_file(black_box(test_file))
        });
    });
}

fn benchmark_analyze_directory(c: &mut Criterion) {
    let analyzer = RustAnalyzer::new();
    let test_dir = Path::new("../src/autodoc");
    
    c.bench_function("analyze_directory", |b| {
        b.iter(|| {
            analyzer.analyze_directory(black_box(test_dir))
        });
    });
}

criterion_group!(benches, benchmark_analyze_file, benchmark_analyze_directory);
criterion_main!(benches);