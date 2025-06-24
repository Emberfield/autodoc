"""
OpenAI embedding functionality for semantic search.
"""

from typing import List

import aiohttp


class OpenAIEmbedder:
    """Handles embedding generation using OpenAI's text-embedding models."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        async with aiohttp.ClientSession() as session:
            data = {"input": text[:8000], "model": "text-embedding-3-small"}
            async with session.post(
                "https://api.openai.com/v1/embeddings", headers=self.headers, json=data
            ) as response:
                result = await response.json()
                return result["data"][0]["embedding"]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings
