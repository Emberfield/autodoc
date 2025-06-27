# enrichment - Module Enrichment

**File:** `src/autodoc/enrichment.py`
**Last Updated:** 2025-06-27T07:47:21.517525
**Total Entities:** 20
**Functions:** 17
**Classes:** 3

## Module Entities

*No enrichments available yet. Run `autodoc enrich` to add detailed descriptions.*

### Functions

#### `__aenter__` (line 38)

#### `__aexit__` (line 42)

#### `__init__` (line 32)

#### `__init__` (line 284)

#### `_build_enrichment_prompt` (line 115)
> Build a prompt for enriching a code entity.

#### `_call_anthropic` (line 194)
> Call Anthropic API for enrichment.

#### `_call_ollama` (line 230)
> Call Ollama API for enrichment.

#### `_call_openai` (line 156)
> Call OpenAI API for enrichment.

#### `_enrich_batch` (line 74)
> Enrich a batch of entities.

#### `_enrich_single` (line 92)
> Enrich a single entity with LLM analysis.

#### `_load_cache` (line 289)
> Load cache from file.

#### `_parse_enrichment_response` (line 263)
> Parse LLM response into an EnrichedEntity.

#### `clear` (line 316)
> Clear the cache.

#### `enrich_entities` (line 46)
> Enrich a list of code entities with LLM analysis.

#### `get_enrichment` (line 308)
> Get cached enrichment for an entity.

#### `save_cache` (line 300)
> Save cache to file.

#### `set_enrichment` (line 312)
> Cache enrichment for an entity.

### Classes

#### `EnrichedEntity` (line 17)
> An enriched code entity with LLM-generated descriptions.

#### `EnrichmentCache` (line 281)
> Cache for enriched entities.

#### `LLMEnricher` (line 29)
> Enriches code entities with LLM-generated descriptions and analysis.
