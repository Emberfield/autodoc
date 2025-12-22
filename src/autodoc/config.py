#!/usr/bin/env python3
"""
Configuration management for autodoc.
"""

import logging
import os
from pathlib import Path
from typing import Literal, Optional, List

import yaml
from pydantic import BaseModel, Field, field_validator

log = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    provider: Literal["openai", "anthropic", "ollama"] = Field(
        "openai", description="LLM provider"
    )
    model: str = Field("gpt-4o-mini", description="Model to use for enrichment")
    api_key: Optional[str] = Field(None, description="API key for the LLM provider")
    base_url: Optional[str] = Field(None, description="Base URL for custom LLM endpoints")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="Temperature for LLM generation")
    max_tokens: int = Field(500, gt=0, description="Maximum tokens for LLM generation")

    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key

        # Check environment variables based on provider
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama": "OLLAMA_API_KEY",  # Optional for local Ollama
        }
        env_var = env_var_map.get(self.provider)
        if env_var:
            return os.getenv(env_var)

        return None


class EnrichmentConfig(BaseModel):
    """Configuration for code enrichment."""

    enabled: bool = Field(True, description="Enable or disable code enrichment")
    batch_size: int = Field(10, gt=0, le=100, description="Number of entities to process at once")
    cache_enrichments: bool = Field(True, description="Cache enriched entities to disk")
    include_examples: bool = Field(True, description="Include usage examples in enrichment")
    analyze_complexity: bool = Field(True, description="Analyze code complexity during enrichment")
    detect_patterns: bool = Field(True, description="Detect design patterns during enrichment")
    languages: List[str] = Field(
        default_factory=lambda: ["python", "typescript"],
        description="List of languages to enrich"
    )


class CostControlConfig(BaseModel):
    """Configuration for controlling LLM API costs."""

    max_tokens_per_run: Optional[int] = Field(
        None, description="Maximum tokens allowed per run (None = unlimited)"
    )
    warn_entity_threshold: int = Field(
        100, ge=0, description="Warn when pack has more than this many entities"
    )
    summary_model: Optional[str] = Field(
        None,
        description="Cheaper model to use for pack summaries (e.g., 'claude-3-haiku-20240307', 'gpt-4o-mini'). If None, uses llm.model"
    )
    cache_summaries: bool = Field(
        True, description="Cache pack summaries to avoid regenerating unchanged content"
    )
    dry_run_by_default: bool = Field(
        False, description="Run in dry-run mode by default (show what would happen without API calls)"
    )


class EmbeddingsConfig(BaseModel):
    """Configuration for embeddings generation."""

    provider: Literal["openai", "chromadb"] = Field("openai", description="Embeddings provider")
    model: str = Field("text-embedding-3-small", description="OpenAI embedding model")
    chromadb_model: str = Field("all-MiniLM-L6-v2", description="ChromaDB/sentence-transformers model")
    dimensions: int = Field(1536, gt=0, description="Embedding dimensions")
    batch_size: int = Field(100, gt=0, le=1000, description="Batch size for embedding generation")
    persist_directory: str = Field(".autodoc_chromadb", description="Directory for ChromaDB persistence")


