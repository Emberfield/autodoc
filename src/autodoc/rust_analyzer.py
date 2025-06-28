"""
Python wrapper for the Rust core analyzer.
Falls back to Python implementation if Rust core is not available.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import the Rust core
try:
    import autodoc_core

    RUST_CORE_AVAILABLE = True
except ImportError:
    RUST_CORE_AVAILABLE = False
    print("Rust core not available, falling back to Python implementation")

from .analyzer import CodeEntity as PythonCodeEntity
from .analyzer import SimpleASTAnalyzer


@dataclass
class RustCodeEntity:
    """Wrapper for Rust CodeEntity to match Python interface."""

    type: str
    name: str
    file_path: str
    line_number: int
    docstring: Optional[str] = None
    code: str = ""
    embedding: Optional[List[float]] = None
    is_internal: bool = False
    is_api_endpoint: bool = False
    endpoint_path: Optional[str] = None
    http_methods: List[str] = None
    is_async: bool = False
    decorators: List[str] = None
    parameters: List[str] = None
    return_type: Optional[str] = None

    def __post_init__(self):
        if self.http_methods is None:
            self.http_methods = []
        if self.decorators is None:
            self.decorators = []
        if self.parameters is None:
            self.parameters = []

    @classmethod
    def from_rust_entity(cls, rust_entity) -> "RustCodeEntity":
        """Convert Rust entity to Python dataclass."""
        return cls(
            type=rust_entity.entity_type,
            name=rust_entity.name,
            file_path=rust_entity.file_path,
            line_number=rust_entity.line_number,
            docstring=rust_entity.docstring,
            code=rust_entity.code,
            is_async=rust_entity.is_async,
            decorators=rust_entity.decorators or [],
            parameters=rust_entity.parameters or [],
            return_type=rust_entity.return_type,
        )

    def to_python_entity(self) -> PythonCodeEntity:
        """Convert to Python CodeEntity for compatibility."""
        return PythonCodeEntity(
            type=self.type,
            name=self.name,
            file_path=self.file_path,
            line_number=self.line_number,
            docstring=self.docstring,
            code=self.code,
            embedding=self.embedding,
            is_internal=self.is_internal,
            is_api_endpoint=self.is_api_endpoint,
            endpoint_path=self.endpoint_path,
            http_methods=self.http_methods,
        )


class HybridAnalyzer:
    """
    Hybrid analyzer that uses Rust core when available,
    falls back to Python implementation otherwise.
    """

    def __init__(self, use_rust: bool = True):
        self.use_rust = use_rust and RUST_CORE_AVAILABLE

        if self.use_rust:
            self.rust_analyzer = autodoc_core.RustAnalyzer()
            print("Using high-performance Rust analyzer")
        else:
            self.python_analyzer = SimpleASTAnalyzer()
            print("Using Python analyzer")

    def analyze_file(self, file_path: Path) -> List[PythonCodeEntity]:
        """Analyze a single file."""
        if self.use_rust:
            try:
                rust_entities = self.rust_analyzer.analyze_file(str(file_path))
                return [
                    RustCodeEntity.from_rust_entity(e).to_python_entity() for e in rust_entities
                ]
            except Exception as e:
                print(f"Rust analyzer failed, falling back to Python: {e}")
                self.use_rust = False

        return self.python_analyzer.analyze_file(file_path)

    def analyze_directory(
        self, path: Path, exclude_patterns: List[str] = None
    ) -> List[PythonCodeEntity]:
        """Analyze all Python files in a directory."""
        if self.use_rust:
            try:
                rust_entities = self.rust_analyzer.analyze_directory(str(path))
                return [
                    RustCodeEntity.from_rust_entity(e).to_python_entity() for e in rust_entities
                ]
            except Exception as e:
                print(f"Rust analyzer failed, falling back to Python: {e}")
                self.use_rust = False

        return self.python_analyzer.analyze_directory(path, exclude_patterns)

    def benchmark_comparison(self, path: Path) -> Dict[str, Any]:
        """Compare performance between Rust and Python implementations."""
        import time

        results = {}

        # Benchmark Python implementation
        start = time.time()
        python_entities = self.python_analyzer.analyze_directory(path)
        python_time = time.time() - start

        results["python"] = {
            "time_seconds": python_time,
            "entities_found": len(python_entities),
            "entities_per_second": len(python_entities) / python_time if python_time > 0 else 0,
        }

        # Benchmark Rust implementation if available
        if RUST_CORE_AVAILABLE:
            rust_analyzer = autodoc_core.RustAnalyzer()
            start = time.time()
            rust_entities = rust_analyzer.analyze_directory(str(path))
            rust_time = time.time() - start

            results["rust"] = {
                "time_seconds": rust_time,
                "entities_found": len(rust_entities),
                "entities_per_second": len(rust_entities) / rust_time if rust_time > 0 else 0,
            }

            # Calculate speedup
            if python_time > 0:
                results["speedup"] = python_time / rust_time

        return results


def analyze_with_rust(path: Path) -> List[PythonCodeEntity]:
    """Direct function to analyze with Rust core."""
    if not RUST_CORE_AVAILABLE:
        raise ImportError("Rust core is not available. Run 'make build-rust' to compile it.")

    entities = autodoc_core.analyze_directory_rust(str(path))
    return [RustCodeEntity.from_rust_entity(e).to_python_entity() for e in entities]


# Performance testing utility
def run_performance_test(test_dir: Path = None):
    """Run performance comparison between Python and Rust implementations."""
    if test_dir is None:
        test_dir = Path.cwd()

    analyzer = HybridAnalyzer(use_rust=False)  # Force comparison
    results = analyzer.benchmark_comparison(test_dir)

    print("\n" + "=" * 50)
    print("Performance Comparison Results")
    print("=" * 50)

    if "python" in results:
        print("\nPython Implementation:")
        print(f"  Time: {results['python']['time_seconds']:.3f} seconds")
        print(f"  Entities: {results['python']['entities_found']}")
        print(f"  Speed: {results['python']['entities_per_second']:.0f} entities/second")

    if "rust" in results:
        print("\nRust Implementation:")
        print(f"  Time: {results['rust']['time_seconds']:.3f} seconds")
        print(f"  Entities: {results['rust']['entities_found']}")
        print(f"  Speed: {results['rust']['entities_per_second']:.0f} entities/second")

        if "speedup" in results:
            print(f"\n🚀 Rust is {results['speedup']:.1f}x faster than Python!")
    else:
        print("\n⚠️  Rust core not available for comparison")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    # Run performance test
    run_performance_test()
