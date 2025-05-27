"""
Binary Search Optimizer

Implements intelligent binary search optimization for finding optimal chunk sizes
with parallel processing and confidence interval analysis.
"""

import asyncio
import logging
import time
import statistics
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

from .semantic_chunker import SemanticChunker, ChunkingResult
from .quality_assessment import QualityMetricsEngine, QualityMetrics, TranslationPair

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Binary search optimization strategies."""
    QUALITY_FOCUSED = "quality"      # Prioritize quality improvement
    BALANCED = "balanced"            # Balance quality and speed
    SPEED_FOCUSED = "speed"          # Prioritize fast convergence


@dataclass
class OptimizationPoint:
    """Single optimization data point."""
    chunk_size: int
    quality_score: float
    translation: str
    chunking_result: ChunkingResult
    processing_time: float
    confidence: float = 0.0


@dataclass
class OptimizationResult:
    """Result of binary search optimization."""
    optimal_chunk_size: int
    optimal_translation: str
    optimal_quality_score: float
    quality_improvement: float
    confidence_interval: Tuple[float, float]
    optimization_confidence: float
    search_points: List[OptimizationPoint]
    convergence_iterations: int
    total_optimization_time: float
    metadata: Dict[str, Any]


class BinarySearchOptimizer:
    """
    Advanced binary search optimizer for finding optimal chunk sizes
    with parallel processing and statistical confidence analysis.
    """
    
    def __init__(self,
                 translation_function: Callable,
                 chunker: Optional[SemanticChunker] = None,
                 quality_engine: Optional[QualityMetricsEngine] = None,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 800,
                 convergence_threshold: float = 0.02,
                 max_iterations: int = 8,
                 parallel_evaluations: int = 3):
        """
        Initialize the binary search optimizer.
        
        Args:
            translation_function: Function to perform translations
            chunker: Semantic chunker instance
            quality_engine: Quality assessment engine
            min_chunk_size: Minimum chunk size to test
            max_chunk_size: Maximum chunk size to test
            convergence_threshold: Quality improvement threshold for convergence
            max_iterations: Maximum search iterations
            parallel_evaluations: Number of parallel evaluations per iteration
        """
        self.translation_function = translation_function
        self.chunker = chunker or SemanticChunker()
        self.quality_engine = quality_engine or QualityMetricsEngine()
        
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.convergence_threshold = convergence_threshold
        self.max_iterations = max_iterations
        self.parallel_evaluations = parallel_evaluations
        
        # Optimization statistics
        self.optimization_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "avg_improvement": 0.0,
            "avg_optimization_time": 0.0
        }

    async def optimize_translation(self,
                                 text: str,
                                 source_lang: str,
                                 target_lang: str,
                                 api_key: str,
                                 baseline_translation: str,
                                 baseline_quality: float,
                                 strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
                                 timeout: float = 10.0) -> OptimizationResult:
        """
        Perform binary search optimization to find optimal chunk size.
        
        Args:
            text: Original text to optimize
            source_lang: Source language
            target_lang: Target language
            api_key: API key for translation service
            baseline_translation: Current translation for comparison
            baseline_quality: Current quality score
            strategy: Optimization strategy
            timeout: Maximum optimization time
            
        Returns:
            OptimizationResult with optimal parameters and confidence metrics
        """
        start_time = time.time()
        self.optimization_stats["total_optimizations"] += 1
        
        try:
            # 1. Sample quality curve at strategic points
            sample_points = await asyncio.wait_for(
                self._sample_quality_curve(text, source_lang, target_lang, api_key, strategy),
                timeout=timeout * 0.6
            )
            
            if not sample_points:
                return self._create_failed_result(baseline_translation, baseline_quality, start_time, strategy)
            
            # 2. Identify optimal region
            optimal_region = self._identify_optimal_region(sample_points, baseline_quality)
            
            if not optimal_region:
                return self._create_failed_result(baseline_translation, baseline_quality, start_time, strategy)
            
            # 3. Fine-tune within optimal region
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time > 1.0:
                fine_tuned_result = await asyncio.wait_for(
                    self._fine_tune_in_region(
                        text, source_lang, target_lang, api_key, optimal_region, sample_points
                    ),
                    timeout=remaining_time
                )
            else:
                fine_tuned_result = max(sample_points, key=lambda p: p.quality_score)
            
            # 4. Calculate optimization confidence
            optimization_confidence = self._calculate_optimization_confidence(
                sample_points, fine_tuned_result
            )
            
            # 5. Create result
            quality_improvement = fine_tuned_result.quality_score - baseline_quality
            
            if quality_improvement > self.convergence_threshold:
                self.optimization_stats["successful_optimizations"] += 1
                self.optimization_stats["avg_improvement"] = (
                    self.optimization_stats["avg_improvement"] + quality_improvement
                ) / 2
            
            total_time = time.time() - start_time
            self.optimization_stats["avg_optimization_time"] = (
                self.optimization_stats["avg_optimization_time"] + total_time
            ) / 2
            
            return OptimizationResult(
                optimal_chunk_size=fine_tuned_result.chunk_size,
                optimal_translation=fine_tuned_result.translation,
                optimal_quality_score=fine_tuned_result.quality_score,
                quality_improvement=quality_improvement,
                confidence_interval=self._calculate_confidence_interval(sample_points),
                optimization_confidence=optimization_confidence,
                search_points=sample_points,
                convergence_iterations=len(sample_points),
                total_optimization_time=total_time,
                metadata={
                    "strategy": strategy.value,
                    "baseline_quality": baseline_quality,
                    "region_identified": optimal_region is not None,
                    "timeout_reached": total_time >= timeout * 0.9
                }
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"Optimization timeout after {timeout}s")
            return self._create_failed_result(baseline_translation, baseline_quality, start_time, strategy)
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return self._create_failed_result(baseline_translation, baseline_quality, start_time, strategy)

    async def _sample_quality_curve(self,
                                  text: str,
                                  source_lang: str,
                                  target_lang: str,
                                  api_key: str,
                                  strategy: OptimizationStrategy) -> List[OptimizationPoint]:
        """Sample quality curve at strategic points."""
        # Define sampling points based on strategy
        if strategy == OptimizationStrategy.QUALITY_FOCUSED:
            # More points for thorough exploration
            sample_sizes = [150, 250, 350, 450, 550, 650]
        elif strategy == OptimizationStrategy.SPEED_FOCUSED:
            # Fewer points for quick optimization
            sample_sizes = [200, 400, 600]
        else:  # BALANCED
            # Balanced sampling
            sample_sizes = [150, 300, 450, 600]
        
        # Filter sizes within bounds
        sample_sizes = [size for size in sample_sizes 
                       if self.min_chunk_size <= size <= self.max_chunk_size]
        
        # Evaluate points in parallel
        tasks = []
        for chunk_size in sample_sizes:
            task = self._evaluate_chunk_size(text, source_lang, target_lang, api_key, chunk_size)
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful results
            sample_points = []
            for result in results:
                if isinstance(result, OptimizationPoint):
                    sample_points.append(result)
                else:
                    logger.warning(f"Sample evaluation failed: {result}")
            
            return sample_points
            
        except Exception as e:
            logger.error(f"Quality curve sampling failed: {e}")
            return []

    async def _evaluate_chunk_size(self,
                                 text: str,
                                 source_lang: str,
                                 target_lang: str,
                                 api_key: str,
                                 chunk_size: int) -> OptimizationPoint:
        """Evaluate translation quality for a specific chunk size."""
        eval_start = time.time()
        
        try:
            # Create chunker with specific size
            temp_chunker = SemanticChunker(
                min_chunk_size=max(chunk_size - 50, self.min_chunk_size),
                max_chunk_size=chunk_size
            )
            
            # Perform chunking
            chunking_result = await temp_chunker.chunk_text(text, source_lang, target_lang)
            
            # Translate chunks
            if len(chunking_result.chunks) == 1:
                translation = await self.translation_function(
                    chunking_result.chunks[0], source_lang, target_lang, api_key
                )
            else:
                # Parallel translation of chunks
                translation_tasks = [
                    self.translation_function(chunk, source_lang, target_lang, api_key)
                    for chunk in chunking_result.chunks
                ]
                translated_chunks = await asyncio.gather(*translation_tasks)
                translation = " ".join(translated_chunks)
            
            # Assess quality
            translation_pair = TranslationPair(
                original=text,
                translation=translation,
                chunks_original=chunking_result.chunks,
                language_pair=(source_lang, target_lang)
            )
            
            quality_metrics = await self.quality_engine.assess_quality(translation_pair)
            
            processing_time = time.time() - eval_start
            
            return OptimizationPoint(
                chunk_size=chunk_size,
                quality_score=quality_metrics.overall_score,
                translation=translation,
                chunking_result=chunking_result,
                processing_time=processing_time,
                confidence=1.0 - abs(quality_metrics.confidence_interval[1] - quality_metrics.confidence_interval[0])
            )
            
        except Exception as e:
            logger.warning(f"Chunk size {chunk_size} evaluation failed: {e}")
            raise

    def _identify_optimal_region(self,
                               sample_points: List[OptimizationPoint],
                               baseline_quality: float) -> Optional[Tuple[int, int]]:
        """Identify the region with highest quality potential."""
        if len(sample_points) < 2:
            return None
        
        # Sort by chunk size
        sorted_points = sorted(sample_points, key=lambda p: p.chunk_size)
        
        # Find points that improve over baseline
        improving_points = [p for p in sorted_points if p.quality_score > baseline_quality]
        
        if not improving_points:
            # If no improvements, find the best point and create region around it
            best_point = max(sorted_points, key=lambda p: p.quality_score)
            margin = 100
            return (
                max(best_point.chunk_size - margin, self.min_chunk_size),
                min(best_point.chunk_size + margin, self.max_chunk_size)
            )
        
        # Find the region with consistently high quality
        best_start = min(improving_points, key=lambda p: p.chunk_size).chunk_size
        best_end = max(improving_points, key=lambda p: p.chunk_size).chunk_size
        
        # Expand region slightly for fine-tuning
        margin = 50
        return (
            max(best_start - margin, self.min_chunk_size),
            min(best_end + margin, self.max_chunk_size)
        )

    async def _fine_tune_in_region(self,
                                 text: str,
                                 source_lang: str,
                                 target_lang: str,
                                 api_key: str,
                                 region: Tuple[int, int],
                                 existing_points: List[OptimizationPoint]) -> OptimizationPoint:
        """Fine-tune optimization within the identified region."""
        region_start, region_end = region
        
        # Check if we already have points in this region
        region_points = [p for p in existing_points 
                        if region_start <= p.chunk_size <= region_end]
        
        if region_points:
            # Return the best existing point in region
            return max(region_points, key=lambda p: p.quality_score)
        
        # Binary search within region
        left, right = region_start, region_end
        best_point = None
        
        for iteration in range(min(3, self.max_iterations)):  # Limited iterations for fine-tuning
            if right - left < 50:  # Converged
                break
            
            # Test midpoint
            mid_size = (left + right) // 2
            
            try:
                mid_point = await self._evaluate_chunk_size(
                    text, source_lang, target_lang, api_key, mid_size
                )
                
                if best_point is None or mid_point.quality_score > best_point.quality_score:
                    best_point = mid_point
                
                # Decide search direction based on surrounding points
                # Simple heuristic: if quality is good, search around this point
                if mid_point.quality_score > 0.8:  # High quality threshold
                    # Narrow search around this point
                    margin = (right - left) // 4
                    left = max(left, mid_size - margin)
                    right = min(right, mid_size + margin)
                else:
                    # Continue binary search
                    if iteration % 2 == 0:
                        left = mid_size
                    else:
                        right = mid_size
                        
            except Exception as e:
                logger.warning(f"Fine-tuning iteration {iteration} failed: {e}")
                break
        
        return best_point or existing_points[0]  # Fallback to first point

    def _calculate_optimization_confidence(self,
                                         sample_points: List[OptimizationPoint],
                                         optimal_point: OptimizationPoint) -> float:
        """Calculate confidence in the optimization result."""
        if len(sample_points) < 2:
            return 0.5
        
        # Factors affecting confidence:
        # 1. Number of sample points (more = higher confidence)
        # 2. Quality score consistency (lower variance = higher confidence)
        # 3. Clear optimum (peak vs plateau)
        # 4. Processing time consistency
        
        scores = [p.quality_score for p in sample_points]
        
        # Sample diversity score
        diversity_score = min(1.0, len(sample_points) / 5.0)
        
        # Quality consistency score (lower variance = higher confidence)
        if len(scores) > 1:
            score_variance = statistics.variance(scores)
            consistency_score = max(0.0, 1.0 - score_variance * 4)  # Scale variance
        else:
            consistency_score = 0.5
        
        # Optimum clarity (how much better is optimal vs average)
        avg_score = statistics.mean(scores)
        if avg_score > 0:
            clarity_score = min(1.0, (optimal_point.quality_score - avg_score) / avg_score * 2)
        else:
            clarity_score = 0.5
        
        # Weighted combination
        confidence = (
            diversity_score * 0.3 +
            consistency_score * 0.4 +
            clarity_score * 0.3
        )
        
        return max(0.0, min(1.0, confidence))

    def _calculate_confidence_interval(self,
                                     sample_points: List[OptimizationPoint]) -> Tuple[float, float]:
        """Calculate confidence interval for quality scores."""
        if len(sample_points) < 2:
            return (0.0, 1.0)
        
        scores = [p.quality_score for p in sample_points]
        mean_score = statistics.mean(scores)
        
        if len(scores) > 2:
            std_dev = statistics.stdev(scores)
            # 95% confidence interval approximation
            margin = 1.96 * std_dev / (len(scores) ** 0.5)
        else:
            margin = 0.1  # Default margin for small samples
        
        return (
            max(0.0, mean_score - margin),
            min(1.0, mean_score + margin)
        )

    def _create_failed_result(self,
                            baseline_translation: str,
                            baseline_quality: float,
                            start_time: float,
                            strategy: OptimizationStrategy) -> OptimizationResult:
        """Create result for failed optimization."""
        return OptimizationResult(
            optimal_chunk_size=300,  # Default safe chunk size
            optimal_translation=baseline_translation,
            optimal_quality_score=baseline_quality,
            quality_improvement=0.0,
            confidence_interval=(0.0, 1.0),
            optimization_confidence=0.0,
            search_points=[],
            convergence_iterations=0,
            total_optimization_time=time.time() - start_time,
            metadata={
                "optimization_failed": True,
                "strategy": strategy.value
            }
        )

    async def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization performance statistics."""
        success_rate = 0.0
        if self.optimization_stats["total_optimizations"] > 0:
            success_rate = (self.optimization_stats["successful_optimizations"] / 
                          self.optimization_stats["total_optimizations"])
        
        return {
            **self.optimization_stats,
            "success_rate": success_rate,
            "convergence_threshold": self.convergence_threshold,
            "max_iterations": self.max_iterations,
            "chunk_size_range": (self.min_chunk_size, self.max_chunk_size)
        }


# Utility functions for external use
async def optimize_chunk_size(text: str,
                            source_lang: str,
                            target_lang: str,
                            api_key: str,
                            translation_function: Callable,
                            baseline_translation: str,
                            baseline_quality: float,
                            optimizer: Optional[BinarySearchOptimizer] = None) -> OptimizationResult:
    """
    Convenience function for chunk size optimization.
    
    Args:
        text: Original text
        source_lang: Source language
        target_lang: Target language
        api_key: API key
        translation_function: Translation function
        baseline_translation: Current translation
        baseline_quality: Current quality score
        optimizer: Optional pre-initialized optimizer
        
    Returns:
        OptimizationResult with optimal parameters
    """
    if optimizer is None:
        optimizer = BinarySearchOptimizer(translation_function)
    
    return await optimizer.optimize_translation(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang,
        api_key=api_key,
        baseline_translation=baseline_translation,
        baseline_quality=baseline_quality
    )