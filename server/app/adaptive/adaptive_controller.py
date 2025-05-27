"""
Adaptive Translation Controller

Main orchestration logic for the adaptive translation chunking system.
Coordinates semantic chunking, quality assessment, caching, and optimization.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass
from enum import Enum

from .semantic_chunker import SemanticChunker, ChunkingResult, ContentType
from .quality_assessment import QualityMetricsEngine, QualityMetrics, TranslationPair
from .cache_manager import IntelligentCacheManager, CacheEntry
from .binary_search_optimizer import BinarySearchOptimizer, OptimizationStrategy

logger = logging.getLogger(__name__)


class TranslationStage(Enum):
    """Translation processing stages."""
    SEMANTIC = "semantic"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    OPTIMIZED = "optimized"
    ERROR = "error"


@dataclass
class AdaptiveTranslationRequest:
    """Request for adaptive translation."""
    text: str
    source_lang: str
    target_lang: str
    api_key: str
    user_preference: str = "balanced"  # fast, balanced, quality
    force_optimization: bool = False
    max_optimization_time: float = 5.0


@dataclass
class TranslationUpdate:
    """Progressive translation update."""
    stage: TranslationStage
    translation: Optional[str] = None
    quality_metrics: Optional[QualityMetrics] = None
    chunking_result: Optional[ChunkingResult] = None
    progress: float = 0.0
    status_message: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class TranslationResult:
    """Final translation result."""
    translation: str
    original_text: str
    quality_metrics: QualityMetrics
    chunking_result: ChunkingResult
    processing_time: float
    cache_hit: bool
    optimization_applied: bool
    stage_times: Dict[str, float]
    metadata: Dict[str, Any]


class AdaptiveTranslationController:
    """
    Main controller for adaptive translation system.
    Orchestrates semantic chunking, quality assessment, and optimization.
    """
    
    def __init__(self,
                 translation_function: Callable,
                 chunker: Optional[SemanticChunker] = None,
                 quality_engine: Optional[QualityMetricsEngine] = None,
                 cache_manager: Optional[IntelligentCacheManager] = None,
                 binary_optimizer: Optional[BinarySearchOptimizer] = None,
                 quality_threshold: float = 0.75,
                 max_concurrent_translations: int = 5):
        """
        Initialize the adaptive translation controller.
        
        Args:
            translation_function: Function that performs actual translation
            chunker: Semantic chunker instance
            quality_engine: Quality assessment engine
            cache_manager: Cache manager instance
            binary_optimizer: Binary search optimizer for chunk size optimization
            quality_threshold: Quality threshold for optimization
            max_concurrent_translations: Max concurrent translations
        """
        self.translation_function = translation_function
        self.chunker = chunker or SemanticChunker()
        self.quality_engine = quality_engine or QualityMetricsEngine()
        self.cache_manager = cache_manager
        self.binary_optimizer = binary_optimizer or BinarySearchOptimizer(translation_function)
        self.quality_threshold = quality_threshold
        
        # Concurrency control
        self.translation_semaphore = asyncio.Semaphore(max_concurrent_translations)
        
        # Performance tracking
        self.performance_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "optimizations_triggered": 0,
            "avg_processing_time": 0.0,
            "avg_quality_improvement": 0.0
        }

    async def translate(self, request: AdaptiveTranslationRequest) -> TranslationResult:
        """
        Perform adaptive translation with intelligent optimization.
        
        Args:
            request: Translation request with preferences
            
        Returns:
            TranslationResult with optimized translation
        """
        start_time = time.time()
        stage_times = {}
        
        try:
            self.performance_stats["total_requests"] += 1
            
            # 1. Check cache first
            cache_start = time.time()
            cached_result = await self._check_cache(request)
            stage_times["cache_lookup"] = time.time() - cache_start
            
            if cached_result:
                self.performance_stats["cache_hits"] += 1
                return self._create_result_from_cache(cached_result, start_time, stage_times)
            
            # 2. Semantic chunking and fast path translation
            semantic_start = time.time()
            semantic_result = await self._semantic_translation_path(request)
            stage_times["semantic_translation"] = time.time() - semantic_start
            
            # 3. Quality assessment
            quality_start = time.time()
            quality_metrics = await self._assess_translation_quality(
                request.text, semantic_result.translation, semantic_result.chunking_result
            )
            stage_times["quality_assessment"] = time.time() - quality_start
            
            # 4. Determine if optimization is needed
            needs_optimization = self._should_optimize(
                quality_metrics, request.user_preference, request.force_optimization
            )
            
            final_translation = semantic_result.translation
            final_chunking = semantic_result.chunking_result
            optimization_applied = False
            
            # 5. Optimization path if needed
            if needs_optimization:
                optimization_start = time.time()
                try:
                    optimized_result = await asyncio.wait_for(
                        self._optimization_path(request, semantic_result),
                        timeout=request.max_optimization_time
                    )
                    
                    # Verify optimization improved quality
                    optimized_quality = await self._assess_translation_quality(
                        request.text, optimized_result.translation, optimized_result.chunking_result
                    )
                    
                    if optimized_quality.overall_score > quality_metrics.overall_score:
                        final_translation = optimized_result.translation
                        final_chunking = optimized_result.chunking_result
                        quality_metrics = optimized_quality
                        optimization_applied = True
                        self.performance_stats["optimizations_triggered"] += 1
                        
                        # Update performance stats
                        improvement = optimized_quality.overall_score - quality_metrics.overall_score
                        self.performance_stats["avg_quality_improvement"] = (
                            self.performance_stats["avg_quality_improvement"] + improvement
                        ) / 2
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Optimization timeout after {request.max_optimization_time}s")
                except Exception as e:
                    logger.warning(f"Optimization failed: {e}")
                
                stage_times["optimization"] = time.time() - optimization_start
            
            # 6. Cache the result
            if self.cache_manager:
                await self._cache_result(request, final_translation, quality_metrics, final_chunking)
            
            # 7. Create final result
            total_time = time.time() - start_time
            self.performance_stats["avg_processing_time"] = (
                self.performance_stats["avg_processing_time"] + total_time
            ) / 2
            
            return TranslationResult(
                translation=final_translation,
                original_text=request.text,
                quality_metrics=quality_metrics,
                chunking_result=final_chunking,
                processing_time=total_time,
                cache_hit=False,
                optimization_applied=optimization_applied,
                stage_times=stage_times,
                metadata={
                    "user_preference": request.user_preference,
                    "needs_optimization": needs_optimization,
                    "source_lang": request.source_lang,
                    "target_lang": request.target_lang
                }
            )
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    async def progressive_translate(self, 
                                  request: AdaptiveTranslationRequest,
                                  callback: Callable[[TranslationUpdate], None]) -> TranslationResult:
        """
        Perform progressive translation with real-time updates.
        
        Args:
            request: Translation request
            callback: Callback function for progress updates
            
        Returns:
            Final translation result
        """
        start_time = time.time()
        
        async def safe_callback(update):
            """Safely call callback, logging exceptions but not failing."""
            try:
                await callback(update)
            except Exception as e:
                logger.warning(f"Callback failed: {e}")
        
        try:
            # Initial update
            await safe_callback(TranslationUpdate(
                stage=TranslationStage.SEMANTIC,
                status_message="Starting semantic translation...",
                progress=0.1
            ))
            
            # Check cache
            cached_result = await self._check_cache(request)
            if cached_result:
                await safe_callback(TranslationUpdate(
                    stage=TranslationStage.SEMANTIC,
                    translation=cached_result.translation,
                    quality_metrics=cached_result.quality_metrics,
                    progress=1.0,
                    status_message="Retrieved from cache"
                ))
                return self._create_result_from_cache(cached_result, time.time(), {})
            
            # Semantic translation
            await safe_callback(TranslationUpdate(
                stage=TranslationStage.SEMANTIC,
                status_message="Performing semantic chunking...",
                progress=0.3
            ))
            
            semantic_result = await self._semantic_translation_path(request)
            
            await safe_callback(TranslationUpdate(
                stage=TranslationStage.SEMANTIC,
                translation=semantic_result.translation,
                chunking_result=semantic_result.chunking_result,
                progress=0.6,
                status_message="Semantic translation complete"
            ))
            
            # Quality assessment
            await safe_callback(TranslationUpdate(
                stage=TranslationStage.ANALYZING,
                translation=semantic_result.translation,
                progress=0.7,
                status_message="Analyzing translation quality..."
            ))
            
            quality_metrics = await self._assess_translation_quality(
                request.text, semantic_result.translation, semantic_result.chunking_result
            )
            
            # Check if optimization is needed
            needs_optimization = self._should_optimize(
                quality_metrics, request.user_preference, request.force_optimization
            )
            
            if not needs_optimization:
                await safe_callback(TranslationUpdate(
                    stage=TranslationStage.SEMANTIC,
                    translation=semantic_result.translation,
                    quality_metrics=quality_metrics,
                    progress=1.0,
                    status_message="Translation complete - high quality achieved"
                ))
                
                # Create result directly without optimization
                total_time = time.time() - start_time
                stage_times = {"progressive_semantic": total_time}
                
                # Cache the result
                if self.cache_manager:
                    await self._cache_result(request, semantic_result.translation, quality_metrics, semantic_result.chunking_result)
                
                return TranslationResult(
                    translation=semantic_result.translation,
                    original_text=request.text,
                    quality_metrics=quality_metrics,
                    chunking_result=semantic_result.chunking_result,
                    processing_time=total_time,
                    cache_hit=False,
                    optimization_applied=False,
                    stage_times=stage_times,
                    metadata={
                        "user_preference": request.user_preference,
                        "needs_optimization": False,
                        "source_lang": request.source_lang,
                        "target_lang": request.target_lang
                    }
                )
            
            # Optimization needed
            await safe_callback(TranslationUpdate(
                stage=TranslationStage.OPTIMIZING,
                translation=semantic_result.translation,
                quality_metrics=quality_metrics,
                progress=0.8,
                status_message="Optimizing translation quality..."
            ))
            
            # Perform optimization
            optimized_result = await self._optimization_path(request, semantic_result)
            optimized_quality = await self._assess_translation_quality(
                request.text, optimized_result.translation, optimized_result.chunking_result
            )
            
            await safe_callback(TranslationUpdate(
                stage=TranslationStage.OPTIMIZED,
                translation=optimized_result.translation,
                quality_metrics=optimized_quality,
                progress=1.0,
                status_message="Optimization complete"
            ))
            
            # Create result directly with optimization applied
            total_time = time.time() - start_time
            stage_times = {"progressive_semantic_and_optimization": total_time}
            optimization_applied = optimized_quality.overall_score > quality_metrics.overall_score
            
            # Use optimized result if it's better, otherwise fall back to semantic
            final_translation = optimized_result.translation if optimization_applied else semantic_result.translation
            final_quality = optimized_quality if optimization_applied else quality_metrics
            final_chunking = optimized_result.chunking_result if optimization_applied else semantic_result.chunking_result
            
            # Cache the result
            if self.cache_manager:
                await self._cache_result(request, final_translation, final_quality, final_chunking)
            
            return TranslationResult(
                translation=final_translation,
                original_text=request.text,
                quality_metrics=final_quality,
                chunking_result=final_chunking,
                processing_time=total_time,
                cache_hit=False,
                optimization_applied=optimization_applied,
                stage_times=stage_times,
                metadata={
                    "user_preference": request.user_preference,
                    "needs_optimization": True,
                    "optimization_successful": optimization_applied,
                    "source_lang": request.source_lang,
                    "target_lang": request.target_lang
                }
            )
            
        except Exception as e:
            try:
                await safe_callback(TranslationUpdate(
                    stage=TranslationStage.ERROR,
                    status_message=f"Translation failed: {str(e)}",
                    progress=0.0
                ))
            except Exception:
                # If callback also fails, just log and continue
                logger.warning(f"Callback failed during error reporting: {e}")
            raise

    async def _check_cache(self, request: AdaptiveTranslationRequest) -> Optional[CacheEntry]:
        """Check cache for existing translation."""
        if not self.cache_manager:
            return None
        
        return await self.cache_manager.get_translation(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            optimization_level="optimized" if request.user_preference == "quality" else "semantic"
        )

    async def _semantic_translation_path(self, request: AdaptiveTranslationRequest) -> TranslationResult:
        """Perform semantic chunking and translation."""
        # 1. Semantic chunking
        chunking_result = await self.chunker.chunk_text(
            request.text, request.source_lang, request.target_lang
        )
        
        # 2. Translate chunks
        async with self.translation_semaphore:
            if len(chunking_result.chunks) == 1:
                # Single chunk - direct translation
                translation = await self.translation_function(
                    chunking_result.chunks[0], request.source_lang, request.target_lang, request.api_key
                )
            else:
                # Multiple chunks - parallel translation
                translation_tasks = [
                    self.translation_function(chunk, request.source_lang, request.target_lang, request.api_key)
                    for chunk in chunking_result.chunks
                ]
                
                translated_chunks = await asyncio.gather(*translation_tasks)
                translation = " ".join(translated_chunks)
        
        return TranslationResult(
            translation=translation,
            original_text=request.text,
            quality_metrics=None,  # Will be assessed separately
            chunking_result=chunking_result,
            processing_time=0.0,  # Will be calculated in main function
            cache_hit=False,
            optimization_applied=False,
            stage_times={},
            metadata={}
        )

    async def _optimization_path(self, 
                                request: AdaptiveTranslationRequest,
                                semantic_result: TranslationResult) -> TranslationResult:
        """Perform binary search optimization for better quality."""
        try:
            # Assess current quality
            current_quality = await self._assess_translation_quality(
                request.text, semantic_result.translation, semantic_result.chunking_result
            )
            
            # Determine optimization strategy based on user preference
            if request.user_preference == "quality":
                strategy = OptimizationStrategy.QUALITY_FOCUSED
            elif request.user_preference == "fast":
                strategy = OptimizationStrategy.SPEED_FOCUSED
            else:
                strategy = OptimizationStrategy.BALANCED
            
            # Perform binary search optimization
            optimization_result = await self.binary_optimizer.optimize_translation(
                text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                api_key=request.api_key,
                baseline_translation=semantic_result.translation,
                baseline_quality=current_quality.overall_score,
                strategy=strategy,
                timeout=request.max_optimization_time
            )
            
            # Create chunking result for the optimal chunk size
            optimal_chunker = SemanticChunker(
                min_chunk_size=max(optimization_result.optimal_chunk_size - 50, 100),
                max_chunk_size=optimization_result.optimal_chunk_size
            )
            
            optimal_chunking = await optimal_chunker.chunk_text(
                request.text, request.source_lang, request.target_lang
            )
            
            return TranslationResult(
                translation=optimization_result.optimal_translation,
                original_text=request.text,
                quality_metrics=None,  # Will be assessed in main function
                chunking_result=optimal_chunking,
                processing_time=optimization_result.total_optimization_time,
                cache_hit=False,
                optimization_applied=True,
                stage_times={},
                metadata={
                    "optimization_result": optimization_result,
                    "quality_improvement": optimization_result.quality_improvement,
                    "optimization_confidence": optimization_result.optimization_confidence,
                    "convergence_iterations": optimization_result.convergence_iterations
                }
            )
            
        except Exception as e:
            logger.warning(f"Binary search optimization failed: {e}, falling back to semantic result")
            return semantic_result

    async def _assess_translation_quality(self,
                                        original: str,
                                        translation: str,
                                        chunking_result: ChunkingResult) -> QualityMetrics:
        """Assess translation quality."""
        translation_pair = TranslationPair(
            original=original,
            translation=translation,
            chunks_original=chunking_result.chunks if chunking_result else None,
            chunks_translated=translation.split(" ") if " " in translation else [translation]
        )
        
        return await self.quality_engine.assess_quality(translation_pair)

    def _should_optimize(self,
                        quality_metrics: QualityMetrics,
                        user_preference: str,
                        force_optimization: bool) -> bool:
        """Determine if optimization should be applied."""
        if force_optimization:
            return True
        
        # User preference-based decisions take priority
        if user_preference == "fast":
            return False  # Fast preference avoids optimization even if quality is low
        elif user_preference == "quality" and quality_metrics.overall_score < 0.85:
            return True
        elif user_preference == "balanced" and quality_metrics.overall_score < 0.80:
            return True
        
        # Default quality threshold check
        if quality_metrics.overall_score < self.quality_threshold:
            return True
        
        return False

    async def _cache_result(self,
                          request: AdaptiveTranslationRequest,
                          translation: str,
                          quality_metrics: QualityMetrics,
                          chunking_result: ChunkingResult):
        """Cache the translation result."""
        if not self.cache_manager:
            return
        
        optimization_level = "optimized" if quality_metrics.overall_score > self.quality_threshold else "semantic"
        
        await self.cache_manager.store_translation(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            translation=translation,
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            content_type=chunking_result.content_type.value if chunking_result else None,
            optimization_level=optimization_level
        )

    def _create_result_from_cache(self,
                                cached_entry: CacheEntry,
                                start_time: float,
                                stage_times: Dict[str, float]) -> TranslationResult:
        """Create result from cached entry."""
        return TranslationResult(
            translation=cached_entry.translation,
            original_text="",  # Not stored in cache
            quality_metrics=cached_entry.quality_metrics,
            chunking_result=cached_entry.chunking_result,
            processing_time=time.time() - start_time,
            cache_hit=True,
            optimization_applied=cached_entry.key.optimization_level == "optimized",
            stage_times=stage_times,
            metadata={
                "cache_hit": True,
                "cached_timestamp": cached_entry.timestamp,
                "cache_access_count": cached_entry.access_count
            }
        )

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        cache_stats = await self.cache_manager.get_statistics() if self.cache_manager else None
        
        return {
            "controller_stats": self.performance_stats,
            "cache_stats": cache_stats,
            "quality_threshold": self.quality_threshold
        }