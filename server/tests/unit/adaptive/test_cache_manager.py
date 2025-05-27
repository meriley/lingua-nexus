"""
Unit tests for the Intelligent Cache Manager.

Tests multi-level caching, Redis integration, and similarity matching.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np

from app.adaptive.cache_manager import (
    IntelligentCacheManager,
    CacheKey,
    CacheEntry,
    CacheStatistics,
    create_cache_manager
)
from app.adaptive.quality_assessment import QualityMetrics, QualityDimension
from app.adaptive.semantic_chunker import ChunkingResult, ContentType


class TestCacheKey:
    """Test CacheKey data class."""
    
    def test_cache_key_creation(self):
        """Test CacheKey creation and attributes."""
        key = CacheKey(
            text_hash="abc123",
            source_lang="en",
            target_lang="fr",
            chunk_size=300,
            content_type="emotional",
            optimization_level="optimized"
        )
        
        assert key.text_hash == "abc123"
        assert key.source_lang == "en"
        assert key.target_lang == "fr"
        assert key.chunk_size == 300
        assert key.content_type == "emotional"
        assert key.optimization_level == "optimized"
    
    def test_cache_key_defaults(self):
        """Test CacheKey with default values."""
        key = CacheKey(
            text_hash="def456",
            source_lang="ru",
            target_lang="en"
        )
        
        assert key.text_hash == "def456"
        assert key.source_lang == "ru"
        assert key.target_lang == "en"
        assert key.chunk_size is None
        assert key.content_type is None
        assert key.optimization_level == "semantic"


class TestCacheEntry:
    """Test CacheEntry data class."""
    
    def test_cache_entry_creation(self):
        """Test CacheEntry creation and attributes."""
        cache_key = CacheKey("hash123", "en", "fr")
        quality_metrics = Mock()
        chunking_result = Mock()
        
        entry = CacheEntry(
            key=cache_key,
            translation="test translation",
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            timestamp=1234567890,
            access_count=5,
            hit_count=3,
            optimization_time=2.5
        )
        
        assert entry.key == cache_key
        assert entry.translation == "test translation"
        assert entry.quality_metrics == quality_metrics
        assert entry.chunking_result == chunking_result
        assert entry.timestamp == 1234567890
        assert entry.access_count == 5
        assert entry.hit_count == 3
        assert entry.optimization_time == 2.5


class TestCacheStatistics:
    """Test CacheStatistics data class."""
    
    def test_cache_statistics_creation(self):
        """Test CacheStatistics creation and defaults."""
        stats = CacheStatistics()
        
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.hit_rate == 0.0
        assert stats.avg_access_time == 0.0
        assert stats.memory_usage is None
        assert stats.redis_stats is None
    
    def test_cache_statistics_with_values(self):
        """Test CacheStatistics with custom values."""
        memory_usage = {"local_entries": 100}
        redis_stats = {"used_memory": 1024}
        
        stats = CacheStatistics(
            total_requests=1000,
            cache_hits=800,
            cache_misses=200,
            hit_rate=0.8,
            avg_access_time=0.05,
            memory_usage=memory_usage,
            redis_stats=redis_stats
        )
        
        assert stats.total_requests == 1000
        assert stats.cache_hits == 800
        assert stats.cache_misses == 200
        assert stats.hit_rate == 0.8
        assert stats.avg_access_time == 0.05
        assert stats.memory_usage == memory_usage
        assert stats.redis_stats == redis_stats


class TestIntelligentCacheManager:
    """Test suite for IntelligentCacheManager class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock()
        redis_mock.delete = AsyncMock()
        redis_mock.keys = AsyncMock(return_value=[])
        redis_mock.info = AsyncMock(return_value={
            "used_memory": 1024,
            "connected_clients": 5,
            "total_commands_processed": 1000
        })
        redis_mock.close = AsyncMock()
        return redis_mock
    
    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Create cache manager with mocked dependencies."""
        with patch('app.adaptive.cache_manager.SentenceTransformer') as mock_transformer:
            mock_embedder = Mock()
            mock_embedder.encode.return_value = np.array([[0.8, 0.1, 0.1], [0.7, 0.2, 0.1]])
            mock_transformer.return_value = mock_embedder
            
            manager = IntelligentCacheManager(
                redis_url="redis://localhost:6379",
                local_cache_size=100,
                similarity_threshold=0.85
            )
            manager.embedder = mock_embedder
            # Directly set the mocked redis client
            manager.redis_client = mock_redis
            return manager, mock_redis
    
    @pytest.mark.asyncio
    async def test_initialize_cache_manager(self, mock_redis):
        """Test cache manager initialization."""
        with patch('app.adaptive.cache_manager.redis.from_url', return_value=mock_redis):
            with patch('app.adaptive.cache_manager.SentenceTransformer') as mock_transformer:
                mock_embedder = Mock()
                mock_embedder.encode.return_value = np.array([[0.8, 0.1, 0.1], [0.7, 0.2, 0.1]])
                mock_transformer.return_value = mock_embedder
                
                manager = IntelligentCacheManager(
                    redis_url="redis://localhost:6379",
                    local_cache_size=100,
                    similarity_threshold=0.85
                )
                
                await manager.initialize()
                
                mock_redis.ping.assert_called_once()
                assert manager.redis_client == mock_redis
    
    @pytest.mark.asyncio
    async def test_initialize_redis_failure(self):
        """Test cache manager initialization with Redis failure."""
        with patch('app.adaptive.cache_manager.redis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping.side_effect = Exception("Redis connection failed")
            mock_from_url.return_value = mock_redis
            
            manager = IntelligentCacheManager()
            await manager.initialize()
            
            # Should handle failure gracefully
            assert manager.redis_client is None
    
    def test_generate_cache_key(self, cache_manager):
        """Test cache key generation."""
        manager, _ = cache_manager
        
        key = manager._generate_cache_key(
            text="Hello world",
            source_lang="en",
            target_lang="fr",
            chunk_size=300,
            content_type="emotional",
            optimization_level="optimized"
        )
        
        assert isinstance(key, CacheKey)
        assert len(key.text_hash) == 16  # SHA256 truncated to 16 chars
        assert key.source_lang == "en"
        assert key.target_lang == "fr"
        assert key.chunk_size == 300
        assert key.content_type == "emotional"
        assert key.optimization_level == "optimized"
    
    def test_cache_key_to_string(self, cache_manager):
        """Test cache key string conversion."""
        manager, _ = cache_manager
        
        cache_key = CacheKey(
            text_hash="abc123",
            source_lang="en",
            target_lang="fr",
            chunk_size=300,
            content_type="emotional",
            optimization_level="semantic"
        )
        
        key_string = manager._cache_key_to_string(cache_key)
        
        assert key_string.startswith("tg_translate:abc123:en:fr:semantic")
        assert "chunk_300" in key_string
        assert "type_emotional" in key_string
    
    @pytest.mark.asyncio
    async def test_get_translation_local_cache_hit(self, cache_manager):
        """Test getting translation from local cache."""
        manager, _ = cache_manager
        
        # Add entry to local cache
        cache_key = manager._generate_cache_key("test", "en", "fr")
        key_string = manager._cache_key_to_string(cache_key)
        
        mock_entry = CacheEntry(
            key=cache_key,
            translation="cached translation",
            quality_metrics=None,
            chunking_result=None,
            timestamp=time.time(),
            access_count=0,
            hit_count=0
        )
        
        manager.local_cache[key_string] = mock_entry
        manager.local_access_order.append(key_string)
        
        result = await manager.get_translation("test", "en", "fr")
        
        assert result == mock_entry
        assert result.access_count == 1
        assert result.hit_count == 1
        assert manager.stats.cache_hits == 1
    
    @pytest.mark.asyncio
    async def test_get_translation_redis_cache_hit(self, cache_manager):
        """Test getting translation from Redis cache."""
        manager, mock_redis = cache_manager
        
        # Mock Redis cache hit
        cache_entry = {
            "key": {
                "text_hash": "abc123",
                "source_lang": "en",
                "target_lang": "fr",
                "optimization_level": "semantic"
            },
            "translation": "redis cached translation",
            "timestamp": time.time(),
            "access_count": 0,
            "hit_count": 0
        }
        
        mock_redis.get.return_value = json.dumps(cache_entry)
        
        result = await manager.get_translation("test", "en", "fr")
        
        assert result is not None
        assert result.translation == "redis cached translation"
        assert manager.stats.cache_hits == 1
        # Should also be stored in local cache
        assert len(manager.local_cache) == 1
    
    @pytest.mark.asyncio
    async def test_get_translation_similarity_match(self, cache_manager):
        """Test getting translation via similarity matching."""
        manager, mock_redis = cache_manager
        
        # Add similar entry to local cache
        cache_key = manager._generate_cache_key("similar test", "en", "fr")
        key_string = manager._cache_key_to_string(cache_key)
        
        chunking_result = Mock()
        chunking_result.chunks = ["similar test"]
        
        similar_entry = CacheEntry(
            key=cache_key,
            translation="similar translation",
            quality_metrics=None,
            chunking_result=chunking_result,
            timestamp=time.time()
        )
        
        manager.local_cache[key_string] = similar_entry
        
        # Mock high similarity
        manager.embedder.encode.return_value = np.array([[0.9, 0.1], [0.95, 0.05]])  # High similarity
        
        result = await manager.get_translation("very similar test", "en", "fr")
        
        # Should find similarity match
        assert result is not None
        assert result.translation == "similar translation"
        assert manager.stats.cache_hits == 1
    
    @pytest.mark.asyncio
    async def test_get_translation_cache_miss(self, cache_manager):
        """Test cache miss scenario."""
        manager, mock_redis = cache_manager
        
        result = await manager.get_translation("new text", "en", "fr")
        
        assert result is None
        assert manager.stats.cache_misses == 1
        assert manager.stats.total_requests == 1
    
    @pytest.mark.asyncio
    async def test_store_translation(self, cache_manager):
        """Test storing translation in cache."""
        manager, mock_redis = cache_manager
        
        # Use real dataclass instances instead of mocks
        from app.adaptive.quality_assessment import QualityMetrics, QualityDimension
        from app.adaptive.semantic_chunker import ChunkingResult, ContentType
        
        quality_metrics = QualityMetrics(
            overall_score=0.85,
            dimension_scores={QualityDimension.CONFIDENCE: 0.85},
            confidence_interval=(0.8, 0.9),
            quality_grade="B",
            optimization_needed=False,
            improvement_suggestions=["Good translation"],
            metadata={}
        )
        
        chunking_result = ChunkingResult(
            chunks=["test text"],
            chunk_boundaries=[(0, 9)],
            content_type=ContentType.CONVERSATIONAL,
            coherence_score=0.9,
            optimal_size_estimate=300,
            metadata={}
        )
        
        await manager.store_translation(
            text="test text",
            source_lang="en",
            target_lang="fr",
            translation="stored translation",
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            chunk_size=300,
            content_type="emotional",
            optimization_level="optimized",
            optimization_time=2.5
        )
        
        # Should be stored in local cache
        assert len(manager.local_cache) == 1
        entry = list(manager.local_cache.values())[0]
        assert entry.translation == "stored translation"
        assert entry.quality_metrics == quality_metrics
        assert entry.chunking_result == chunking_result
        assert entry.optimization_time == 2.5
        
        # Should be stored in Redis
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_local_lru_eviction(self, cache_manager):
        """Test LRU eviction in local cache."""
        manager, _ = cache_manager
        manager.local_cache_size = 2  # Small cache for testing
        
        # Add entries beyond capacity
        for i in range(3):
            await manager._store_local(
                f"key_{i}",
                CacheEntry(
                    key=Mock(),
                    translation=f"translation_{i}",
                    quality_metrics=None,
                    chunking_result=None,
                    timestamp=time.time()
                )
            )
        
        # Should only keep 2 entries (most recent)
        assert len(manager.local_cache) == 2
        assert "key_0" not in manager.local_cache  # Oldest evicted
        assert "key_1" in manager.local_cache
        assert "key_2" in manager.local_cache
    
    @pytest.mark.asyncio
    async def test_find_similar_translation(self, cache_manager):
        """Test similarity-based translation finding."""
        manager, _ = cache_manager
        
        # Add entry to cache
        cache_key = CacheKey("hash1", "en", "fr", optimization_level="semantic")
        key_string = manager._cache_key_to_string(cache_key)
        
        chunking_result = Mock()
        chunking_result.chunks = ["original text"]
        
        entry = CacheEntry(
            key=cache_key,
            translation="original translation",
            quality_metrics=None,
            chunking_result=chunking_result,
            timestamp=time.time()
        )
        
        manager.local_cache[key_string] = entry
        
        # Mock high similarity
        manager.embedder.encode.side_effect = [
            np.array([[1.0, 0.0]]),  # Query text
            np.array([[0.9, 0.1]])   # Cached text (high similarity)
        ]
        
        result = await manager._find_similar_translation("similar text", "en", "fr", "semantic")
        
        assert result == entry
    
    @pytest.mark.asyncio
    async def test_find_similar_translation_no_embedder(self, cache_manager):
        """Test similarity finding without embedder."""
        manager, _ = cache_manager
        manager.embedder = None
        
        result = await manager._find_similar_translation("text", "en", "fr", "semantic")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_similar_translation_low_similarity(self, cache_manager):
        """Test similarity finding with low similarity."""
        manager, _ = cache_manager
        
        # Add entry to cache
        cache_key = CacheKey("hash1", "en", "fr", optimization_level="semantic")
        key_string = manager._cache_key_to_string(cache_key)
        
        chunking_result = Mock()
        chunking_result.chunks = ["different text"]
        
        entry = CacheEntry(
            key=cache_key,
            translation="different translation",
            quality_metrics=None,
            chunking_result=chunking_result,
            timestamp=time.time()
        )
        
        manager.local_cache[key_string] = entry
        
        # Mock low similarity
        manager.embedder.encode.side_effect = [
            np.array([[1.0, 0.0]]),  # Query text
            np.array([[0.0, 1.0]])   # Cached text (low similarity)
        ]
        
        result = await manager._find_similar_translation("query text", "en", "fr", "semantic")
        
        assert result is None  # Should not match due to low similarity
    
    def test_reconstruct_original_text(self, cache_manager):
        """Test original text reconstruction from cache entry."""
        manager, _ = cache_manager
        
        # Entry with chunking result
        chunking_result = Mock()
        chunking_result.chunks = ["chunk1", "chunk2", "chunk3"]
        
        entry = CacheEntry(
            key=Mock(),
            translation="translation",
            quality_metrics=None,
            chunking_result=chunking_result,
            timestamp=time.time()
        )
        
        result = manager._reconstruct_original_text(entry)
        assert result == "chunk1 chunk2 chunk3"
        
        # Entry without chunking result
        entry_no_chunks = CacheEntry(
            key=Mock(),
            translation="translation",
            quality_metrics=None,
            chunking_result=None,
            timestamp=time.time()
        )
        
        result = manager._reconstruct_original_text(entry_no_chunks)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_pattern_cache(self, cache_manager):
        """Test pattern cache updating."""
        manager, _ = cache_manager
        
        cache_key = CacheKey("hash1", "en", "fr", content_type="emotional")
        entry = CacheEntry(
            key=cache_key,
            translation="test translation",
            quality_metrics=None,
            chunking_result=None,
            timestamp=time.time()
        )
        
        await manager._update_pattern_cache(entry)
        
        pattern_key = "en_fr_emotional"
        assert pattern_key in manager.pattern_cache
        assert entry in manager.pattern_cache[pattern_key]
    
    @pytest.mark.asyncio
    async def test_update_pattern_cache_size_limit(self, cache_manager):
        """Test pattern cache size limiting."""
        manager, _ = cache_manager
        
        cache_key = CacheKey("hash1", "en", "fr", content_type="test")
        pattern_key = "en_fr_test"
        
        # Add many entries to exceed limit
        for i in range(150):  # Exceeds the 100 limit
            entry = CacheEntry(
                key=cache_key,
                translation=f"translation_{i}",
                quality_metrics=None,
                chunking_result=None,
                timestamp=time.time()
            )
            await manager._update_pattern_cache(entry)
        
        # Should keep only the last 100
        assert len(manager.pattern_cache[pattern_key]) == 100
    
    def test_serialize_cache_entry(self, cache_manager):
        """Test cache entry serialization."""
        manager, _ = cache_manager
        
        cache_key = CacheKey("hash1", "en", "fr")
        quality_metrics = QualityMetrics(
            overall_score=0.85,
            dimension_scores={QualityDimension.CONFIDENCE: 0.8},
            confidence_interval=(0.7, 0.9),
            quality_grade="B",
            optimization_needed=False,
            improvement_suggestions=[],
            metadata={}
        )
        
        chunking_result = ChunkingResult(
            chunks=["chunk1"],
            chunk_boundaries=[(0, 6)],
            content_type=ContentType.CONVERSATIONAL,
            coherence_score=0.8,
            optimal_size_estimate=300,
            metadata={}
        )
        
        entry = CacheEntry(
            key=cache_key,
            translation="test translation",
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            timestamp=time.time()
        )
        
        serialized = manager._serialize_cache_entry(entry)
        
        assert isinstance(serialized, dict)
        assert serialized["translation"] == "test translation"
        assert isinstance(serialized["key"], dict)
        assert isinstance(serialized["quality_metrics"], dict)
        assert isinstance(serialized["chunking_result"], dict)
    
    def test_deserialize_cache_entry(self, cache_manager):
        """Test cache entry deserialization."""
        manager, _ = cache_manager
        
        entry_dict = {
            "key": {
                "text_hash": "abc123",
                "source_lang": "en",
                "target_lang": "fr",
                "chunk_size": None,
                "content_type": None,
                "optimization_level": "semantic"
            },
            "translation": "test translation",
            "quality_metrics": {
                "overall_score": 0.85,
                "dimension_scores": {},
                "confidence_interval": (0.7, 0.9),
                "quality_grade": "B",
                "optimization_needed": False,
                "improvement_suggestions": [],
                "metadata": {}
            },
            "chunking_result": {
                "chunks": ["chunk1"],
                "chunk_boundaries": [(0, 6)],
                "content_type": "conversational",
                "coherence_score": 0.8,
                "optimal_size_estimate": 300,
                "metadata": {}
            },
            "timestamp": 1234567890,
            "access_count": 5,
            "hit_count": 3
        }
        
        entry = manager._deserialize_cache_entry(entry_dict)
        
        assert isinstance(entry, CacheEntry)
        assert entry.translation == "test translation"
        assert isinstance(entry.key, CacheKey)
        assert isinstance(entry.quality_metrics, QualityMetrics)
        assert isinstance(entry.chunking_result, ChunkingResult)
        assert entry.access_count == 5
        assert entry.hit_count == 3
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_manager):
        """Test cache pattern invalidation."""
        manager, mock_redis = cache_manager
        
        # Add entries to local cache
        key1 = "tg_translate:hash1:en:fr:semantic"
        key2 = "tg_translate:hash2:en:fr:semantic:type_emotional"
        key3 = "tg_translate:hash3:ru:en:semantic"
        
        manager.local_cache[key1] = Mock()
        manager.local_cache[key2] = Mock()
        manager.local_cache[key3] = Mock()
        manager.local_access_order = [key1, key2, key3]
        
        # Mock Redis keys
        mock_redis.keys.return_value = [key1.encode(), key2.encode()]
        
        await manager.invalidate_pattern("en", "fr")
        
        # Should remove en->fr entries from local cache
        assert key1 not in manager.local_cache
        assert key2 not in manager.local_cache
        assert key3 in manager.local_cache  # Different language pair
        
        # Should delete from Redis
        mock_redis.delete.assert_called_once()
    
    def test_key_matches_pattern(self, cache_manager):
        """Test pattern matching for cache keys."""
        manager, _ = cache_manager
        
        # Test matching keys
        assert manager._key_matches_pattern(
            "tg_translate:hash1:en:fr:semantic", "en", "fr", None
        )
        assert manager._key_matches_pattern(
            "tg_translate:hash2:en:fr:semantic:type_emotional", "en", "fr", "emotional"
        )
        
        # Test non-matching keys
        assert not manager._key_matches_pattern(
            "tg_translate:hash3:ru:en:semantic", "en", "fr", None
        )
        assert not manager._key_matches_pattern(
            "tg_translate:hash4:en:fr:semantic:type_technical", "en", "fr", "emotional"
        )
        assert not manager._key_matches_pattern(
            "invalid:key:format", "en", "fr", None
        )
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, cache_manager):
        """Test cache statistics retrieval."""
        manager, mock_redis = cache_manager
        
        # Set up some stats
        manager.stats.total_requests = 100
        manager.stats.cache_hits = 80
        manager.stats.cache_misses = 20
        
        # Add some local cache entries
        manager.local_cache["key1"] = Mock()
        manager.local_cache["key2"] = Mock()
        
        # Add pattern cache entries
        manager.pattern_cache["en_fr_test"] = [Mock(), Mock(), Mock()]
        
        stats = await manager.get_statistics()
        
        assert isinstance(stats, CacheStatistics)
        assert stats.hit_rate == 0.8  # 80/100
        assert stats.memory_usage["local_entries"] == 2
        assert stats.memory_usage["pattern_cache_size"] == 3
        assert stats.redis_stats["used_memory"] == 1024
        
        # Verify Redis info was called
        mock_redis.info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_statistics_redis_failure(self, cache_manager):
        """Test statistics retrieval when Redis fails."""
        manager, mock_redis = cache_manager
        mock_redis.info.side_effect = Exception("Redis error")
        
        stats = await manager.get_statistics()
        
        assert isinstance(stats, CacheStatistics)
        # Should handle Redis failure gracefully
        assert stats.redis_stats is None
    
    @pytest.mark.asyncio
    async def test_warm_cache(self, cache_manager):
        """Test cache warming functionality."""
        manager, _ = cache_manager
        
        common_translations = [
            ("Hello", "en", "fr", "Bonjour"),
            ("Goodbye", "en", "fr", "Au revoir"),
            ("Thank you", "en", "fr", "Merci")
        ]
        
        await manager.warm_cache(common_translations)
        
        # Should have stored all translations
        assert len(manager.local_cache) == 3
        
        # Verify one of the translations
        result = await manager.get_translation("Hello", "en", "fr")
        assert result is not None
        assert result.translation == "Bonjour"
    
    @pytest.mark.asyncio
    async def test_close(self, cache_manager):
        """Test cache manager cleanup."""
        manager, mock_redis = cache_manager
        
        await manager.close()
        
        mock_redis.close.assert_called_once()


class TestCreateCacheManagerUtility:
    """Test the utility function."""
    
    @pytest.mark.asyncio
    async def test_create_cache_manager(self):
        """Test the create_cache_manager utility function."""
        with patch('app.adaptive.cache_manager.IntelligentCacheManager') as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager_class.return_value = mock_manager
            
            result = await create_cache_manager("redis://test:6379")
            
            assert result == mock_manager
            mock_manager_class.assert_called_once_with(redis_url="redis://test:6379")
            mock_manager.initialize.assert_called_once()


class TestCacheManagerEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def manager_no_embedder(self):
        """Create cache manager without embedder."""
        with patch('app.adaptive.cache_manager.SentenceTransformer') as mock_transformer:
            mock_transformer.side_effect = Exception("No embedder")
            manager = IntelligentCacheManager()
            assert manager.embedder is None
            return manager
    
    @pytest.mark.asyncio
    async def test_manager_without_embedder(self, manager_no_embedder):
        """Test cache manager operation without embedder."""
        # Should not crash
        result = await manager_no_embedder.get_translation("test", "en", "fr")
        assert result is None
        
        # Similarity matching should fail gracefully
        similar = await manager_no_embedder._find_similar_translation("test", "en", "fr", "semantic")
        assert similar is None
    
    @pytest.mark.asyncio
    async def test_redis_serialization_error(self):
        """Test handling of Redis serialization errors."""
        with patch('app.adaptive.cache_manager.redis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.setex.side_effect = Exception("Serialization error")
            mock_from_url.return_value = mock_redis
            
            manager = IntelligentCacheManager()
            await manager.initialize()
            
            # Should handle serialization error gracefully
            await manager.store_translation("test", "en", "fr", "translation")
            # Should not crash
    
    @pytest.mark.asyncio
    async def test_redis_deserialization_error(self):
        """Test handling of Redis deserialization errors."""
        with patch('app.adaptive.cache_manager.redis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.get.return_value = "invalid json"  # Invalid JSON
            mock_from_url.return_value = mock_redis
            
            manager = IntelligentCacheManager()
            await manager.initialize()
            
            result = await manager.get_translation("test", "en", "fr")
            # Should handle gracefully and return None
            assert result is None
    
    @pytest.mark.asyncio
    async def test_very_large_cache_key(self, manager_no_embedder):
        """Test with very large cache key (long text)."""
        very_long_text = "word " * 10000  # Very long text
        
        key = manager_no_embedder._generate_cache_key(very_long_text, "en", "fr")
        
        # Hash should still be short
        assert len(key.text_hash) == 16
        
        # Should handle normally
        await manager_no_embedder.store_translation(very_long_text, "en", "fr", "translation")
    
    @pytest.mark.asyncio
    async def test_unicode_text_handling(self, manager_no_embedder):
        """Test cache with Unicode text."""
        unicode_text = "Hello 世界 🌍 Здравствуй мир"
        
        await manager_no_embedder.store_translation(unicode_text, "multi", "en", "translation")
        
        result = await manager_no_embedder.get_translation(unicode_text, "multi", "en")
        
        assert result is not None
        assert result.translation == "translation"
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, manager_no_embedder):
        """Test concurrent cache operations."""
        async def store_translation(i):
            await manager_no_embedder.store_translation(f"text{i}", "en", "fr", f"translation{i}")
        
        async def get_translation(i):
            return await manager_no_embedder.get_translation(f"text{i}", "en", "fr")
        
        # Run concurrent operations
        store_tasks = [store_translation(i) for i in range(10)]
        await asyncio.gather(*store_tasks)
        
        get_tasks = [get_translation(i) for i in range(10)]
        results = await asyncio.gather(*get_tasks)
        
        # Should handle concurrency gracefully
        assert len([r for r in results if r is not None]) == 10