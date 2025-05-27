"""
Unit tests for the Adaptive Translation Controller.

Tests orchestration logic, progressive translation, and integration of all components.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from app.adaptive.adaptive_controller import (
    AdaptiveTranslationController,
    AdaptiveTranslationRequest,
    TranslationUpdate,
    TranslationResult,
    TranslationStage
)
from app.adaptive.semantic_chunker import ChunkingResult, ContentType
from app.adaptive.quality_assessment import QualityMetrics, QualityDimension
from app.adaptive.cache_manager import CacheEntry, CacheKey
from app.adaptive.binary_search_optimizer import OptimizationResult


class TestAdaptiveTranslationRequest:
    """Test AdaptiveTranslationRequest data class."""
    
    def test_request_creation(self):
        """Test request creation with required fields."""
        request = AdaptiveTranslationRequest(
            text="Hello world",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        assert request.text == "Hello world"
        assert request.source_lang == "en"
        assert request.target_lang == "fr"
        assert request.api_key == "test_key"
        assert request.user_preference == "balanced"  # Default
        assert request.force_optimization == False  # Default
        assert request.max_optimization_time == 5.0  # Default
    
    def test_request_with_custom_values(self):
        """Test request creation with custom values."""
        request = AdaptiveTranslationRequest(
            text="Custom text",
            source_lang="ru",
            target_lang="en",
            api_key="custom_key",
            user_preference="quality",
            force_optimization=True,
            max_optimization_time=10.0
        )
        
        assert request.user_preference == "quality"
        assert request.force_optimization == True
        assert request.max_optimization_time == 10.0


class TestTranslationUpdate:
    """Test TranslationUpdate data class."""
    
    def test_update_creation(self):
        """Test update creation with minimal fields."""
        update = TranslationUpdate(stage=TranslationStage.SEMANTIC)
        
        assert update.stage == TranslationStage.SEMANTIC
        assert update.translation is None
        assert update.quality_metrics is None
        assert update.progress == 0.0
        assert update.status_message == ""
        assert update.metadata is None
    
    def test_update_with_all_fields(self):
        """Test update creation with all fields."""
        quality_metrics = Mock()
        metadata = {"test": "data"}
        
        update = TranslationUpdate(
            stage=TranslationStage.OPTIMIZED,
            translation="test translation",
            quality_metrics=quality_metrics,
            progress=0.8,
            status_message="Optimization complete",
            metadata=metadata
        )
        
        assert update.stage == TranslationStage.OPTIMIZED
        assert update.translation == "test translation"
        assert update.quality_metrics == quality_metrics
        assert update.progress == 0.8
        assert update.status_message == "Optimization complete"
        assert update.metadata == metadata


class TestTranslationResult:
    """Test TranslationResult data class."""
    
    def test_result_creation(self):
        """Test result creation with all required fields."""
        quality_metrics = Mock()
        chunking_result = Mock()
        stage_times = {"semantic": 1.0, "optimization": 2.0}
        metadata = {"cache_hit": False}
        
        result = TranslationResult(
            translation="Final translation",
            original_text="Original text",
            quality_metrics=quality_metrics,
            chunking_result=chunking_result,
            processing_time=3.5,
            cache_hit=False,
            optimization_applied=True,
            stage_times=stage_times,
            metadata=metadata
        )
        
        assert result.translation == "Final translation"
        assert result.original_text == "Original text"
        assert result.quality_metrics == quality_metrics
        assert result.chunking_result == chunking_result
        assert result.processing_time == 3.5
        assert result.cache_hit == False
        assert result.optimization_applied == True
        assert result.stage_times == stage_times
        assert result.metadata == metadata


class TestAdaptiveTranslationController:
    """Test suite for AdaptiveTranslationController class."""
    
    @pytest.fixture
    def mock_translation_function(self):
        """Mock translation function."""
        async def translate(text, source_lang, target_lang, api_key):
            return f"translated({text})"
        return translate
    
    @pytest.fixture
    def mock_chunker(self):
        """Mock semantic chunker."""
        chunker = Mock()
        chunker.chunk_text = AsyncMock(return_value=ChunkingResult(
            chunks=["test chunk"],
            chunk_boundaries=[(0, 10)],
            content_type=ContentType.CONVERSATIONAL,
            coherence_score=0.8,
            optimal_size_estimate=300,
            metadata={}
        ))
        return chunker
    
    @pytest.fixture
    def mock_quality_engine(self):
        """Mock quality assessment engine."""
        engine = Mock()
        engine.assess_quality = AsyncMock(return_value=QualityMetrics(
            overall_score=0.85,
            dimension_scores={QualityDimension.CONFIDENCE: 0.8},
            confidence_interval=(0.7, 0.9),
            quality_grade="B",
            optimization_needed=False,
            improvement_suggestions=["Good quality"],
            metadata={}
        ))
        return engine
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager."""
        cache = Mock()
        cache.get_translation = AsyncMock(return_value=None)  # No cache hit by default
        cache.store_translation = AsyncMock()
        cache.get_statistics = AsyncMock(return_value=Mock())
        return cache
    
    @pytest.fixture
    def mock_binary_optimizer(self):
        """Mock binary search optimizer."""
        optimizer = Mock()
        optimizer.optimize_translation = AsyncMock(return_value=OptimizationResult(
            optimal_chunk_size=350,
            optimal_translation="optimized translation",
            optimal_quality_score=0.92,
            quality_improvement=0.07,
            confidence_interval=(0.85, 0.99),
            optimization_confidence=0.88,
            search_points=[],
            convergence_iterations=3,
            total_optimization_time=2.5,
            metadata={}
        ))
        return optimizer
    
    @pytest.fixture
    def controller(self, mock_translation_function, mock_chunker, mock_quality_engine, 
                  mock_cache_manager, mock_binary_optimizer):
        """Create adaptive translation controller with mocked dependencies."""
        return AdaptiveTranslationController(
            translation_function=mock_translation_function,
            chunker=mock_chunker,
            quality_engine=mock_quality_engine,
            cache_manager=mock_cache_manager,
            binary_optimizer=mock_binary_optimizer,
            quality_threshold=0.8
        )
    
    @pytest.mark.asyncio
    async def test_translate_basic(self, controller):
        """Test basic translation functionality."""
        request = AdaptiveTranslationRequest(
            text="Hello world",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller.translate(request)
        
        assert isinstance(result, TranslationResult)
        assert result.translation is not None
        assert result.original_text == "Hello world"
        assert result.quality_metrics is not None
        assert result.processing_time > 0
        assert result.cache_hit == False
        assert "semantic_translation" in result.stage_times
        assert "quality_assessment" in result.stage_times
    
    @pytest.mark.asyncio
    async def test_translate_with_cache_hit(self, controller, mock_cache_manager):
        """Test translation with cache hit."""
        # Mock cache hit
        cached_entry = CacheEntry(
            key=Mock(),
            translation="cached translation",
            quality_metrics=Mock(),
            chunking_result=Mock(),
            timestamp=time.time()
        )
        mock_cache_manager.get_translation.return_value = cached_entry
        
        request = AdaptiveTranslationRequest(
            text="Cached text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller.translate(request)
        
        assert result.translation == "cached translation"
        assert result.cache_hit == True
        assert result.processing_time > 0
        # Should have fast response from cache
    
    @pytest.mark.asyncio
    async def test_translate_with_optimization(self, controller, mock_quality_engine):
        """Test translation that triggers optimization."""
        # Mock quality engine to return different scores for semantic vs optimized
        low_quality = QualityMetrics(
            overall_score=0.6,  # Below threshold
            dimension_scores={QualityDimension.CONFIDENCE: 0.6},
            confidence_interval=(0.5, 0.7),
            quality_grade="D",
            optimization_needed=True,
            improvement_suggestions=["Needs optimization"],
            metadata={}
        )
        high_quality = QualityMetrics(
            overall_score=0.9,  # Improved after optimization
            dimension_scores={QualityDimension.CONFIDENCE: 0.9},
            confidence_interval=(0.85, 0.95),
            quality_grade="A",
            optimization_needed=False,
            improvement_suggestions=[],
            metadata={}
        )
        # Use a custom side_effect function to track calls
        call_count = 0
        def quality_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return low_quality  # First call: semantic translation assessment
            else:
                return high_quality  # All subsequent calls: optimized translation assessment
        
        mock_quality_engine.assess_quality.side_effect = quality_side_effect
        
        request = AdaptiveTranslationRequest(
            text="Text needing optimization",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            user_preference="quality"
        )
        
        result = await controller.translate(request)
        
        assert result.optimization_applied == True
        assert "optimization" in result.stage_times
        assert result.quality_metrics.overall_score == 0.9  # Should be improved
    
    @pytest.mark.asyncio
    async def test_translate_force_optimization(self, controller, mock_quality_engine):
        """Test translation with forced optimization."""
        # Mock quality to show improvement after optimization
        initial_quality = QualityMetrics(
            overall_score=0.7,  # Decent quality
            dimension_scores={QualityDimension.CONFIDENCE: 0.7},
            confidence_interval=(0.6, 0.8),
            quality_grade="C",
            optimization_needed=False,
            improvement_suggestions=[],
            metadata={}
        )
        improved_quality = QualityMetrics(
            overall_score=0.95,  # Much improved after optimization
            dimension_scores={QualityDimension.CONFIDENCE: 0.95},
            confidence_interval=(0.9, 1.0),
            quality_grade="A+",
            optimization_needed=False,
            improvement_suggestions=[],
            metadata={}
        )
        # Use a custom side_effect function to track calls
        call_count = 0
        def quality_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return initial_quality  # First call: semantic translation assessment
            else:
                return improved_quality  # All subsequent calls: optimized translation assessment
        
        mock_quality_engine.assess_quality.side_effect = quality_side_effect
        
        request = AdaptiveTranslationRequest(
            text="Text with forced optimization",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            force_optimization=True
        )
        
        result = await controller.translate(request)
        
        assert result.optimization_applied == True
        assert "optimization" in result.stage_times
    
    @pytest.mark.asyncio
    async def test_progressive_translate(self, controller):
        """Test progressive translation with callback updates."""
        updates = []
        
        async def update_callback(update):
            updates.append(update)
        
        request = AdaptiveTranslationRequest(
            text="Progressive translation test",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller.progressive_translate(request, update_callback)
        
        assert isinstance(result, TranslationResult)
        assert len(updates) > 0
        # Should have received progress updates
        stages = [update.stage for update in updates]
        assert TranslationStage.SEMANTIC in stages
    
    @pytest.mark.asyncio
    async def test_progressive_translate_with_cache(self, controller, mock_cache_manager):
        """Test progressive translation with cache hit."""
        cached_entry = CacheEntry(
            key=Mock(),
            translation="cached progressive",
            quality_metrics=Mock(),
            chunking_result=Mock(),
            timestamp=time.time()
        )
        mock_cache_manager.get_translation.return_value = cached_entry
        
        updates = []
        async def update_callback(update):
            updates.append(update)
        
        request = AdaptiveTranslationRequest(
            text="Cached progressive text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller.progressive_translate(request, update_callback)
        
        assert result.cache_hit == True
        assert len(updates) > 0
        # Should still provide updates even for cached results
    
    @pytest.mark.asyncio
    async def test_progressive_translate_with_optimization(self, controller, mock_quality_engine):
        """Test progressive translation that triggers optimization."""
        # Mock low quality first, then high quality after optimization
        # Progressive translate calls assess_quality multiple times due to internal translate() calls
        low_quality = QualityMetrics(
            overall_score=0.6,
            dimension_scores={QualityDimension.CONFIDENCE: 0.6},
            confidence_interval=(0.5, 0.7),
            quality_grade="D",
            optimization_needed=True,
            improvement_suggestions=["Needs optimization"],
            metadata={}
        )
        high_quality = QualityMetrics(
            overall_score=0.9,
            dimension_scores={QualityDimension.CONFIDENCE: 0.9},
            confidence_interval=(0.8, 1.0),
            quality_grade="A",
            optimization_needed=False,
            improvement_suggestions=["Excellent"],
            metadata={}
        )
        # Use a custom side_effect function to track calls
        call_count = 0
        def quality_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return low_quality  # First call: semantic translation assessment
            else:
                return high_quality  # All subsequent calls: optimized translation assessment
        
        mock_quality_engine.assess_quality.side_effect = quality_side_effect
        
        updates = []
        async def update_callback(update):
            updates.append(update)
        
        request = AdaptiveTranslationRequest(
            text="Text for progressive optimization",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            user_preference="quality"
        )
        
        result = await controller.progressive_translate(request, update_callback)
        
        assert result.optimization_applied == True
        
        # Should have progression of stages
        stages = [update.stage for update in updates]
        assert TranslationStage.SEMANTIC in stages
        assert TranslationStage.ANALYZING in stages
        assert TranslationStage.OPTIMIZING in stages
        assert TranslationStage.OPTIMIZED in stages
    
    @pytest.mark.asyncio
    async def test_check_cache(self, controller, mock_cache_manager):
        """Test cache checking functionality."""
        request = AdaptiveTranslationRequest(
            text="Cache check test",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller._check_cache(request)
        
        assert result is None  # No cache hit
        mock_cache_manager.get_translation.assert_called_once_with(
            text="Cache check test",
            source_lang="en",
            target_lang="fr",
            optimization_level="semantic"
        )
    
    @pytest.mark.asyncio
    async def test_check_cache_quality_preference(self, controller, mock_cache_manager):
        """Test cache checking with quality preference."""
        request = AdaptiveTranslationRequest(
            text="Quality cache test",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            user_preference="quality"
        )
        
        await controller._check_cache(request)
        
        mock_cache_manager.get_translation.assert_called_once_with(
            text="Quality cache test",
            source_lang="en",
            target_lang="fr",
            optimization_level="optimized"  # Should request optimized for quality
        )
    
    @pytest.mark.asyncio
    async def test_semantic_translation_path_single_chunk(self, controller, mock_chunker, mock_translation_function):
        """Test semantic translation path with single chunk."""
        # Mock single chunk result
        mock_chunker.chunk_text.return_value = ChunkingResult(
            chunks=["single chunk text"],
            chunk_boundaries=[(0, 17)],
            content_type=ContentType.CONVERSATIONAL,
            coherence_score=1.0,
            optimal_size_estimate=300,
            metadata={}
        )
        
        request = AdaptiveTranslationRequest(
            text="single chunk text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller._semantic_translation_path(request)
        
        assert isinstance(result, TranslationResult)
        assert result.translation == "translated(single chunk text)"
        assert result.chunking_result.chunks == ["single chunk text"]
    
    @pytest.mark.asyncio
    async def test_semantic_translation_path_multiple_chunks(self, controller, mock_chunker):
        """Test semantic translation path with multiple chunks."""
        # Mock multiple chunks result
        mock_chunker.chunk_text.return_value = ChunkingResult(
            chunks=["chunk1", "chunk2", "chunk3"],
            chunk_boundaries=[(0, 6), (7, 13), (14, 20)],
            content_type=ContentType.NARRATIVE,
            coherence_score=0.85,
            optimal_size_estimate=350,
            metadata={}
        )
        
        request = AdaptiveTranslationRequest(
            text="chunk1 chunk2 chunk3",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller._semantic_translation_path(request)
        
        assert isinstance(result, TranslationResult)
        # Should be joined translated chunks
        assert result.translation == "translated(chunk1) translated(chunk2) translated(chunk3)"
        assert len(result.chunking_result.chunks) == 3
    
    @pytest.mark.asyncio
    async def test_optimization_path(self, controller, mock_binary_optimizer):
        """Test optimization path execution."""
        semantic_result = TranslationResult(
            translation="semantic translation",
            original_text="test text",
            quality_metrics=None,
            chunking_result=Mock(),
            processing_time=1.0,
            cache_hit=False,
            optimization_applied=False,
            stage_times={},
            metadata={}
        )
        
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            user_preference="balanced"
        )
        
        result = await controller._optimization_path(request, semantic_result)
        
        assert isinstance(result, TranslationResult)
        assert result.optimization_applied == True
        assert result.translation == "optimized translation"
        mock_binary_optimizer.optimize_translation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimization_path_quality_strategy(self, controller, mock_binary_optimizer):
        """Test optimization path with quality strategy."""
        semantic_result = TranslationResult(
            translation="semantic translation",
            original_text="test text",
            quality_metrics=None,
            chunking_result=Mock(),
            processing_time=1.0,
            cache_hit=False,
            optimization_applied=False,
            stage_times={},
            metadata={}
        )
        
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            user_preference="quality"  # Quality-focused strategy
        )
        
        await controller._optimization_path(request, semantic_result)
        
        # Verify optimization was called with quality strategy
        call_args = mock_binary_optimizer.optimize_translation.call_args[1]
        assert call_args["strategy"].value == "quality"
    
    @pytest.mark.asyncio
    async def test_optimization_path_failure(self, controller, mock_binary_optimizer):
        """Test optimization path when optimization fails."""
        mock_binary_optimizer.optimize_translation.side_effect = Exception("Optimization failed")
        
        semantic_result = TranslationResult(
            translation="semantic translation",
            original_text="test text",
            quality_metrics=None,
            chunking_result=Mock(),
            processing_time=1.0,
            cache_hit=False,
            optimization_applied=False,
            stage_times={},
            metadata={}
        )
        
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await controller._optimization_path(request, semantic_result)
        
        # Should fall back to semantic result
        assert result == semantic_result
    
    def test_should_optimize_force_optimization(self, controller):
        """Test optimization decision with force flag."""
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.9  # High quality
        
        should_optimize = controller._should_optimize(
            quality_metrics, "balanced", force_optimization=True
        )
        
        assert should_optimize == True
    
    def test_should_optimize_below_threshold(self, controller):
        """Test optimization decision with quality below threshold."""
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.7  # Below 0.8 threshold
        
        should_optimize = controller._should_optimize(
            quality_metrics, "balanced", force_optimization=False
        )
        
        assert should_optimize == True
    
    def test_should_optimize_quality_preference(self, controller):
        """Test optimization decision with quality preference."""
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.82  # Above threshold but below quality standard
        
        should_optimize = controller._should_optimize(
            quality_metrics, "quality", force_optimization=False
        )
        
        assert should_optimize == True  # Quality preference has higher standard
    
    def test_should_optimize_fast_preference(self, controller):
        """Test optimization decision with fast preference."""
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.7  # Below threshold
        
        should_optimize = controller._should_optimize(
            quality_metrics, "fast", force_optimization=False
        )
        
        assert should_optimize == False  # Fast preference avoids optimization
    
    def test_should_optimize_balanced_above_threshold(self, controller):
        """Test optimization decision with balanced preference above threshold."""
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.85  # Above threshold
        
        should_optimize = controller._should_optimize(
            quality_metrics, "balanced", force_optimization=False
        )
        
        assert should_optimize == False
    
    @pytest.mark.asyncio
    async def test_cache_result(self, controller, mock_cache_manager):
        """Test caching of translation result."""
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.85
        
        chunking_result = Mock()
        chunking_result.content_type = ContentType.CONVERSATIONAL
        
        await controller._cache_result(request, "translation", quality_metrics, chunking_result)
        
        mock_cache_manager.store_translation.assert_called_once()
        call_args = mock_cache_manager.store_translation.call_args[1]
        assert call_args["text"] == "test text"
        assert call_args["translation"] == "translation"
        assert call_args["optimization_level"] == "optimized"  # Above threshold
    
    @pytest.mark.asyncio
    async def test_cache_result_below_threshold(self, controller, mock_cache_manager):
        """Test caching result below quality threshold."""
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        quality_metrics = Mock()
        quality_metrics.overall_score = 0.7  # Below threshold
        
        chunking_result = Mock()
        chunking_result.content_type = ContentType.CONVERSATIONAL
        
        await controller._cache_result(request, "translation", quality_metrics, chunking_result)
        
        call_args = mock_cache_manager.store_translation.call_args[1]
        assert call_args["optimization_level"] == "semantic"  # Below threshold
    
    def test_create_result_from_cache(self, controller):
        """Test creating result from cached entry."""
        cached_entry = CacheEntry(
            key=Mock(),
            translation="cached translation",
            quality_metrics=Mock(),
            chunking_result=Mock(),
            timestamp=1234567890,
            access_count=5,
            hit_count=3
        )
        cached_entry.key.optimization_level = "optimized"
        
        start_time = time.time() - 0.1
        stage_times = {"cache_lookup": 0.05}
        
        result = controller._create_result_from_cache(cached_entry, start_time, stage_times)
        
        assert isinstance(result, TranslationResult)
        assert result.translation == "cached translation"
        assert result.cache_hit == True
        assert result.optimization_applied == True  # From optimized level
        assert result.metadata["cache_hit"] == True
        assert result.metadata["cached_timestamp"] == 1234567890
        assert result.metadata["cache_access_count"] == 5
    
    @pytest.mark.asyncio
    async def test_get_performance_stats(self, controller, mock_cache_manager):
        """Test performance statistics retrieval."""
        # Set up some controller stats
        controller.performance_stats["total_requests"] = 100
        controller.performance_stats["cache_hits"] = 80
        
        # Mock cache stats
        mock_cache_stats = Mock()
        mock_cache_manager.get_statistics.return_value = mock_cache_stats
        
        stats = await controller.get_performance_stats()
        
        assert "controller_stats" in stats
        assert "cache_stats" in stats
        assert "quality_threshold" in stats
        assert stats["controller_stats"]["total_requests"] == 100
        assert stats["cache_stats"] == mock_cache_stats
        assert stats["quality_threshold"] == 0.8
    
    @pytest.mark.asyncio
    async def test_get_performance_stats_no_cache(self, controller):
        """Test performance statistics without cache manager."""
        controller.cache_manager = None
        
        stats = await controller.get_performance_stats()
        
        assert "controller_stats" in stats
        assert stats["cache_stats"] is None
        assert "quality_threshold" in stats


class TestAdaptiveControllerEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def minimal_controller(self):
        """Create controller with minimal configuration."""
        async def simple_translate(text, source_lang, target_lang, api_key):
            return f"simple({text})"
        
        return AdaptiveTranslationController(
            translation_function=simple_translate,
            quality_threshold=0.5
        )
    
    @pytest.mark.asyncio
    async def test_translate_empty_text(self, minimal_controller):
        """Test translation with empty text."""
        request = AdaptiveTranslationRequest(
            text="",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await minimal_controller.translate(request)
        
        assert isinstance(result, TranslationResult)
        # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_translate_translation_function_failure(self, minimal_controller):
        """Test translation when translation function fails."""
        async def failing_translate(text, source_lang, target_lang, api_key):
            raise Exception("Translation service unavailable")
        
        minimal_controller.translation_function = failing_translate
        
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        with pytest.raises(Exception):
            await minimal_controller.translate(request)
    
    @pytest.mark.asyncio
    async def test_progressive_translate_callback_exception(self, minimal_controller):
        """Test progressive translation when callback raises exception."""
        async def failing_callback(update):
            raise Exception("Callback failed")
        
        request = AdaptiveTranslationRequest(
            text="test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        # Should handle callback exception gracefully
        result = await minimal_controller.progressive_translate(request, failing_callback)
        assert isinstance(result, TranslationResult)
    
    @pytest.mark.asyncio
    async def test_assess_translation_quality_no_chunking(self, minimal_controller):
        """Test quality assessment without chunking result."""
        result = await minimal_controller._assess_translation_quality(
            "original", "translation", None
        )
        
        assert isinstance(result, QualityMetrics)
        # Should handle None chunking result
    
    @pytest.mark.asyncio
    async def test_concurrent_translations(self, minimal_controller):
        """Test concurrent translation requests."""
        requests = [
            AdaptiveTranslationRequest(
                text=f"test text {i}",
                source_lang="en",
                target_lang="fr",
                api_key="test_key"
            )
            for i in range(5)
        ]
        
        # Run concurrent translations
        tasks = [minimal_controller.translate(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(isinstance(result, TranslationResult) for result in results)
    
    @pytest.mark.asyncio
    async def test_translation_with_none_cache_manager(self, minimal_controller):
        """Test translation when cache manager is None."""
        minimal_controller.cache_manager = None
        
        request = AdaptiveTranslationRequest(
            text="test without cache",
            source_lang="en",
            target_lang="fr",
            api_key="test_key"
        )
        
        result = await minimal_controller.translate(request)
        
        assert isinstance(result, TranslationResult)
        assert result.cache_hit == False
        # Should work without caching