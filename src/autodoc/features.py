#!/usr/bin/env python3
"""
Auto-feature discovery using Neo4j Graph Data Science.
Detects code clusters using Louvain community detection and names them semantically using LLM.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import Driver
from neo4j.exceptions import ClientError, DatabaseError

log = logging.getLogger(__name__)

FEATURES_CACHE_FILE = ".autodoc/features_cache.json"
FEATURES_CACHE_VERSION = 1
DEFAULT_MAX_DEGREE = 50

# Patterns to exclude from feature detection (external libraries, build artifacts)
EXCLUDED_PATH_PATTERNS = [
    "node_modules",
    "site-packages",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".tox",
    ".eggs",
    "coverage",
    ".next",
    ".nuxt",
    ".output",
    "vendor",
    "third_party",
    "external_libs",
]


@dataclass
class SampleFile:
    """A file with optional summary for context-rich naming."""

    path: str
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "summary": self.summary}


@dataclass
class DetectedFeature:
    """A detected code cluster/feature."""

    id: int
    files: List[str] = field(default_factory=list)
    file_count: int = 0
    sample_files: List[SampleFile] = field(default_factory=list)
    name: Optional[str] = None
    display_name: Optional[str] = None
    reasoning: Optional[str] = None
    named_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "files": self.files,
            "file_count": self.file_count,
            "sample_files": [f.to_dict() for f in self.sample_files],
            "name": self.name,
            "display_name": self.display_name,
            "reasoning": self.reasoning,
            "named_at": self.named_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectedFeature":
        sample_files = [
            SampleFile(path=f["path"], summary=f.get("summary"))
            for f in data.get("sample_files", [])
        ]
        return cls(
            id=data["id"],
            files=data.get("files", []),
            file_count=data.get("file_count", 0),
            sample_files=sample_files,
            name=data.get("name"),
            display_name=data.get("display_name"),
            reasoning=data.get("reasoning"),
            named_at=data.get("named_at"),
        )


@dataclass
class FeatureDetectionResult:
    """Result of running community detection."""

    community_count: int
    modularity: float
    ran_levels: int = 0
    graph_hash: str = ""
    max_degree_threshold: int = DEFAULT_MAX_DEGREE
    features: Dict[int, DetectedFeature] = field(default_factory=dict)
    detected_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "community_count": self.community_count,
            "modularity": self.modularity,
            "ran_levels": self.ran_levels,
            "graph_hash": self.graph_hash,
            "max_degree_threshold": self.max_degree_threshold,
            "features": {str(k): v.to_dict() for k, v in self.features.items()},
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureDetectionResult":
        features = {}
        for fid, fdata in data.get("features", {}).items():
            features[int(fid)] = DetectedFeature.from_dict(fdata)
        return cls(
            community_count=data.get("community_count", 0),
            modularity=data.get("modularity", 0.0),
            ran_levels=data.get("ran_levels", 0),
            graph_hash=data.get("graph_hash", ""),
            max_degree_threshold=data.get("max_degree_threshold", DEFAULT_MAX_DEGREE),
            features=features,
            detected_at=data.get("detected_at"),
        )


class FeatureDetector:
    """Detects code features using Neo4j GDS Louvain community detection."""

    def __init__(self, driver: Driver):
        self.driver = driver
        self._gds_available: Optional[bool] = None

    def check_gds_available(self) -> bool:
        """Check if GDS library is installed in Neo4j."""
        if self._gds_available is not None:
            return self._gds_available

        try:
            with self.driver.session() as session:
                result = session.run("RETURN gds.version() AS version")
                record = result.single()
                if record:
                    log.info(f"GDS version: {record['version']}")
                    self._gds_available = True
                    return True
        except (ClientError, DatabaseError) as e:
            log.warning(f"GDS not available: {e}")
            self._gds_available = False

        return False

    def check_graph_exists(self) -> bool:
        """Check if the code graph has been built."""
        with self.driver.session() as session:
            result = session.run("MATCH (f:File) RETURN count(f) AS count")
            record = result.single()
            return record is not None and record["count"] > 0

    def compute_graph_hash(self) -> str:
        """Compute hash of graph state for cache invalidation."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (f:File) RETURN count(f) as file_count, max(f.path) as last_file"
            )
            record = result.single()
            if record:
                hash_input = f"{record['file_count']}:{record['last_file']}"
                return hashlib.md5(hash_input.encode()).hexdigest()
            return ""

    def detect_features(
        self, max_degree: int = DEFAULT_MAX_DEGREE, projection_name: str = "codebase"
    ) -> FeatureDetectionResult:
        """Run Louvain community detection on the code graph.

        Args:
            max_degree: Maximum connections a file can have to be included.
                        Files with more connections are considered "God Objects"
                        and are excluded from clustering.
            projection_name: Name for the GDS graph projection.

        Returns:
            FeatureDetectionResult with detected communities.
        """
        if not self.check_gds_available():
            raise RuntimeError(
                "Neo4j GDS library not installed. "
                "Install from: https://neo4j.com/docs/graph-data-science/current/installation/"
            )

        if not self.check_graph_exists():
            raise RuntimeError(
                "No code graph found. Run 'autodoc graph' first to build the graph."
            )

        graph_hash = self.compute_graph_hash()

        with self.driver.session() as session:
            # Step 1: Drop existing projection if it exists
            try:
                session.run(f"CALL gds.graph.drop('{projection_name}', false)")
                log.debug(f"Dropped existing projection '{projection_name}'")
            except (ClientError, DatabaseError):
                pass  # Graph didn't exist, that's fine

            # Step 2: Create Cypher-based projection excluding high-degree nodes
            # This filters out "God Objects" like logger, config, types files
            # Also excludes external libraries and build artifacts by path pattern
            # Neo4j 5 requires COUNT {} instead of deprecated size() for pattern expressions

            # Build path exclusion condition for Cypher
            path_exclusions = " AND ".join(
                [f"NOT f.path CONTAINS '{pattern}'" for pattern in EXCLUDED_PATH_PATTERNS]
            )

            node_query = f"""
            MATCH (f:File)
            WHERE COUNT {{ (f)--() }} < {max_degree}
              AND {path_exclusions}
            RETURN id(f) as id
            """

            # Build path exclusions for both source and target
            src_exclusions = " AND ".join(
                [f"NOT s.path CONTAINS '{pattern}'" for pattern in EXCLUDED_PATH_PATTERNS]
            )
            tgt_exclusions = " AND ".join(
                [f"NOT t.path CONTAINS '{pattern}'" for pattern in EXCLUDED_PATH_PATTERNS]
            )

            rel_query = f"""
            MATCH (s:File)-[:IMPORTS]-(t:File)
            WHERE COUNT {{ (s)--() }} < {max_degree} AND COUNT {{ (t)--() }} < {max_degree}
              AND {src_exclusions}
              AND {tgt_exclusions}
            RETURN id(s) as source, id(t) as target
            """

            try:
                proj_result = session.run(
                    """
                    CALL gds.graph.project.cypher(
                        $projection_name,
                        $node_query,
                        $rel_query
                    )
                    YIELD graphName, nodeCount, relationshipCount
                    RETURN graphName, nodeCount, relationshipCount
                    """,
                    projection_name=projection_name,
                    node_query=node_query,
                    rel_query=rel_query,
                )
                proj_record = proj_result.single()

                if not proj_record or proj_record["nodeCount"] == 0:
                    raise RuntimeError(
                        "Graph projection created but contains no nodes. "
                        "Try increasing --max-degree threshold."
                    )

                log.info(
                    f"Created projection with {proj_record['nodeCount']} nodes, "
                    f"{proj_record['relationshipCount']} relationships "
                    f"(filtered files with >{max_degree} connections)"
                )
            except (ClientError, DatabaseError) as e:
                raise RuntimeError(f"Failed to create graph projection: {e}")

            # Step 3: Run Louvain community detection
            try:
                louvain_result = session.run(
                    """
                    CALL gds.louvain.write(
                        $projection_name,
                        { writeProperty: 'featureId' }
                    )
                    YIELD communityCount, modularity, ranLevels
                    RETURN communityCount, modularity, ranLevels
                    """,
                    projection_name=projection_name,
                )
                louvain_record = louvain_result.single()

                community_count = louvain_record["communityCount"]
                modularity = louvain_record["modularity"]
                ran_levels = louvain_record["ranLevels"]

                log.info(
                    f"Detected {community_count} communities with modularity {modularity:.3f}"
                )
            except (ClientError, DatabaseError) as e:
                raise RuntimeError(f"Failed to run Louvain algorithm: {e}")

            # Step 4: Query detected features with context (excluding external libraries)
            features_result = session.run(
                f"""
                MATCH (f:File)
                WHERE f.featureId IS NOT NULL
                  AND {path_exclusions}
                WITH f.featureId AS id, collect(f) AS files
                RETURN
                    id,
                    size(files) as file_count,
                    [f IN files[0..10] | {{path: f.path, summary: f.summary}}] as sample_files,
                    [f IN files | f.path] as all_paths
                ORDER BY file_count DESC
                """
            )

            features = {}
            for record in features_result:
                feature_id = record["id"]
                sample_files = [
                    SampleFile(path=f["path"], summary=f.get("summary"))
                    for f in record["sample_files"]
                ]
                features[feature_id] = DetectedFeature(
                    id=feature_id,
                    files=record["all_paths"],
                    file_count=record["file_count"],
                    sample_files=sample_files,
                )

            # Step 5: Clean up projection
            try:
                session.run(f"CALL gds.graph.drop('{projection_name}')")
            except (ClientError, DatabaseError) as e:
                log.warning(f"Could not drop projection: {e}")

            return FeatureDetectionResult(
                community_count=community_count,
                modularity=modularity,
                ran_levels=ran_levels,
                graph_hash=graph_hash,
                max_degree_threshold=max_degree,
                features=features,
                detected_at=datetime.now().isoformat(),
            )

    def get_feature_files(self, feature_id: int) -> List[str]:
        """Get all files belonging to a specific feature (excluding external libraries)."""
        # Build path exclusion condition
        path_exclusions = " AND ".join(
            [f"NOT f.path CONTAINS '{pattern}'" for pattern in EXCLUDED_PATH_PATTERNS]
        )

        with self.driver.session() as session:
            result = session.run(
                f"""
                MATCH (f:File)
                WHERE f.featureId = $feature_id
                  AND {path_exclusions}
                RETURN f.path AS path
                ORDER BY f.path
                """,
                feature_id=feature_id,
            )
            return [record["path"] for record in result]


class FeaturesCache:
    """Cache for detected features with persistence."""

    def __init__(self, cache_file: str = FEATURES_CACHE_FILE):
        self.cache_file = Path(cache_file)

    def load(self) -> Optional[FeatureDetectionResult]:
        """Load cached features from disk."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file) as f:
                data = json.load(f)

            if data.get("version") != FEATURES_CACHE_VERSION:
                log.warning("Cache version mismatch, ignoring cache")
                return None

            return FeatureDetectionResult.from_dict(data)
        except Exception as e:
            log.error(f"Error loading features cache: {e}")
            return None

    def save(self, result: FeatureDetectionResult):
        """Save features to cache."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": FEATURES_CACHE_VERSION,
            **result.to_dict(),
        }

        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=2)

        log.info(f"Saved features cache to {self.cache_file}")

    def is_stale(self, current_hash: str) -> bool:
        """Check if cache is stale by comparing graph hash."""
        cached = self.load()
        if not cached:
            return True
        return cached.graph_hash != current_hash

    def update_feature_name(
        self,
        feature_id: int,
        name: str,
        display_name: str,
        reasoning: Optional[str] = None,
    ):
        """Update feature name in cache."""
        result = self.load()
        if not result:
            raise RuntimeError("No features cache found")

        if feature_id not in result.features:
            raise ValueError(f"Feature {feature_id} not found")

        feature = result.features[feature_id]
        feature.name = name
        feature.display_name = display_name
        feature.reasoning = reasoning
        feature.named_at = datetime.now().isoformat()

        self.save(result)


