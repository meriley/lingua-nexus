"""
Intelligent Cache Manager

Multi-level caching system with Redis integration, pattern-based keys, and similarity matching.
Supports local cache, Redis cache, and pattern-based cache optimization for translation results.
"""

import json
import hashlib
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import time

import redis.asyncio as redis
import numpy as np
from sentence_transformers import SentenceTransformer

from .quality_assessment import QualityMetrics
from .semantic_chunker import ChunkingResult

logger = logging.getLogger(__name__)


@dataclass
class CacheKey:
    """Structured cache key for translations."""
    text_hash: str
    source_lang: str
    target_lang: str
    chunk_size: Optional[int] = None
    content_type: Optional[str] = None
    optimization_level: str = "semantic"  # semantic, optimized


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: CacheKey
    translation: str
    quality_metrics: Optional[QualityMetrics]
    chunking_result: Optional[ChunkingResult]
    timestamp: float
    access_count: int = 0
    hit_count: int = 0
    optimization_time: Optional[float] = None


@dataclass
class CacheStatistics:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    avg_access_time: float = 0.0
    memory_usage: Dict[str, int] = None
    redis_stats: Dict[str, Any] = None


class IntelligentCacheManager:
    """
    Multi-level intelligent cache manager with Redis integration,
    similarity matching, and pattern-based optimization.
    """
    
    def __init__(self,
                 redis_url: str = "redis://localhost:6379",
                 local_cache_size: int = 1000,
                 redis_ttl: int = 86400,  # 24 hours
                 similarity_threshold: float = 0.85,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the intelligent cache manager.
        
        Args:
            redis_url: Redis connection URL
            local_cache_size: Maximum local cache entries
            redis_ttl: Redis TTL in seconds
            similarity_threshold: Threshold for similarity matching
            embedding_model: Model for semantic similarity
        """
        self.redis_url = redis_url
        self.local_cache_size = local_cache_size
        self.redis_ttl = redis_ttl
        self.similarity_threshold = similarity_threshold
        
        # Local cache
        self.local_cache: Dict[str, CacheEntry] = {}
        self.local_access_order: List[str] = []
        
        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        
        # Embeddings for similarity matching
        try:
            self.embedder = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model for cache similarity: {embedding_model}")
        except Exception as e:
            logger.warning(f"Failed to load embedding model {embedding_model}: {e}")
            self.embedder = None
        
        # Statistics
        self.stats = CacheStatistics()
        
        # Pattern cache for optimization
        self.pattern_cache: Dict[str, List[CacheEntry]] = {}

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

    def _generate_cache_key(self, 
                          text: str,
                          source_lang: str,
                          target_lang: str,
                          chunk_size: Optional[int] = None,
                          content_type: Optional[str] = None,
                          optimization_level: str = "semantic") -> CacheKey:
        """Generate structured cache key."""
        # Create hash of text content
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
        
        return CacheKey(
            text_hash=text_hash,
            source_lang=source_lang,
            target_lang=target_lang,
            chunk_size=chunk_size,
            content_type=content_type,
            optimization_level=optimization_level
        )

    def _cache_key_to_string(self, cache_key: CacheKey) -> str:
        """Convert cache key to string representation."""
        parts = [
            f"tg_translate",
            cache_key.text_hash,
            cache_key.source_lang,
            cache_key.target_lang,
            cache_key.optimization_level
        ]
        
        if cache_key.chunk_size:
            parts.append(f"chunk_{cache_key.chunk_size}")
        if cache_key.content_type:
            parts.append(f"type_{cache_key.content_type}")
            
        return ":".join(parts)

    async def get_translation(self,
                            text: str,
                            source_lang: str,
                            target_lang: str,
                            chunk_size: Optional[int] = None,
                            content_type: Optional[str] = None,
                            optimization_level: str = "semantic") -> Optional[CacheEntry]:
        """
        Get translation from cache with multi-level lookup and similarity matching.
        
        Args:
            text: Original text
            source_lang: Source language
            target_lang: Target language
            chunk_size: Optional chunk size
            content_type: Optional content type
            optimization_level: Optimization level (semantic, optimized)
            
        Returns:
            CacheEntry if found, None otherwise
        """
        start_time = time.time()
        self.stats.total_requests += 1
        
        cache_key = self._generate_cache_key(
            text, source_lang, target_lang, chunk_size, content_type, optimization_level
        )
        key_string = self._cache_key_to_string(cache_key)
        
        # 1. Local cache lookup
        if key_string in self.local_cache:
            entry = self.local_cache[key_string]
            entry.access_count += 1
            entry.hit_count += 1
            self._update_access_order(key_string)
            
            self.stats.cache_hits += 1
            self.stats.avg_access_time = (self.stats.avg_access_time + (time.time() - start_time)) / 2
            
            logger.debug(f"Local cache hit for key: {key_string}")
            return entry
        
        # 2. Redis cache lookup
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(key_string)
                if cached_data:
                    entry_dict = json.loads(cached_data)
                    entry = self._deserialize_cache_entry(entry_dict)
                    
                    # Store in local cache
                    await self._store_local(key_string, entry)
                    
                    self.stats.cache_hits += 1
                    self.stats.avg_access_time = (self.stats.avg_access_time + (time.time() - start_time)) / 2
                    
                    logger.debug(f"Redis cache hit for key: {key_string}")
                    return entry
            except Exception as e:
                logger.warning(f"Redis lookup failed: {e}")
        
        # 3. Similarity-based lookup
        similar_entry = await self._find_similar_translation(
            text, source_lang, target_lang, optimization_level
        )
        
        if similar_entry:
            # Store similar result with new key
            await self.store_translation(
                text, source_lang, target_lang, similar_entry.translation,
                similar_entry.quality_metrics, similar_entry.chunking_result,
                chunk_size, content_type, optimization_level
            )
            
            self.stats.cache_hits += 1
            self.stats.avg_access_time = (self.stats.avg_access_time + (time.time() - start_time)) / 2
            
            logger.debug(f"Similarity cache hit for text: {text[:50]}...")
            return similar_entry
        
        # 4. Cache miss
        self.stats.cache_misses += 1
        self.stats.avg_access_time = (self.stats.avg_access_time + (time.time() - start_time)) / 2
        
        logger.debug(f"Cache miss for key: {key_string}")
        return None

    async def store_translation(self,
                              text: str,
                              source_lang: str,
                              target_lang: str,
                              translation: str,
                              quality_metrics: Optional[QualityMetrics] = None,
                              chunking_result: Optional[ChunkingResult] = None,
                              chunk_size: Optional[int] = None,
                              content_type: Optional[str] = None,
                              optimization_level: str = "semantic",
                              optimization_time: Optional[float] = None):
        """
        Store translation in multi-level cache.
        
        Args:
            text: Original text
            source_lang: Source language
            target_lang: Target language
            translation: Translation result
            quality_metrics: Optional quality metrics
            chunking_result: Optional chunking result
            chunk_size: Optional chunk size
            content_type: Optional content type
            optimization_level: Optimization level
            optimization_time: Time taken for optimization
        """
        cache_key = self._generate_cache_key(
            text, source_lang, target_lang, chunk_size, content_type, optimization_level
        )
        key_string = self._cache_key_to_string(cache_key)
        
        entry = CacheEntry(
            key=cache_key,
            translation=translation,
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            timestamp=time.time(),
            optimization_time=optimization_time
        )
        
        # Store in local cache
        await self._store_local(key_string, entry)
        
        # Store in Redis
        if self.redis_client:
            try:
                entry_dict = self._serialize_cache_entry(entry)
                await self.redis_client.setex(
                    key_string, 
                    self.redis_ttl, 
                    json.dumps(entry_dict)
                )
                logger.debug(f"Stored in Redis cache: {key_string}")
            except Exception as e:
                logger.warning(f"Redis storage failed: {e}")
        
        # Update pattern cache
        await self._update_pattern_cache(entry)

    async def _store_local(self, key_string: str, entry: CacheEntry):
        """Store entry in local cache with LRU eviction."""
        # Remove if already exists
        if key_string in self.local_cache:
            self.local_access_order.remove(key_string)
        
        # Add to cache
        self.local_cache[key_string] = entry
        self.local_access_order.append(key_string)
        
        # Evict if over size limit
        while len(self.local_cache) > self.local_cache_size:
            oldest_key = self.local_access_order.pop(0)
            del self.local_cache[oldest_key]

    def _update_access_order(self, key_string: str):
        """Update access order for LRU."""
        if key_string in self.local_access_order:
            self.local_access_order.remove(key_string)
        self.local_access_order.append(key_string)

    async def _find_similar_translation(self,
                                      text: str,
                                      source_lang: str,
                                      target_lang: str,
                                      optimization_level: str) -> Optional[CacheEntry]:
        """Find similar translation using semantic similarity."""
        if not self.embedder:
            return None
        
        try:
            # Get embedding for current text
            text_embedding = self.embedder.encode([text])
            
            # Search through local cache
            for cached_entry in self.local_cache.values():
                if (cached_entry.key.source_lang == source_lang and
                    cached_entry.key.target_lang == target_lang and
                    cached_entry.key.optimization_level == optimization_level):
                    
                    # Get text from chunking result or reconstruct
                    cached_text = self._reconstruct_original_text(cached_entry)
                    if not cached_text:
                        continue
                    
                    # Calculate similarity
                    cached_embedding = self.embedder.encode([cached_text])
                    similarity = np.dot(text_embedding[0], cached_embedding[0]) / (
                        np.linalg.norm(text_embedding[0]) * np.linalg.norm(cached_embedding[0])
                    )
                    
                    if similarity >= self.similarity_threshold:
                        logger.debug(f"Found similar translation with similarity: {similarity:.3f}")
                        return cached_entry
            
            return None
            
        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
            return None

    def _reconstruct_original_text(self, entry: CacheEntry) -> Optional[str]:
        """Reconstruct original text from cache entry."""
        if entry.chunking_result and entry.chunking_result.chunks:
            # Reconstruct from chunks
            return " ".join(entry.chunking_result.chunks)
        
        # Cannot reconstruct without chunking result
        return None

    async def _update_pattern_cache(self, entry: CacheEntry):
        """Update pattern-based cache for optimization."""
        # Create pattern key based on content characteristics
        pattern_key = f"{entry.key.source_lang}_{entry.key.target_lang}_{entry.key.content_type or 'default'}"
        
        if pattern_key not in self.pattern_cache:
            self.pattern_cache[pattern_key] = []
        
        # Add entry to pattern cache (keep limited size)
        self.pattern_cache[pattern_key].append(entry)
        
        # Keep only recent entries
        if len(self.pattern_cache[pattern_key]) > 100:
            self.pattern_cache[pattern_key] = self.pattern_cache[pattern_key][-100:]

    def _serialize_cache_entry(self, entry: CacheEntry) -> Dict[str, Any]:
        """Serialize cache entry for Redis storage."""
        entry_dict = asdict(entry)
        
        # Handle special serialization for complex objects
        if entry.quality_metrics:
            quality_dict = asdict(entry.quality_metrics)
            # Convert enum keys to strings for JSON serialization
            if 'dimension_scores' in quality_dict:
                quality_dict['dimension_scores'] = {
                    k.value if hasattr(k, 'value') else str(k): v 
                    for k, v in quality_dict['dimension_scores'].items()
                }
            entry_dict['quality_metrics'] = quality_dict
        
        if entry.chunking_result:
            chunking_dict = asdict(entry.chunking_result)
            # Convert enum values to strings for JSON serialization
            if 'content_type' in chunking_dict and hasattr(chunking_dict['content_type'], 'value'):
                chunking_dict['content_type'] = chunking_dict['content_type'].value
            entry_dict['chunking_result'] = chunking_dict
        
        return entry_dict

    def _deserialize_cache_entry(self, entry_dict: Dict[str, Any]) -> CacheEntry:
        """Deserialize cache entry from Redis data."""
        # Reconstruct cache key
        key_data = entry_dict['key']
        cache_key = CacheKey(**key_data)
        
        # Reconstruct quality metrics if present
        quality_metrics = None
        if entry_dict.get('quality_metrics'):
            quality_metrics = QualityMetrics(**entry_dict['quality_metrics'])
        
        # Reconstruct chunking result if present
        chunking_result = None
        if entry_dict.get('chunking_result'):
            from .semantic_chunker import ChunkingResult, ContentType
            cr_data = entry_dict['chunking_result']
            if 'content_type' in cr_data and isinstance(cr_data['content_type'], str):
                cr_data['content_type'] = ContentType(cr_data['content_type'])
            chunking_result = ChunkingResult(**cr_data)
        
        return CacheEntry(
            key=cache_key,
            translation=entry_dict['translation'],
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            timestamp=entry_dict['timestamp'],
            access_count=entry_dict.get('access_count', 0),
            hit_count=entry_dict.get('hit_count', 0),
            optimization_time=entry_dict.get('optimization_time')
        )

    async def invalidate_pattern(self, 
                               source_lang: str,
                               target_lang: str,
                               content_type: Optional[str] = None):
        """Invalidate cache entries matching pattern."""
        pattern = f"tg_translate:*:{source_lang}:{target_lang}:*"
        if content_type:
            pattern += f":type_{content_type}"
        
        # Clear from local cache
        keys_to_remove = []
        for key in self.local_cache:
            if self._key_matches_pattern(key, source_lang, target_lang, content_type):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.local_cache[key]
            if key in self.local_access_order:
                self.local_access_order.remove(key)
        
        # Clear from Redis
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys_to_remove)} local and {len(keys) if keys else 0} Redis entries")
            except Exception as e:
                logger.warning(f"Redis invalidation failed: {e}")

    def _key_matches_pattern(self, key: str, source_lang: str, target_lang: str, content_type: Optional[str]) -> bool:
        """Check if key matches invalidation pattern."""
        parts = key.split(":")
        if len(parts) < 5:
            return False
        
        return (parts[2] == source_lang and 
                parts[3] == target_lang and
                (content_type is None or f"type_{content_type}" in parts))

    async def get_statistics(self) -> CacheStatistics:
        """Get cache performance statistics."""
        # Update hit rate
        if self.stats.total_requests > 0:
            self.stats.hit_rate = self.stats.cache_hits / self.stats.total_requests
        
        # Update memory usage
        self.stats.memory_usage = {
            "local_entries": len(self.local_cache),
            "pattern_cache_size": sum(len(entries) for entries in self.pattern_cache.values())
        }
        
        # Get Redis stats if available
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                self.stats.redis_stats = {
                    "used_memory": redis_info.get("used_memory", 0),
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "total_commands_processed": redis_info.get("total_commands_processed", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")
        
        return self.stats

    async def warm_cache(self, common_translations: List[Tuple[str, str, str, str]]):
        """
        Warm cache with common translations.
        
        Args:
            common_translations: List of (text, source_lang, target_lang, translation) tuples
        """
        logger.info(f"Warming cache with {len(common_translations)} translations")
        
        for text, source_lang, target_lang, translation in common_translations:
            await self.store_translation(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                translation=translation,
                optimization_level="semantic"
            )
        
        logger.info("Cache warming completed")


# Utility functions
async def create_cache_manager(redis_url: str = "redis://localhost:6379") -> IntelligentCacheManager:
    """Create and initialize cache manager."""
    cache_manager = IntelligentCacheManager(redis_url=redis_url)
    await cache_manager.initialize()
    return cache_manager