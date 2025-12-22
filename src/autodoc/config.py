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


class AutodocConfig(BaseModel):
    """Main configuration for autodoc."""

    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM settings")
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig, description="Enrichment settings")
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig, description="Embedding settings")
    graph: GraphConfig = Field(default_factory=GraphConfig, description="Graph database settings")
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig, description="Analysis settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output settings")

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
