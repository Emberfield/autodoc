#!/usr/bin/env python3
"""
Configuration management for autodoc.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    provider: str = "openai"  # openai, anthropic, ollama
    model: str = "gpt-4o-mini"  # model to use for enrichment
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # for custom endpoints
    temperature: float = 0.3
    max_tokens: int = 500

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


@dataclass
class EnrichmentConfig:
    """Configuration for code enrichment."""

    enabled: bool = True
    batch_size: int = 10  # Number of entities to process at once
    cache_enrichments: bool = True
    include_examples: bool = True
    analyze_complexity: bool = True
    detect_patterns: bool = True
    languages: list = field(default_factory=lambda: ["python", "typescript"])


@dataclass
class AutodocConfig:
    """Main configuration for autodoc."""

    # LLM settings
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Enrichment settings
    enrichment: EnrichmentConfig = field(default_factory=EnrichmentConfig)

    # Embedding settings
    embeddings: Dict[str, Any] = field(
        default_factory=lambda: {
            "provider": "openai",  # Options: openai, chromadb
            "model": "text-embedding-3-small",  # For OpenAI
            "chromadb_model": "all-MiniLM-L6-v2",  # For ChromaDB local embeddings
            "dimensions": 1536,
            "batch_size": 100,
            "persist_directory": ".autodoc_chromadb",  # For ChromaDB
        }
    )

    # Graph settings
    graph: Dict[str, Any] = field(
        default_factory=lambda: {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_username": "neo4j",
            "neo4j_password": "password",
            "enrich_nodes": True,
        }
    )

    # Analysis settings
    analysis: Dict[str, Any] = field(
        default_factory=lambda: {
            "ignore_patterns": ["__pycache__", "*.pyc", ".git", "node_modules"],
            "max_file_size": 1048576,  # 1MB
            "follow_imports": True,
            "analyze_dependencies": True,
        }
    )

    # Output settings
    output: Dict[str, Any] = field(
        default_factory=lambda: {
            "format": "markdown",
            "include_code_snippets": True,
            "max_description_length": 500,
            "group_by_feature": True,
        }
    )

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AutodocConfig":
        """Load configuration from file or defaults."""
        config_data = {}

        # Look for config file
        if config_path and config_path.exists():
            config_file = config_path
        else:
            # Search for config in common locations
            for filename in [".autodoc.yml", ".autodoc.yaml", "autodoc.yml", "autodoc.yaml"]:
                config_file = Path.cwd() / filename
                if config_file.exists():
                    break
            else:
                # No config file found, use defaults
                return cls()

        # Load config file
        try:
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Error loading config file {config_file}: {e}")
            return cls()

        # Parse config data
        config = cls()

        # LLM settings
        if "llm" in config_data:
            llm_data = config_data["llm"]
            config.llm = LLMConfig(
                provider=llm_data.get("provider", "openai"),
                model=llm_data.get("model", "gpt-4o-mini"),
                api_key=llm_data.get("api_key"),
                base_url=llm_data.get("base_url"),
                temperature=llm_data.get("temperature", 0.3),
                max_tokens=llm_data.get("max_tokens", 500),
            )

        # Enrichment settings
        if "enrichment" in config_data:
            enr_data = config_data["enrichment"]
            config.enrichment = EnrichmentConfig(
                enabled=enr_data.get("enabled", True),
                batch_size=enr_data.get("batch_size", 10),
                cache_enrichments=enr_data.get("cache_enrichments", True),
                include_examples=enr_data.get("include_examples", True),
                analyze_complexity=enr_data.get("analyze_complexity", True),
                detect_patterns=enr_data.get("detect_patterns", True),
                languages=enr_data.get("languages", ["python", "typescript"]),
            )

        # Other settings
        if "embeddings" in config_data:
            config.embeddings.update(config_data["embeddings"])
        if "graph" in config_data:
            config.graph.update(config_data["graph"])
        if "analysis" in config_data:
            config.analysis.update(config_data["analysis"])
        if "output" in config_data:
            config.output.update(config_data["output"])

        return config

    def save(self, config_path: Optional[Path] = None):
        """Save configuration to file."""
        if not config_path:
            config_path = Path.cwd() / ".autodoc.yml"

        config_data = {
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
            },
            "enrichment": {
                "enabled": self.enrichment.enabled,
                "batch_size": self.enrichment.batch_size,
                "cache_enrichments": self.enrichment.cache_enrichments,
                "include_examples": self.enrichment.include_examples,
                "analyze_complexity": self.enrichment.analyze_complexity,
                "detect_patterns": self.enrichment.detect_patterns,
                "languages": self.enrichment.languages,
            },
            "embeddings": self.embeddings,
            "graph": self.graph,
            "analysis": self.analysis,
            "output": self.output,
        }

        # Don't save API keys
        if self.llm.api_key:
            config_data["llm"]["api_key"] = "# Set via environment variable or add here"
        if self.llm.base_url:
            config_data["llm"]["base_url"] = self.llm.base_url

        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
