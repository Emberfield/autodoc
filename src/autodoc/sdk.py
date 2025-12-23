"""
Clean Python SDK for Autodoc.

Usage:
    from autodoc import Autodoc, Pack

    # Initialize with repo path
    autodoc = Autodoc("/path/to/repo")

    # Analyze codebase
    result = autodoc.analyze()

    # Search with natural language
    results = autodoc.search("user authentication flow")

    # Work with context packs
    packs = autodoc.list_packs()
    auth_pack = autodoc.get_pack("auth")

    # Analyze impact of changes
    impact = autodoc.analyze_impact(["src/auth/login.py"])
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .autodoc import SimpleAutodoc
from .chromadb_embedder import ChromaDBEmbedder
from .config import AutodocConfig, ContextPackConfig


@dataclass
class SearchResult:
    """A single search result."""

    name: str
    type: str
    file_path: str
    line_number: int
    similarity: float
    docstring: Optional[str] = None
    code: Optional[str] = None
    pack: Optional[str] = None


@dataclass
class AnalysisResult:
    """Result of codebase analysis."""

    files_analyzed: int
    total_entities: int
    functions: int
    classes: int
    methods: int
    has_embeddings: bool
    languages: Dict[str, Dict[str, int]]


@dataclass
class ImpactResult:
    """Result of impact analysis."""

    affected_packs: List[str]
    critical_packs: List[str]
    files_affected: List[str]
    security_implications: List[str]


@dataclass
class Pack:
    """A context pack representing a logical grouping of code."""

    name: str
    display_name: str
    description: str
    files: List[str]
    dependencies: List[str]
    security_level: Optional[str]
    tags: List[str]
    tables: List[str]

    @classmethod
    def from_config(cls, config: ContextPackConfig) -> "Pack":
        """Create Pack from ContextPackConfig."""
        return cls(
            name=config.name,
            display_name=config.display_name,
            description=config.description,
            files=config.files,
            dependencies=config.dependencies,
            security_level=config.security_level,
            tags=config.tags,
            tables=config.tables,
        )


def _run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, can't use run_until_complete
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running loop, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class Autodoc:
    """
    Main SDK class for Autodoc code intelligence.

    Example:
        >>> from autodoc import Autodoc
        >>> autodoc = Autodoc("/path/to/repo")
        >>> autodoc.analyze()
        >>> results = autodoc.search("authentication")
    """

    def __init__(
        self,
        path: Union[str, Path],
        config: Optional[AutodocConfig] = None,
        quiet: bool = False,
    ):
        """
        Initialize Autodoc for a repository.

        Args:
            path: Path to the repository root
            config: Optional AutodocConfig. If not provided, loads from autodoc.yaml
            quiet: Suppress console output
        """
        self.path = Path(path).resolve()
        self._quiet = quiet

        # Load config from path if not provided
        if config is None:
            config = AutodocConfig.load(self.path)
        self.config = config

        # Initialize internal autodoc
        self._autodoc = SimpleAutodoc(config)
        self._analyzed = False

    def analyze(
        self,
        incremental: bool = False,
        exclude_patterns: Optional[List[str]] = None,
        save: bool = True,
    ) -> AnalysisResult:
        """
        Analyze the codebase.

        Args:
            incremental: Only analyze changed files
            exclude_patterns: Glob patterns to exclude
            save: Save results to cache

        Returns:
            AnalysisResult with analysis statistics
        """
        result = _run_async(
            self._autodoc.analyze_directory(
                self.path,
                incremental=incremental,
                exclude_patterns=exclude_patterns or [],
            )
        )

        if save:
            self._autodoc.save(str(self.path / "autodoc_cache.json"))

        self._analyzed = True

        return AnalysisResult(
            files_analyzed=result.get("files_analyzed", 0),
            total_entities=result.get("total_entities", 0),
            functions=result.get("functions", 0),
            classes=result.get("classes", 0),
            methods=result.get("methods", 0),
            has_embeddings=result.get("has_embeddings", False),
            languages=result.get("languages", {}),
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        type_filter: Optional[str] = None,
        pack: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search the codebase with natural language.

        Args:
            query: Natural language search query
            limit: Maximum number of results
            type_filter: Filter by entity type (function, class, method)
            pack: Limit search to a specific context pack

        Returns:
            List of SearchResult objects
        """
        # If searching within a pack, use pack-specific ChromaDB collection
        if pack:
            return self._search_pack(query, pack, limit)

        # Global search
        results = _run_async(
            self._autodoc.search(
                query,
                limit=limit,
                type_filter=type_filter,
            )
        )

        return [
            SearchResult(
                name=r["entity"]["name"],
                type=r["entity"]["type"],
                file_path=r["entity"]["file_path"],
                line_number=r["entity"]["line_number"],
                similarity=r["similarity"],
                docstring=r["entity"].get("docstring"),
                code=r["entity"].get("code"),
            )
            for r in results
        ]

    def _search_pack(self, query: str, pack_name: str, limit: int) -> List[SearchResult]:
        """Search within a specific pack's embeddings."""
        pack_config = self.config.get_pack(pack_name)
        if not pack_config:
            raise ValueError(f"Pack '{pack_name}' not found")

        # Try to use pack-specific ChromaDB collection
        pack_db_path = self.path / ".autodoc" / "packs" / f"{pack_name}_chromadb"
        if pack_db_path.exists():
            embedder = ChromaDBEmbedder(
                collection_name=f"autodoc_pack_{pack_name}",
                persist_directory=str(pack_db_path),
            )
            results = _run_async(embedder.search(query, limit=limit))
            return [
                SearchResult(
                    name=r["entity"]["name"],
                    type=r["entity"]["type"],
                    file_path=r["entity"]["file_path"],
                    line_number=r["entity"]["line_number"],
                    similarity=r["similarity"],
                    pack=pack_name,
                )
                for r in results
            ]

        # Fallback: filter global search by pack files
        import fnmatch

        all_results = self.search(query, limit=limit * 3)
        pack_results = []
        for result in all_results:
            for pattern in pack_config.files:
                if fnmatch.fnmatch(result.file_path, pattern):
                    result.pack = pack_name
                    pack_results.append(result)
                    break
            if len(pack_results) >= limit:
                break
        return pack_results

    def list_packs(
        self,
        tag: Optional[str] = None,
        security_level: Optional[str] = None,
    ) -> List[Pack]:
        """
        List all context packs.

        Args:
            tag: Filter by tag
            security_level: Filter by security level (critical, high, normal)

        Returns:
            List of Pack objects
        """
        packs = self.config.context_packs

        if tag:
            packs = [p for p in packs if tag in p.tags]

        if security_level:
            packs = [p for p in packs if p.security_level == security_level]

        return [Pack.from_config(p) for p in packs]

    def get_pack(self, name: str) -> Optional[Pack]:
        """
        Get a specific context pack by name.

        Args:
            name: Pack name

        Returns:
            Pack object or None if not found
        """
        config = self.config.get_pack(name)
        if config:
            return Pack.from_config(config)
        return None

    def analyze_impact(self, changed_files: List[str]) -> ImpactResult:
        """
        Analyze the impact of file changes on context packs.

        Args:
            changed_files: List of file paths that changed

        Returns:
            ImpactResult with affected packs and security implications
        """
        import fnmatch

        affected_packs = []
        critical_packs = []
        security_implications = []

        for pack_config in self.config.context_packs:
            pack_affected = False
            for changed_file in changed_files:
                for pattern in pack_config.files:
                    if fnmatch.fnmatch(changed_file, pattern):
                        pack_affected = True
                        break
                if pack_affected:
                    break

            if pack_affected:
                affected_packs.append(pack_config.name)
                if pack_config.security_level == "critical":
                    critical_packs.append(pack_config.name)
                    security_implications.append(
                        f"CRITICAL: Changes affect {pack_config.display_name} "
                        f"(security level: critical)"
                    )
                elif pack_config.security_level == "high":
                    security_implications.append(
                        f"HIGH: Changes affect {pack_config.display_name} (security level: high)"
                    )

        return ImpactResult(
            affected_packs=affected_packs,
            critical_packs=critical_packs,
            files_affected=changed_files,
            security_implications=security_implications,
        )

    def build_pack(
        self,
        name: str,
        with_embeddings: bool = True,
        with_summary: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a context pack's index and optionally generate embeddings/summary.

        Args:
            name: Pack name to build
            with_embeddings: Generate ChromaDB embeddings
            with_summary: Generate LLM summary (requires API key)
            dry_run: Preview without making changes

        Returns:
            Build result with statistics
        """
        pack_config = self.config.get_pack(name)
        if not pack_config:
            raise ValueError(f"Pack '{name}' not found")

        # This would integrate with the CLI's pack_build functionality
        # For now, return a stub that shows what would be built
        import glob

        files = []
        for pattern in pack_config.files:
            full_pattern = str(self.path / pattern)
            files.extend(glob.glob(full_pattern, recursive=True))

        return {
            "pack": name,
            "files_matched": len(files),
            "files": files[:10],  # First 10 for preview
            "with_embeddings": with_embeddings,
            "with_summary": with_summary,
            "dry_run": dry_run,
        }

    def get_pack_dependencies(
        self,
        name: str,
        transitive: bool = False,
    ) -> List[str]:
        """
        Get dependencies for a pack.

        Args:
            name: Pack name
            transitive: Include transitive dependencies

        Returns:
            List of dependency pack names
        """
        if transitive:
            deps = self.config.resolve_pack_dependencies(name)
            return [d.name for d in deps]

        pack = self.config.get_pack(name)
        if pack:
            return pack.dependencies
        return []

    def load(self, cache_path: Optional[str] = None) -> None:
        """Load previously analyzed data from cache."""
        path = cache_path or str(self.path / "autodoc_cache.json")
        self._autodoc.load(path)
        self._analyzed = True

    def save(self, cache_path: Optional[str] = None) -> None:
        """Save analyzed data to cache."""
        path = cache_path or str(self.path / "autodoc_cache.json")
        self._autodoc.save(path)

    @property
    def entities(self):
        """Access to raw code entities."""
        return self._autodoc.entities

    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive codebase summary."""
        return self._autodoc.generate_summary()

    def format_summary_markdown(self, summary: Dict[str, Any]) -> str:
        """Format summary as Markdown."""
        return self._autodoc.format_summary_markdown(summary)


# Convenience function for quick analysis
def analyze(path: Union[str, Path], **kwargs) -> Autodoc:
    """
    Quick analysis of a codebase.

    Example:
        >>> from autodoc import analyze
        >>> autodoc = analyze("/path/to/repo")
        >>> results = autodoc.search("authentication")
    """
    autodoc = Autodoc(path, **kwargs)
    autodoc.analyze()
    return autodoc
