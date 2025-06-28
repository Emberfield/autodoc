#!/usr/bin/env python3
"""
LLM-powered code enrichment for autodoc.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)

from .analyzer import CodeEntity
from .config import AutodocConfig


@dataclass
class EnrichedEntity:
    """An enriched code entity with LLM-generated descriptions."""

    entity: CodeEntity
    description: str
    purpose: str
    key_features: List[str]
    complexity_notes: Optional[str] = None
    usage_examples: Optional[List[str]] = None
    design_patterns: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None


class LLMEnricher:
    """Enriches code entities with LLM-generated descriptions and analysis."""

    def __init__(self, config: AutodocConfig):
        self.config = config
        self.llm_config = config.llm
        self.enrichment_config = config.enrichment
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def enrich_entities(
        self, entities: List[CodeEntity], context: Optional[Dict[str, Any]] = None
    ) -> List[EnrichedEntity]:
        """Enrich a list of code entities with LLM analysis."""
        if not self.enrichment_config.enabled:
            return []

        api_key = self.llm_config.get_api_key()
        if not api_key:
            log.warning(
                f"No API key found for {self.llm_config.provider}. Skipping enrichment. "
                f"To generate enrichments, set {self.llm_config.provider.upper()}_API_KEY environment variable"
            )
            return []

        enriched = []

        # Process in batches
        batch_size = self.enrichment_config.batch_size
        for i in range(0, len(entities), batch_size):
            batch = entities[i : i + batch_size]
            batch_enriched = await self._enrich_batch(batch, context)
            enriched.extend(batch_enriched)

        return enriched

    async def _enrich_batch(
        self, entities: List[CodeEntity], context: Optional[Dict[str, Any]] = None
    ) -> List[EnrichedEntity]:
        """Enrich a batch of entities."""
        enriched = []

        for entity in entities:
            try:
                enriched_entity = await self._enrich_single(entity, context)
                if enriched_entity:
                    enriched.append(enriched_entity)
            except Exception as e:
                log.error(f"Error enriching {entity.name}: {e}")

        return enriched

    async def _enrich_single(
        self, entity: CodeEntity, context: Optional[Dict[str, Any]] = None
    ) -> Optional[EnrichedEntity]:
        """Enrich a single entity with LLM analysis."""
        prompt = self._build_enrichment_prompt(entity, context)

        if self.llm_config.provider == "openai":
            response = await self._call_openai(prompt)
        elif self.llm_config.provider == "anthropic":
            response = await self._call_anthropic(prompt)
        elif self.llm_config.provider == "ollama":
            response = await self._call_ollama(prompt)
        else:
            log.warning(f"Unsupported LLM provider: {self.llm_config.provider}")
            return None

        if response:
            return self._parse_enrichment_response(entity, response)

        return None

    def _build_enrichment_prompt(
        self, entity: CodeEntity, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a prompt for enriching a code entity."""
        entity_type = entity.type

        prompt = f"""Analyze this {entity_type} and provide a detailed description.

Name: {entity.name}
Type: {entity_type}
File: {entity.file_path}
"""

        if entity.docstring:
            prompt += f"\nExisting docstring: {entity.docstring}\n"

        if entity.code:
            prompt += f"\nCode:\n```python\n{entity.code}\n```\n"

        prompt += """
Please provide:
1. A clear, concise description of what this {entity_type} does (2-3 sentences)
2. The primary purpose or responsibility
3. Key features or capabilities (as a list)
"""

        if self.enrichment_config.analyze_complexity:
            prompt += "4. Any complexity or performance considerations\n"

        if self.enrichment_config.include_examples:
            prompt += "5. 1-2 usage examples (if applicable)\n"

        if self.enrichment_config.detect_patterns:
            prompt += "6. Any design patterns used\n"

        prompt += "\nProvide the response in JSON format with keys: description, purpose, key_features, complexity_notes, usage_examples, design_patterns"

        return prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(aiohttp.ClientError),
        reraise=True,
    )
    async def _call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI API for enrichment."""
        if not self._session:
            raise RuntimeError("Session not initialized")

        api_key = self.llm_config.get_api_key()
        url = self.llm_config.base_url or "https://api.openai.com/v1/chat/completions"

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        data = {
            "model": self.llm_config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a code analysis expert. Provide clear, technical descriptions of code functionality.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            async with self._session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content)
                else:
                    error = await resp.text()
                    log.error(f"OpenAI API error: {error}")
                    return None
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            log.error(f"Error calling OpenAI or parsing response: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(aiohttp.ClientError),
        reraise=True,
    )
    async def _call_anthropic(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Anthropic API for enrichment."""
        if not self._session:
            raise RuntimeError("Session not initialized")

        api_key = self.llm_config.get_api_key()
        url = self.llm_config.base_url or "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.llm_config.model or "claude-3-haiku-20240307",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.llm_config.temperature,
            "max_tokens": self.llm_config.max_tokens,
            "system": "You are a code analysis expert. Provide clear, technical descriptions of code functionality. Always respond with valid JSON.",
        }

        try:
            async with self._session.post(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result["content"][0]["text"]
                    return json.loads(content)
                else:
                    error = await resp.text()
                    log.error(f"Anthropic API error: {error}")
                    return None
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            log.error(f"Error calling Anthropic or parsing response: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(aiohttp.ClientError),
        reraise=True,
    )
    async def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Ollama API for enrichment."""
        if not self._session:
            raise RuntimeError("Session not initialized")

        url = self.llm_config.base_url or "http://localhost:11434/api/generate"

        data = {
            "model": self.llm_config.model or "llama2",
            "prompt": prompt + "\n\nRespond only with valid JSON.",
            "temperature": self.llm_config.temperature,
            "stream": False,
        }

        try:
            async with self._session.post(url, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    response = result.get("response", "")
                    # Extract JSON from response
                    import re

                    json_match = re.search(r"\{.*\}", response, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    log.error(f"Ollama API: No JSON found in response: {response}")
                    return None
                else:
                    error = await resp.text()
                    log.error(f"Ollama API error: {error}")
                    return None
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            log.error(f"Error calling Ollama or parsing response: {e}")
            return None

    def _parse_enrichment_response(
        self, entity: CodeEntity, response: Dict[str, Any]
    ) -> EnrichedEntity:
        """Parse LLM response into an EnrichedEntity."""
        return EnrichedEntity(
            entity=entity,
            description=response.get("description", "No description available"),
            purpose=response.get("purpose", ""),
            key_features=response.get("key_features", []),
            complexity_notes=response.get("complexity_notes"),
            usage_examples=response.get("usage_examples"),
            design_patterns=response.get("design_patterns"),
            dependencies=response.get("dependencies"),
        )


class EnrichmentCache:
    """Cache for enriched entities."""

    def __init__(self, cache_file: str = "autodoc_enrichment_cache.json"):
        self.cache_file = cache_file
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from file."""
        try:
            with open(self.cache_file, "r") as f:
                self._cache = json.load(f)
        except FileNotFoundError:
            self._cache = {}
        except Exception as e:
            log.error(f"Error loading enrichment cache: {e}")
            self._cache = {}

    def save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            log.error(f"Error saving enrichment cache: {e}")

    def get_enrichment(self, entity_key: str) -> Optional[Dict[str, Any]]:
        """Get cached enrichment for an entity."""
        return self._cache.get(entity_key)

    def set_enrichment(self, entity_key: str, enrichment: Dict[str, Any]):
        """Cache enrichment for an entity."""
        self._cache[entity_key] = enrichment

    def clear(self):
        """Clear the cache."""
        self._cache = {}
        self.save_cache()
