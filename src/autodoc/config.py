#!/usr/bin/env python3
"""
Configuration management for autodoc.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, List

import yaml
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    provider: str = Field("openai", description="LLM provider (openai, anthropic, ollama)")
    model: str = Field("gpt-4o-mini", description="Model to use for enrichment")
    api_key: Optional[str] = Field(None, description="API key for the LLM provider")
    base_url: Optional[str] = Field(None, description="Base URL for custom LLM endpoints")
    temperature: float = Field(0.3, description="Temperature for LLM generation")
    max_tokens: int = Field(500, description="Maximum tokens for LLM generation")

    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key

        # Check environment variables
        if self.provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")

        return None


class EnrichmentConfig(BaseModel):
    """Configuration for code enrichment."""

    enabled: bool = Field(True, description="Enable or disable code enrichment")
    batch_size: int = Field(10, description="Number of entities to process at once")
    cache_enrichments: bool = Field(True, description="Cache enriched entities to disk")
    include_examples: bool = Field(True, description="Include usage examples in enrichment")
    analyze_complexity: bool = Field(True, description="Analyze code complexity during enrichment")
    detect_patterns: bool = Field(True, description="Detect design patterns during enrichment")
    languages: List[str] = Field(default_factory=lambda: ["python", "typescript"], description="List of languages to enrich")


class AutodocConfig(BaseModel):
    """Main configuration for autodoc."""

    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM settings")
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig, description="Enrichment settings")
    embeddings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "chromadb_model": "all-MiniLM-L6-v2",
            "dimensions": 1536,
            "batch_size": 100,
            "persist_directory": ".autodoc_chromadb",
        },
        description="Embedding settings",
    )
    graph: Dict[str, Any] = Field(
        default_factory=lambda: {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_username": "neo4j",
            "neo4j_password": "password",
            "enrich_nodes": True,
        },
        description="Graph settings",
    )
    analysis: Dict[str, Any] = Field(
        default_factory=lambda: {
            "ignore_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"],
            "max_file_size": 1048576,
            "follow_imports": True,
            "analyze_dependencies": True,
        },
        description="Analysis settings",
    )
    output: Dict[str, Any] = Field(
        default_factory=lambda: {
            "format": "markdown",
            "include_code_snippets": True,
            "max_description_length": 500,
            "group_by_feature": True,
        },
        description="Output settings",
    )

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
            except Exception as e:
                log.error(f"Error loading config file {config_file}: {e}")
                # If there's an error loading the file, proceed with defaults
                return cls()

        return cls.parse_obj(config_data)

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
