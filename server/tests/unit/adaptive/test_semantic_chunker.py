"""
Unit tests for the Semantic Chunker component.

Tests discourse analysis, content type detection, and semantic chunking algorithms.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.adaptive.semantic_chunker import (
    SemanticChunker, 
    ChunkingResult, 
    ContentType, 
    DiscourseFeatures,
    chunk_text_semantically
)


class TestSemanticChunker:
    """Test suite for SemanticChunker class."""
    
    @pytest.fixture
    def chunker(self):
        """Create a semantic chunker with mocked embeddings."""
        with patch('app.adaptive.semantic_chunker.SentenceTransformer') as mock_transformer:
            mock_embedder = Mock()
            mock_embedder.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
            mock_transformer.return_value = mock_embedder
            
            chunker = SemanticChunker(min_chunk_size=100, max_chunk_size=400)
            chunker.embedder = mock_embedder
            return chunker
    
    @pytest.fixture
    def sample_texts(self):
        """Sample texts for different content types."""
        return {
            'emotional': "I can't believe this happened! It's absolutely amazing how life works sometimes. I'm so grateful for this opportunity, but also terrified about what comes next. This is incredible!",
            'technical': "The API endpoint returns a JSON response with the following schema. The authentication mechanism uses OAuth 2.0 with bearer tokens. You need to configure the client_id and client_secret parameters.",
            'conversational': "Hey, how are you? Did you see the game last night? Pretty crazy stuff happening.",
            'formal': "The quarterly financial results demonstrate a significant improvement in operational efficiency. The board of directors has approved the proposed merger with subsidiary companies.",
            'long_emotional': "I've been thinking about this for weeks now, and I just can't shake the feeling that something amazing is about to happen. The way everything has been falling into place lately feels almost too good to be true. Yesterday, when I got that phone call, I literally started crying with joy. I never imagined that all those years of hard work would finally pay off like this. It's overwhelming in the best possible way. I keep pinching myself to make sure I'm not dreaming. This is exactly what I've been working towards my entire career, and now it's actually happening!"
        }
    
    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        result = await chunker.chunk_text("")
        
        assert result.chunks == []
        assert result.chunk_boundaries == []
        assert result.coherence_score == 0.0
        assert "error" in result.metadata
    
    @pytest.mark.asyncio
    async def test_chunk_short_text(self, chunker, sample_texts):
        """Test chunking text shorter than max chunk size."""
        text = sample_texts['conversational']
        result = await chunker.chunk_text(text)
        
        assert len(result.chunks) == 1
        assert result.chunks[0] == text
        assert result.content_type == ContentType.CONVERSATIONAL
        assert result.coherence_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_content_type_detection(self, chunker, sample_texts):
        """Test content type classification."""
        # Test emotional content
        result = await chunker.chunk_text(sample_texts['emotional'])
        assert result.content_type == ContentType.EMOTIONAL
        
        # Test technical content
        result = await chunker.chunk_text(sample_texts['technical'])
        assert result.content_type == ContentType.TECHNICAL
        
        # Test conversational content
        result = await chunker.chunk_text(sample_texts['conversational'])
        assert result.content_type == ContentType.CONVERSATIONAL
        
        # Test formal content
        result = await chunker.chunk_text(sample_texts['formal'])
        assert result.content_type in [ContentType.FORMAL, ContentType.NARRATIVE]
    
    @pytest.mark.asyncio
    async def test_emotional_content_chunking(self, chunker, sample_texts):
        """Test chunking strategy for emotional content."""
        text = sample_texts['long_emotional']
        result = await chunker.chunk_text(text)
        
        assert result.content_type == ContentType.EMOTIONAL
        assert len(result.chunks) >= 1
        assert all(len(chunk) <= chunker.max_chunk_size for chunk in result.chunks)
        assert all(len(chunk) >= chunker.min_chunk_size or chunk == result.chunks[-1] for chunk in result.chunks)
    
    @pytest.mark.asyncio
    async def test_technical_content_chunking(self, chunker, sample_texts):
        """Test chunking strategy for technical content."""
        # Create longer technical text
        technical_text = sample_texts['technical'] * 3
        result = await chunker.chunk_text(technical_text)
        
        assert result.content_type == ContentType.TECHNICAL
        assert len(result.chunks) >= 1
        # Technical content should preserve structure
        assert all(len(chunk) <= chunker.max_chunk_size for chunk in result.chunks)
    
    def test_discourse_analysis(self, chunker):
        """Test discourse feature analysis."""
        text = "This is amazing! I love it. However, there are some technical issues. The API endpoint doesn't work properly."
        features = chunker._analyze_discourse(text, 'en')
        
        assert isinstance(features, DiscourseFeatures)
        assert features.sentence_count > 0
        assert features.avg_sentence_length > 0
        assert features.punctuation_density > 0
        assert features.emotion_indicators > 0  # "!" and "love"
        assert features.technical_terms > 0     # "API"
    
    def test_content_type_classification(self, chunker):
        """Test content type classification logic."""
        # High emotion indicators
        emotional_features = DiscourseFeatures(
            sentence_count=3,
            avg_sentence_length=15,
            punctuation_density=0.1,
            connector_count=1,
            emotion_indicators=5,  # High emotion
            technical_terms=0,
            coreference_chains=[]
        )
        content_type = chunker._classify_content_type("test", emotional_features, 'en')
        assert content_type == ContentType.EMOTIONAL
        
        # High technical terms
        technical_features = DiscourseFeatures(
            sentence_count=2,
            avg_sentence_length=30,
            punctuation_density=0.05,
            connector_count=1,
            emotion_indicators=0,
            technical_terms=5,  # High technical
            coreference_chains=[]
        )
        content_type = chunker._classify_content_type("test", technical_features, 'en')
        assert content_type == ContentType.TECHNICAL
        
        # Short sentences (conversational)
        conversational_features = DiscourseFeatures(
            sentence_count=3,
            avg_sentence_length=10,  # Short sentences
            punctuation_density=0.05,
            connector_count=0,
            emotion_indicators=1,
            technical_terms=0,
            coreference_chains=[]
        )
        content_type = chunker._classify_content_type("short text", conversational_features, 'en')
        assert content_type == ContentType.CONVERSATIONAL
    
    @pytest.mark.asyncio
    async def test_coherence_calculation(self, chunker):
        """Test coherence score calculation."""
        # Mock embedder for coherence test
        mock_embeddings = np.array([[0.8, 0.2], [0.9, 0.1], [0.7, 0.3]])
        chunker.embedder.encode.return_value = mock_embeddings
        
        chunks = ["First chunk", "Second chunk", "Third chunk"]
        coherence = await chunker._calculate_coherence_score(chunks)
        
        assert 0.0 <= coherence <= 1.0
        assert coherence > 0.5  # High similarity should give good coherence
    
    @pytest.mark.asyncio
    async def test_coherence_single_chunk(self, chunker):
        """Test coherence for single chunk."""
        coherence = await chunker._calculate_coherence_score(["Single chunk"])
        assert coherence == 1.0  # Single chunk is perfectly coherent
    
    @pytest.mark.asyncio
    async def test_coherence_no_embedder(self, chunker):
        """Test coherence calculation when embedder is unavailable."""
        chunker.embedder = None
        coherence = await chunker._calculate_coherence_score(["chunk1", "chunk2"])
        assert coherence == 0.5  # Neutral score
    
    def test_optimal_size_estimation(self, chunker):
        """Test optimal chunk size estimation."""
        # Emotional content should get larger chunks
        emotional_features = DiscourseFeatures(
            sentence_count=5,
            avg_sentence_length=20,
            punctuation_density=0.1,
            connector_count=2,
            emotion_indicators=5,
            technical_terms=0,
            coreference_chains=[]
        )
        size = chunker._estimate_optimal_size("test", ContentType.EMOTIONAL, emotional_features)
        assert size >= 350  # Should be larger for emotional
        
        # Technical content should get smaller chunks
        technical_features = DiscourseFeatures(
            sentence_count=3,
            avg_sentence_length=25,
            punctuation_density=0.05,
            connector_count=1,
            emotion_indicators=0,
            technical_terms=3,
            coreference_chains=[]
        )
        size = chunker._estimate_optimal_size("test", ContentType.TECHNICAL, technical_features)
        assert size <= 300  # Should be smaller for technical
    
    def test_coreference_detection(self, chunker):
        """Test simple coreference detection."""
        sentences = [
            "John went to the store.",
            "He bought some milk.",
            "This was expensive."
        ]
        chains = chunker._detect_coreference_chains(sentences)
        
        # Should detect pronouns linking to previous sentences
        assert len(chains) > 0
        assert any(1 in chain for chain in chains)  # "He" in sentence 1
        assert any(2 in chain for chain in chains)  # "This" in sentence 2
    
    @pytest.mark.asyncio
    async def test_similarity_based_chunking(self, chunker):
        """Test semantic similarity-based chunking."""
        # Mock high similarity between first two sentences, low with third
        embeddings = np.array([
            [1.0, 0.0, 0.0],  # First sentence
            [0.9, 0.1, 0.0],  # Similar to first
            [0.0, 0.0, 1.0]   # Different from first two
        ])
        chunker.embedder.encode.return_value = embeddings
        
        sentences = [
            "The weather is nice today.",
            "It's a beautiful sunny day.",
            "The technical documentation explains the API."
        ]
        text = " ".join(sentences)
        
        chunks, boundaries = await chunker._chunk_by_similarity(sentences, text)
        
        # Should group similar sentences together
        assert len(chunks) >= 1
        assert len(boundaries) == len(chunks)
    
    @pytest.mark.asyncio
    async def test_size_based_chunking_fallback(self, chunker):
        """Test fallback to size-based chunking."""
        sentences = ["Short sentence."] * 10
        text = " ".join(sentences)
        
        chunks, boundaries = await chunker._chunk_by_size(sentences, text)
        
        assert len(chunks) >= 1
        assert all(len(chunk) <= chunker.max_chunk_size for chunk in chunks)
        assert len(boundaries) == len(chunks)
    
    @pytest.mark.asyncio
    async def test_chunk_boundaries(self, chunker, sample_texts):
        """Test chunk boundary calculation."""
        result = await chunker.chunk_text(sample_texts['long_emotional'])
        
        assert len(result.chunk_boundaries) == len(result.chunks)
        
        # Verify boundaries don't overlap
        for i in range(len(result.chunk_boundaries) - 1):
            start1, end1 = result.chunk_boundaries[i]
            start2, end2 = result.chunk_boundaries[i + 1]
            assert end1 <= start2  # No overlap
            assert start1 >= 0     # Valid start
            assert end1 <= len(sample_texts['long_emotional'])  # Valid end


class TestChunkTextSemanically:
    """Test the convenience function."""
    
    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """Test the chunk_text_semantically convenience function."""
        with patch('app.adaptive.semantic_chunker.SemanticChunker') as mock_chunker_class:
            mock_chunker = Mock()
            mock_result = ChunkingResult(
                chunks=["test chunk"],
                chunk_boundaries=[(0, 10)],
                content_type=ContentType.CONVERSATIONAL,
                coherence_score=0.8,
                optimal_size_estimate=300,
                metadata={}
            )
            mock_chunker.chunk_text = AsyncMock(return_value=mock_result)
            mock_chunker_class.return_value = mock_chunker
            
            result = await chunk_text_semantically("test text", "en", "ru")
            
            assert result == mock_result
            mock_chunker.chunk_text.assert_called_once_with("test text", "en", "ru")
    
    @pytest.mark.asyncio
    async def test_convenience_function_with_chunker(self):
        """Test convenience function with provided chunker."""
        mock_chunker = Mock()
        mock_result = ChunkingResult(
            chunks=["test chunk"],
            chunk_boundaries=[(0, 10)],
            content_type=ContentType.CONVERSATIONAL,
            coherence_score=0.8,
            optimal_size_estimate=300,
            metadata={}
        )
        mock_chunker.chunk_text = AsyncMock(return_value=mock_result)
        
        result = await chunk_text_semantically("test text", "en", "ru", chunker=mock_chunker)
        
        assert result == mock_result
        mock_chunker.chunk_text.assert_called_once_with("test text", "en", "ru")


class TestSemanticChunkerEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def chunker_no_embedder(self):
        """Create chunker without embedder for testing fallbacks."""
        with patch('app.adaptive.semantic_chunker.SentenceTransformer') as mock_transformer:
            mock_transformer.side_effect = Exception("Embedder failed")
            chunker = SemanticChunker()
            assert chunker.embedder is None
            return chunker
    
    @pytest.mark.asyncio
    async def test_chunker_without_embedder(self, chunker_no_embedder):
        """Test chunker operation when embedder is unavailable."""
        text = "This is a test. It should still work without embeddings."
        result = await chunker_no_embedder.chunk_text(text)
        
        assert len(result.chunks) >= 1
        assert result.coherence_score == 0.5  # Neutral score
        assert result.content_type in ContentType  # Should still classify
    
    @pytest.mark.asyncio
    async def test_very_long_text(self, chunker_no_embedder):
        """Test handling of very long text."""
        long_text = "This is a sentence. " * 200  # Very long text
        result = await chunker_no_embedder.chunk_text(long_text)
        
        assert len(result.chunks) > 1  # Should be split
        assert all(len(chunk) <= chunker_no_embedder.max_chunk_size for chunk in result.chunks)
        assert sum(len(chunk) for chunk in result.chunks) <= len(long_text) + len(result.chunks) - 1
    
    @pytest.mark.asyncio
    async def test_single_word(self, chunker_no_embedder):
        """Test single word input."""
        result = await chunker_no_embedder.chunk_text("Hello")
        
        assert len(result.chunks) == 1
        assert result.chunks[0] == "Hello"
        assert result.coherence_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_special_characters(self, chunker_no_embedder):
        """Test text with special characters and emojis."""
        text = "Hello! 😊 This is amazing! ❤️ Technical stuff: API endpoint /v1/translate?param=value"
        result = await chunker_no_embedder.chunk_text(text)
        
        assert len(result.chunks) >= 1
        assert result.content_type in ContentType
        assert "😊" in "".join(result.chunks)  # Emojis preserved
    
    def test_edge_case_discourse_features(self, chunker_no_embedder):
        """Test discourse analysis with edge cases."""
        # Empty text
        features = chunker_no_embedder._analyze_discourse("", 'en')
        assert features.sentence_count == 0
        assert features.avg_sentence_length == 0
        
        # Single character
        features = chunker_no_embedder._analyze_discourse(".", 'en')
        assert features.sentence_count >= 0
        assert features.punctuation_density > 0
        
        # No punctuation
        features = chunker_no_embedder._analyze_discourse("hello world", 'en')
        assert features.sentence_count >= 0
        assert features.punctuation_density == 0