class GraphConfig(BaseModel):
    """Configuration for Neo4j graph database."""

    neo4j_uri: str = Field(
        default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        description="Neo4j connection URI"
    )
    neo4j_username: str = Field(
        default_factory=lambda: os.getenv("NEO4J_USERNAME", "neo4j"),
        description="Neo4j username"
    )
    neo4j_password: Optional[str] = Field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD"),
        description="Neo4j password (from NEO4J_PASSWORD env var)"
    )
    enrich_nodes: bool = Field(True, description="Enrich graph nodes with LLM analysis")

    @field_validator("neo4j_uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        """Validate Neo4j URI format."""
        if not v.startswith(("bolt://", "neo4j://", "neo4j+s://", "bolt+s://")):
            raise ValueError("neo4j_uri must start with bolt://, neo4j://, neo4j+s://, or bolt+s://")
        return v


class AnalysisConfig(BaseModel):
    """Configuration for code analysis."""

    ignore_patterns: List[str] = Field(
        default_factory=lambda: ["__pycache__", "*.pyc", ".git", "node_modules"],
        description="Glob patterns for files/directories to ignore"
    )
    max_file_size: int = Field(
        1048576, gt=0, description="Maximum file size in bytes (default 1MB)"
    )
    follow_imports: bool = Field(True, description="Follow and analyze imported modules")
    analyze_dependencies: bool = Field(True, description="Analyze module dependencies")


class OutputConfig(BaseModel):
    """Configuration for output generation."""

    format: Literal["markdown", "json", "html"] = Field("markdown", description="Output format")
    include_code_snippets: bool = Field(True, description="Include code snippets in output")
    max_description_length: int = Field(
        500, gt=0, le=10000, description="Maximum description length in characters"
    )
    group_by_feature: bool = Field(True, description="Group entities by feature/module")


class ContextPackConfig(BaseModel):
    """Configuration for a context pack - a logical grouping of related code entities."""

    name: str = Field(..., description="Unique identifier for the pack (e.g., 'authentication')")
    display_name: str = Field(..., description="Human-readable name (e.g., 'Authentication System')")
    description: str = Field(..., description="Description of what this pack covers")
    files: List[str] = Field(
        default_factory=list,
        description="Glob patterns for files in this pack (e.g., ['src/auth/**/*.py'])"
    )
    tables: List[str] = Field(
        default_factory=list,
        description="Database tables related to this pack (for documentation)"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Names of other packs this pack depends on"
    )
    security_level: Optional[Literal["critical", "high", "normal"]] = Field(
        None, description="Security classification for this pack"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization (e.g., ['security', 'core'])"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate pack name is a valid identifier."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Pack name must contain only alphanumeric characters, underscores, and hyphens")
        return v.lower()


class DatabaseConfig(BaseModel):
    """Configuration for database schema analysis."""

    migration_paths: List[str] = Field(
        default_factory=lambda: [
            "init/postgres/*.sql",
            "alembic/versions/*.py",
            "migrations/*.sql",
        ],
        description="Paths to database migration files"
    )
    model_paths: List[str] = Field(
        default_factory=lambda: [
            "api/models/*.py",
            "src/models/*.py",
            "**/models.py",
        ],
        description="Paths to ORM model files"
    )
    analyze_schema: bool = Field(
        False, description="Whether to parse and analyze database schema"
    )


class AutodocConfig(BaseModel):
    """Main configuration for autodoc."""

    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM settings")
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig, description="Enrichment settings")
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig, description="Embedding settings")
    graph: GraphConfig = Field(default_factory=GraphConfig, description="Graph database settings")
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig, description="Analysis settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database schema settings")
    cost_control: CostControlConfig = Field(
        default_factory=CostControlConfig, description="Cost control settings for LLM API usage"
    )
    context_packs: List[ContextPackConfig] = Field(
        default_factory=list, description="Context packs for feature-based code grouping"
    )

    def get_pack(self, name: str) -> Optional[ContextPackConfig]:
        """Get a context pack by name."""
        for pack in self.context_packs:
            if pack.name == name.lower():
                return pack
        return None

    def get_packs_by_tag(self, tag: str) -> List[ContextPackConfig]:
        """Get all context packs with a specific tag."""
        return [pack for pack in self.context_packs if tag in pack.tags]

    def get_packs_by_security_level(
        self, level: Literal["critical", "high", "normal"]
    ) -> List[ContextPackConfig]:
        """Get all context packs with a specific security level."""
        return [pack for pack in self.context_packs if pack.security_level == level]

    def resolve_pack_dependencies(self, pack_name: str) -> List[ContextPackConfig]:
        """Resolve all dependencies for a pack (including transitive)."""
        pack = self.get_pack(pack_name)
        if not pack:
            return []

        resolved: List[ContextPackConfig] = []
        seen: set[str] = set()

        def resolve(p: ContextPackConfig) -> None:
            if p.name in seen:
                return
            seen.add(p.name)
            for dep_name in p.dependencies:
                dep = self.get_pack(dep_name)
                if dep:
                    resolve(dep)
            resolved.append(p)

        resolve(pack)
        return resolved

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AutodocConfig":
        """Load configuration from file or defaults."""
        config_data = {}
        config_file = None

        # Look for config file
        if config_path and config_path.exists():
            config_file = config_path
        else:
            # Search for config in common locations
            for filename in [".autodoc.yml", ".autodoc.yaml", "autodoc.yml", "autodoc.yaml"]:
                temp_config_file = Path.cwd() / filename
                if temp_config_file.exists():
                    config_file = temp_config_file
                    break

        if config_file:
            try:
                with open(config_file, "r") as f:
                    config_data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                log.warning(f"Config file not found: {config_file}, using defaults")
                return cls()
            except yaml.YAMLError as e:
                log.error(f"Invalid YAML in config file {config_file}: {e}")
                return cls()
            except OSError as e:
                log.error(f"Error reading config file {config_file}: {e}")
                return cls()

        return cls.model_validate(config_data)

    def save(self, config_path: Optional[Path] = None):
        """Save configuration to file."""
        if not config_path:
            config_path = Path.cwd() / ".autodoc.yml"

        # Use model_dump to get a dictionary representation of the config
        config_data = self.model_dump(exclude_none=True, exclude_defaults=True)

        # Handle API key and base_url separately if they are set
        if self.llm.api_key:
            config_data.setdefault("llm", {})["api_key"] = "# Set via environment variable or add here"
        if self.llm.base_url:
            config_data.setdefault("llm", {})["base_url"] = self.llm.base_url

        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
