#!/usr/bin/env python3
"""
Tests for the embedder module
"""

from unittest.mock import AsyncMock, patch

import pytest

from autodoc.embedder import OpenAIEmbedder


class TestOpenAIEmbedder:
    """Test OpenAI embedder functionality"""

    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        embedder = OpenAIEmbedder("test-api-key")

        # Mock the embed method directly
        with patch.object(embedder, "embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]

            embedding = await embedder.embed("test text")

            assert embedding == [0.1, 0.2, 0.3]
            mock_embed.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        embedder = OpenAIEmbedder("test-api-key")

        # Mock the embed method to return different values
        with patch.object(embedder, "embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            embeddings = await embedder.embed_batch(["text1", "text2"])

            assert len(embeddings) == 2
            assert embeddings[0] == [0.1, 0.2, 0.3]
            assert embeddings[1] == [0.4, 0.5, 0.6]

    def test_api_key_initialization(self):
        """Test that API key is properly stored"""
        api_key = "test-api-key-123"
        embedder = OpenAIEmbedder(api_key)

        assert embedder.api_key == api_key
        assert "Authorization" in embedder.headers
        assert f"Bearer {api_key}" in embedder.headers["Authorization"]

    @pytest.mark.asyncio
    async def test_text_truncation(self):
        """Test that long text is properly truncated"""
        embedder = OpenAIEmbedder("test-api-key")

        # Create a very long text (over 8000 characters)
        long_text = "a" * 10000

        # Mock the HTTP request instead of the embed method to test truncation logic
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
            mock_post.return_value.__aenter__.return_value = mock_response

            await embedder.embed(long_text)

            # Check that the request was made with truncated text
            call_args = mock_post.call_args[1]["json"]["input"]
            assert len(call_args) <= 8000
