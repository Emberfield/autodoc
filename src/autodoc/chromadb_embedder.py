#!/usr/bin/env python3
"""
ChromaDB-based embedding storage and search for autodoc.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

from .analyzer import CodeEntity
from .enrichment import EnrichmentCache


class ChromaDBEmbedder:
    """Handles embeddings and search using ChromaDB with local storage."""
    
    def __init__(
        self, 
        collection_name: str = "autodoc_embeddings",
        persist_directory: str = ".autodoc_chromadb",
        embedding_model: str = "all-MiniLM-L6-v2"  # Default local model
    ):
        """Initialize ChromaDB with local persistence."""
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.embedding_model = embedding_model
        
        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Use sentence transformers for local embeddings (no API needed)
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Autodoc code embeddings"}
            )
    
    def clear_collection(self):
        """Clear all embeddings from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Autodoc code embeddings"}
        )
    
    def generate_id(self, entity: CodeEntity) -> str:
        """Generate a unique ID for an entity."""
        key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def prepare_entity_text(
        self, 
        entity: CodeEntity, 
        enrichment_cache: Optional[EnrichmentCache] = None
    ) -> str:
        """Prepare entity text for embedding, using enrichment if available."""
        text = f"{entity.type} {entity.name}"
        
        # Use enriched description if available
        if enrichment_cache:
            cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
            enrichment = enrichment_cache.get_enrichment(cache_key)
            if enrichment and enrichment.get("description"):
                text += f": {enrichment['description']}"
                if enrichment.get("key_features"):
                    text += " Features: " + ", ".join(enrichment['key_features'])
                if enrichment.get("purpose"):
                    text += f" Purpose: {enrichment['purpose']}"
            elif entity.docstring:
                text += f": {entity.docstring}"
        elif entity.docstring:
            text += f": {entity.docstring}"
        
        # Add code snippet for better context
        if entity.code:
            # Truncate code if too long
            code_preview = entity.code[:500] + "..." if len(entity.code) > 500 else entity.code
            text += f"\nCode: {code_preview}"
        
        return text
    
    async def embed_entities(
        self, 
        entities: List[CodeEntity], 
        use_enrichment: bool = True,
        batch_size: int = 100
    ) -> int:
        """Embed a list of entities into ChromaDB."""
        if not entities:
            return 0
        
        # Load enrichment cache if requested
        enrichment_cache = None
        if use_enrichment:
            try:
                enrichment_cache = EnrichmentCache()
            except:
                pass
        
        embedded_count = 0
        
        # Process in batches
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            
            for entity in batch:
                entity_id = self.generate_id(entity)
                text = self.prepare_entity_text(entity, enrichment_cache)
                
                metadata = {
                    "type": entity.type,
                    "name": entity.name,
                    "file_path": entity.file_path,
                    "line_number": entity.line_number,
                    "has_docstring": bool(entity.docstring),
                    "is_internal": entity.is_internal,
                }
                
                # Add enrichment metadata if available
                if enrichment_cache:
                    cache_key = f"{entity.file_path}:{entity.name}:{entity.line_number}"
                    enrichment = enrichment_cache.get_enrichment(cache_key)
                    if enrichment:
                        metadata["is_enriched"] = True
                        if enrichment.get("complexity_notes"):
                            metadata["complexity_notes"] = enrichment["complexity_notes"]
                        if enrichment.get("design_patterns"):
                            metadata["design_patterns"] = ", ".join(enrichment["design_patterns"])
                
                ids.append(entity_id)
                documents.append(text)
                metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            embedded_count += len(batch)
        
        return embedded_count
    
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        filter_type: Optional[str] = None,
        filter_internal: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar entities using ChromaDB."""
        # Build where clause for filtering
        where = {}
        if filter_type:
            where["type"] = filter_type
        if filter_internal is not None:
            where["is_internal"] = filter_internal
        
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
            where=where if where else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                
                # Convert distance to similarity score (1 - normalized distance)
                # ChromaDB uses L2 distance by default
                similarity = 1.0 / (1.0 + distance)
                
                result = {
                    "entity": {
                        "type": metadata.get("type", "unknown"),
                        "name": metadata.get("name", "unknown"),
                        "file_path": metadata.get("file_path", ""),
                        "line_number": metadata.get("line_number", 0),
                        "is_enriched": metadata.get("is_enriched", False),
                    },
                    "similarity": similarity,
                    "document": results['documents'][0][i],
                    "metadata": metadata
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the embeddings collection."""
        count = self.collection.count()
        
        # Get sample to check enrichment status
        sample = self.collection.get(limit=100, include=["metadatas"])
        enriched_count = sum(1 for m in sample['metadatas'] if m.get('is_enriched', False))
        
        return {
            "total_embeddings": count,
            "collection_name": self.collection_name,
            "persist_directory": str(self.persist_directory),
            "embedding_model": self.embedding_model,
            "sample_enriched_ratio": enriched_count / len(sample['metadatas']) if sample['metadatas'] else 0
        }
    
    def export_to_json(self, output_path: str = "chromadb_export.json"):
        """Export all embeddings to JSON for backup or migration."""
        all_data = self.collection.get(include=["embeddings", "documents", "metadatas"])
        
        export_data = {
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "count": len(all_data['ids']),
            "data": []
        }
        
        for i, doc_id in enumerate(all_data['ids']):
            export_data["data"].append({
                "id": doc_id,
                "document": all_data['documents'][i],
                "metadata": all_data['metadatas'][i],
                "embedding": all_data['embeddings'][i] if 'embeddings' in all_data else None
            })
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return output_path