class FeatureNamer:
    """Names detected features using LLM."""

    def __init__(self, config):
        from .config import AutodocConfig

        self.config: AutodocConfig = config

    async def name_feature(
        self,
        feature: DetectedFeature,
        sample_size: int = 5,
    ) -> Optional[Dict[str, str]]:
        """Generate a semantic name for a detected feature.

        Args:
            feature: The detected feature to name.
            sample_size: Number of sample files to include in prompt.

        Returns:
            Dict with 'name', 'display_name', 'reasoning' or None on failure.
        """
        from .enrichment import LLMEnricher

        # Build context from sample files
        context_lines = []
        for i, sf in enumerate(feature.sample_files[:sample_size], 1):
            summary = sf.summary if sf.summary else "(no summary available)"
            context_lines.append(f"{i}. {sf.path} - {summary}")

        if not context_lines:
            # Fallback to just paths if no sample_files
            for i, path in enumerate(feature.files[:sample_size], 1):
                context_lines.append(f"{i}. {path}")

        context_text = "\n".join(context_lines)

        prompt = f"""Analyze this code cluster (Feature ID: {feature.id}, {feature.file_count} files).

Key Files & their Responsibilities:
{context_text}

Task: Name this feature based on its BUSINESS DOMAIN purpose.

Rules:
- NO generic names like "Utils", "Helpers", "Common", "Shared", "Core", "Base"
- Focus on WHAT the code does (e.g., "Checkout Flow", "User Onboarding", "Payment Processing")
- 2-4 words maximum

Respond in JSON:
{{
  "name": "feature-name-here",
  "display_name": "Feature Name Here",
  "reasoning": "Brief explanation of why this name fits"
}}"""

        try:
            async with LLMEnricher(self.config) as enricher:
                if self.config.llm.provider == "anthropic":
                    response = await enricher._call_anthropic(prompt)
                elif self.config.llm.provider == "openai":
                    response = await enricher._call_openai(prompt)
                elif self.config.llm.provider == "ollama":
                    response = await enricher._call_ollama(prompt)
                else:
                    log.warning(f"Unsupported LLM provider: {self.config.llm.provider}")
                    return None

            if response:
                return {
                    "name": response.get("name", f"feature-{feature.id}"),
                    "display_name": response.get(
                        "display_name", f"Feature {feature.id}"
                    ),
                    "reasoning": response.get("reasoning"),
                }
        except Exception as e:
            log.error(f"Error naming feature {feature.id}: {e}")

        return None

    async def name_all_features(
        self,
        result: FeatureDetectionResult,
        skip_named: bool = True,
    ) -> Dict[int, Dict[str, str]]:
        """Name all detected features.

        Args:
            result: Detection result with features.
            skip_named: Skip features that already have names.

        Returns:
            Dict mapping feature_id to naming result.
        """
        named = {}

        for feature_id, feature in result.features.items():
            if skip_named and feature.name:
                log.info(f"Skipping already named feature {feature_id}")
                continue

            if feature.file_count == 0:
                log.warning(f"Skipping empty feature {feature_id}")
                continue

            try:
                naming = await self.name_feature(feature)
                if naming:
                    named[feature_id] = naming
                    log.info(f"Named feature {feature_id}: {naming['name']}")
            except Exception as e:
                log.error(f"Failed to name feature {feature_id}: {e}")
                # Continue with other features

        return named
