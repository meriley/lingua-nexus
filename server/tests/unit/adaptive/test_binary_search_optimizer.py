"""
Unit tests for the Binary Search Optimizer.

Tests optimization strategies, chunk size optimization, and confidence analysis.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import time

from app.adaptive.binary_search_optimizer import (
    BinarySearchOptimizer,
    OptimizationStrategy,
    OptimizationPoint,
    OptimizationResult,
    optimize_chunk_size
)
from app.adaptive.semantic_chunker import ChunkingResult, ContentType
from app.adaptive.quality_assessment import QualityMetrics, QualityDimension


class TestBinarySearchOptimizer:
    """Test suite for BinarySearchOptimizer class."""
    
    @pytest.fixture
    def mock_translation_function(self):
        """Mock translation function."""
        async def translate(text, source_lang, target_lang, api_key):
            # Simple mock: return reversed text
            return text[::-1]
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
    def optimizer(self, mock_translation_function, mock_chunker, mock_quality_engine):
        """Create binary search optimizer with mocked dependencies."""
        return BinarySearchOptimizer(
            translation_function=mock_translation_function,
            chunker=mock_chunker,
            quality_engine=mock_quality_engine,
            min_chunk_size=100,
            max_chunk_size=600,
            max_iterations=3,
            parallel_evaluations=2
        )
    
    @pytest.mark.asyncio
    async def test_optimize_translation_basic(self, optimizer):
        """Test basic optimization functionality."""
        result = await optimizer.optimize_translation(
            text="This is a test text for optimization",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="baseline translation",
            baseline_quality=0.7,
            strategy=OptimizationStrategy.BALANCED,
            timeout=5.0
        )
        
        assert isinstance(result, OptimizationResult)
        assert 100 <= result.optimal_chunk_size <= 600
        assert result.optimal_translation is not None
        assert 0.0 <= result.optimal_quality_score <= 1.0
        assert 0.0 <= result.optimization_confidence <= 1.0
        assert result.total_optimization_time > 0
        assert len(result.search_points) > 0
    
    @pytest.mark.asyncio
    async def test_optimization_strategies(self, optimizer):
        """Test different optimization strategies."""
        strategies = [
            OptimizationStrategy.QUALITY_FOCUSED,
            OptimizationStrategy.BALANCED,
            OptimizationStrategy.SPEED_FOCUSED
        ]
        
        for strategy in strategies:
            result = await optimizer.optimize_translation(
                text="Test text",
                source_lang="en",
                target_lang="fr",
                api_key="test_key",
                baseline_translation="baseline",
                baseline_quality=0.6,
                strategy=strategy,
                timeout=2.0
            )
            
            assert isinstance(result, OptimizationResult)
            assert result.metadata["strategy"] == strategy.value
    
    @pytest.mark.asyncio
    async def test_sample_quality_curve(self, optimizer):
        """Test quality curve sampling."""
        # Mock varying quality scores for different chunk sizes
        def mock_quality_by_size(chunk_size):
            # Simulate better quality for medium sizes
            if 200 <= chunk_size <= 400:
                return 0.9
            else:
                return 0.7
        
        optimizer.quality_engine.assess_quality = AsyncMock(
            side_effect=lambda pair: QualityMetrics(
                overall_score=mock_quality_by_size(300),  # Default medium quality
                dimension_scores={QualityDimension.CONFIDENCE: 0.8},
                confidence_interval=(0.7, 0.9),
                quality_grade="B",
                optimization_needed=False,
                improvement_suggestions=[],
                metadata={}
            )
        )
        
        sample_points = await optimizer._sample_quality_curve(
            text="Test text for sampling",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            strategy=OptimizationStrategy.BALANCED
        )
        
        assert len(sample_points) > 0
        assert all(isinstance(point, OptimizationPoint) for point in sample_points)
        assert all(100 <= point.chunk_size <= 600 for point in sample_points)
        assert all(0.0 <= point.quality_score <= 1.0 for point in sample_points)
    
    @pytest.mark.asyncio
    async def test_evaluate_chunk_size(self, optimizer):
        """Test individual chunk size evaluation."""
        point = await optimizer._evaluate_chunk_size(
            text="Test text for evaluation",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            chunk_size=300
        )
        
        assert isinstance(point, OptimizationPoint)
        assert point.chunk_size == 300
        assert 0.0 <= point.quality_score <= 1.0
        assert point.translation is not None
        assert point.processing_time > 0
        assert point.chunking_result is not None
    
    def test_identify_optimal_region(self, optimizer):
        """Test optimal region identification."""
        # Create sample points with varying quality
        sample_points = [
            OptimizationPoint(150, 0.6, "trans1", Mock(), 0.1),
            OptimizationPoint(250, 0.9, "trans2", Mock(), 0.1),  # Best quality
            OptimizationPoint(350, 0.85, "trans3", Mock(), 0.1),
            OptimizationPoint(450, 0.7, "trans4", Mock(), 0.1),
        ]
        
        baseline_quality = 0.75
        region = optimizer._identify_optimal_region(sample_points, baseline_quality)
        
        assert region is not None
        assert len(region) == 2
        assert region[0] <= region[1]
        assert 100 <= region[0] <= 600
        assert 100 <= region[1] <= 600
    
    def test_identify_optimal_region_no_improvement(self, optimizer):
        """Test optimal region identification when no improvement is found."""
        # All points worse than baseline
        sample_points = [
            OptimizationPoint(200, 0.5, "trans1", Mock(), 0.1),
            OptimizationPoint(300, 0.6, "trans2", Mock(), 0.1),
            OptimizationPoint(400, 0.55, "trans3", Mock(), 0.1),
        ]
        
        baseline_quality = 0.8
        region = optimizer._identify_optimal_region(sample_points, baseline_quality)
        
        # Should still create region around best point
        assert region is not None
        assert len(region) == 2
    
    def test_identify_optimal_region_insufficient_points(self, optimizer):
        """Test optimal region identification with insufficient points."""
        sample_points = [OptimizationPoint(300, 0.8, "trans", Mock(), 0.1)]
        region = optimizer._identify_optimal_region(sample_points, 0.7)
        
        assert region is None
    
    @pytest.mark.asyncio
    async def test_fine_tune_in_region(self, optimizer):
        """Test fine-tuning within identified region."""
        region = (200, 400)
        existing_points = [
            OptimizationPoint(150, 0.7, "trans1", Mock(), 0.1),
            OptimizationPoint(500, 0.6, "trans2", Mock(), 0.1),
        ]
        
        result = await optimizer._fine_tune_in_region(
            text="Test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            region=region,
            existing_points=existing_points
        )
        
        assert isinstance(result, OptimizationPoint)
        assert result.chunk_size is not None
        assert result.quality_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_fine_tune_existing_points_in_region(self, optimizer):
        """Test fine-tuning when points already exist in region."""
        region = (200, 400)
        existing_points = [
            OptimizationPoint(250, 0.9, "trans1", Mock(), 0.1),  # In region
            OptimizationPoint(300, 0.85, "trans2", Mock(), 0.1),  # In region
            OptimizationPoint(500, 0.6, "trans3", Mock(), 0.1),   # Outside region
        ]
        
        result = await optimizer._fine_tune_in_region(
            text="Test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            region=region,
            existing_points=existing_points
        )
        
        # Should return best existing point in region
        assert result.chunk_size == 250
        assert result.quality_score == 0.9
    
    def test_calculate_optimization_confidence(self, optimizer):
        """Test optimization confidence calculation."""
        # High quality, consistent results
        high_confidence_points = [
            OptimizationPoint(200, 0.9, "trans1", Mock(), 0.1),
            OptimizationPoint(250, 0.92, "trans2", Mock(), 0.1),
            OptimizationPoint(300, 0.91, "trans3", Mock(), 0.1),
            OptimizationPoint(350, 0.89, "trans4", Mock(), 0.1),
        ]
        optimal_point = high_confidence_points[1]  # Best quality
        
        confidence = optimizer._calculate_optimization_confidence(
            high_confidence_points, optimal_point
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably confident
        
        # Low confidence with single point
        single_point = [OptimizationPoint(300, 0.8, "trans", Mock(), 0.1)]
        confidence = optimizer._calculate_optimization_confidence(single_point, single_point[0])
        assert confidence == 0.5
        
        # Variable quality (low confidence)
        variable_points = [
            OptimizationPoint(200, 0.3, "trans1", Mock(), 0.1),
            OptimizationPoint(250, 0.9, "trans2", Mock(), 0.1),
            OptimizationPoint(300, 0.4, "trans3", Mock(), 0.1),
        ]
        confidence = optimizer._calculate_optimization_confidence(
            variable_points, variable_points[1]
        )
        assert 0.0 <= confidence <= 1.0
    
    def test_calculate_confidence_interval(self, optimizer):
        """Test confidence interval calculation."""
        sample_points = [
            OptimizationPoint(200, 0.8, "trans1", Mock(), 0.1),
            OptimizationPoint(250, 0.85, "trans2", Mock(), 0.1),
            OptimizationPoint(300, 0.82, "trans3", Mock(), 0.1),
        ]
        
        interval = optimizer._calculate_confidence_interval(sample_points)
        
        assert len(interval) == 2
        assert interval[0] <= interval[1]
        assert 0.0 <= interval[0] <= 1.0
        assert 0.0 <= interval[1] <= 1.0
        
        # Test with insufficient points
        single_point = [OptimizationPoint(300, 0.8, "trans", Mock(), 0.1)]
        interval = optimizer._calculate_confidence_interval(single_point)
        assert interval == (0.0, 1.0)
    
    def test_create_failed_result(self, optimizer):
        """Test failed optimization result creation."""
        start_time = time.time()
        result = optimizer._create_failed_result("baseline", 0.7, start_time, OptimizationStrategy.BALANCED)
        
        assert isinstance(result, OptimizationResult)
        assert result.optimal_chunk_size == 300  # Default
        assert result.optimal_translation == "baseline"
        assert result.optimal_quality_score == 0.7
        assert result.quality_improvement == 0.0
        assert result.optimization_confidence == 0.0
        assert result.search_points == []
        assert result.metadata["optimization_failed"]
        assert result.metadata["strategy"] == OptimizationStrategy.BALANCED.value
    
    @pytest.mark.asyncio
    async def test_optimization_timeout(self, optimizer):
        """Test optimization behavior with timeout."""
        # Mock slow translation function
        async def slow_translation(text, source_lang, target_lang, api_key):
            await asyncio.sleep(1)  # Simulate slow operation
            return "slow translation"
        
        optimizer.translation_function = slow_translation
        
        result = await optimizer.optimize_translation(
            text="Test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="baseline",
            baseline_quality=0.7,
            strategy=OptimizationStrategy.SPEED_FOCUSED,
            timeout=0.5  # Very short timeout
        )
        
        # Should handle timeout gracefully
        assert isinstance(result, OptimizationResult)
        assert result.total_optimization_time <= 0.6  # Should stop before or around timeout
        assert result.metadata.get('optimization_failed') == True  # Should indicate timeout failure
    
    @pytest.mark.asyncio
    async def test_optimization_with_errors(self, optimizer):
        """Test optimization behavior when translation fails."""
        # Mock failing translation function
        async def failing_translation(text, source_lang, target_lang, api_key):
            raise Exception("Translation failed")
        
        optimizer.translation_function = failing_translation
        
        result = await optimizer.optimize_translation(
            text="Test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="baseline",
            baseline_quality=0.7,
            strategy=OptimizationStrategy.BALANCED,
            timeout=5.0
        )
        
        # Should handle errors gracefully
        assert isinstance(result, OptimizationResult)
        assert result.metadata.get("optimization_failed") is True
    
    @pytest.mark.asyncio
    async def test_get_optimization_stats(self, optimizer):
        """Test optimization statistics retrieval."""
        # Perform some optimizations to generate stats
        await optimizer.optimize_translation(
            text="Test text 1",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="baseline1",
            baseline_quality=0.6,
            timeout=2.0
        )
        
        await optimizer.optimize_translation(
            text="Test text 2",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="baseline2",
            baseline_quality=0.8,
            timeout=2.0
        )
        
        stats = await optimizer.get_optimization_stats()
        
        assert "total_optimizations" in stats
        assert "successful_optimizations" in stats
        assert "success_rate" in stats
        assert "avg_improvement" in stats
        assert "avg_optimization_time" in stats
        assert "convergence_threshold" in stats
        assert "max_iterations" in stats
        assert "chunk_size_range" in stats
        
        assert stats["total_optimizations"] == 2
        assert 0.0 <= stats["success_rate"] <= 1.0


class TestOptimizationPoint:
    """Test OptimizationPoint data class."""
    
    def test_optimization_point_creation(self):
        """Test OptimizationPoint creation and attributes."""
        mock_chunking = Mock()
        point = OptimizationPoint(
            chunk_size=300,
            quality_score=0.85,
            translation="test translation",
            chunking_result=mock_chunking,
            processing_time=0.5,
            confidence=0.9
        )
        
        assert point.chunk_size == 300
        assert point.quality_score == 0.85
        assert point.translation == "test translation"
        assert point.chunking_result == mock_chunking
        assert point.processing_time == 0.5
        assert point.confidence == 0.9


class TestOptimizationResult:
    """Test OptimizationResult data class."""
    
    def test_optimization_result_creation(self):
        """Test OptimizationResult creation and attributes."""
        search_points = [
            OptimizationPoint(200, 0.7, "trans1", Mock(), 0.1),
            OptimizationPoint(300, 0.85, "trans2", Mock(), 0.1),
        ]
        
        result = OptimizationResult(
            optimal_chunk_size=300,
            optimal_translation="best translation",
            optimal_quality_score=0.85,
            quality_improvement=0.15,
            confidence_interval=(0.75, 0.95),
            optimization_confidence=0.8,
            search_points=search_points,
            convergence_iterations=5,
            total_optimization_time=2.5,
            metadata={"strategy": "balanced"}
        )
        
        assert result.optimal_chunk_size == 300
        assert result.optimal_translation == "best translation"
        assert result.optimal_quality_score == 0.85
        assert result.quality_improvement == 0.15
        assert result.confidence_interval == (0.75, 0.95)
        assert result.optimization_confidence == 0.8
        assert len(result.search_points) == 2
        assert result.convergence_iterations == 5
        assert result.total_optimization_time == 2.5
        assert result.metadata["strategy"] == "balanced"


class TestOptimizeChunkSizeUtility:
    """Test the utility function."""
    
    @pytest.mark.asyncio
    async def test_optimize_chunk_size_function(self):
        """Test the optimize_chunk_size utility function."""
        mock_translation_func = AsyncMock(return_value="translated")
        
        with patch('app.adaptive.binary_search_optimizer.BinarySearchOptimizer') as mock_optimizer_class:
            mock_optimizer = Mock()
            mock_result = OptimizationResult(
                optimal_chunk_size=350,
                optimal_translation="optimized translation",
                optimal_quality_score=0.9,
                quality_improvement=0.2,
                confidence_interval=(0.8, 1.0),
                optimization_confidence=0.85,
                search_points=[],
                convergence_iterations=3,
                total_optimization_time=1.5,
                metadata={}
            )
            mock_optimizer.optimize_translation = AsyncMock(return_value=mock_result)
            mock_optimizer_class.return_value = mock_optimizer
            
            result = await optimize_chunk_size(
                text="Test text",
                source_lang="en",
                target_lang="fr",
                api_key="test_key",
                translation_function=mock_translation_func,
                baseline_translation="baseline",
                baseline_quality=0.7
            )
            
            assert result == mock_result
            mock_optimizer.optimize_translation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_chunk_size_with_optimizer(self):
        """Test utility function with provided optimizer."""
        mock_translation_func = AsyncMock(return_value="translated")
        mock_optimizer = Mock()
        mock_result = OptimizationResult(
            optimal_chunk_size=400,
            optimal_translation="custom optimized",
            optimal_quality_score=0.88,
            quality_improvement=0.18,
            confidence_interval=(0.78, 0.98),
            optimization_confidence=0.82,
            search_points=[],
            convergence_iterations=4,
            total_optimization_time=2.0,
            metadata={}
        )
        mock_optimizer.optimize_translation = AsyncMock(return_value=mock_result)
        
        result = await optimize_chunk_size(
            text="Test text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            translation_function=mock_translation_func,
            baseline_translation="baseline",
            baseline_quality=0.7,
            optimizer=mock_optimizer
        )
        
        assert result == mock_result
        mock_optimizer.optimize_translation.assert_called_once()


class TestOptimizationEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def minimal_optimizer(self):
        """Create optimizer with minimal configuration."""
        mock_translation = AsyncMock(return_value="translated")
        return BinarySearchOptimizer(
            translation_function=mock_translation,
            min_chunk_size=50,
            max_chunk_size=200,
            max_iterations=1,
            parallel_evaluations=1
        )
    
    @pytest.mark.asyncio
    async def test_empty_text_optimization(self, minimal_optimizer):
        """Test optimization with empty text."""
        result = await minimal_optimizer.optimize_translation(
            text="",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="",
            baseline_quality=0.0,
            timeout=1.0
        )
        
        assert isinstance(result, OptimizationResult)
        # Should handle gracefully
    
    @pytest.mark.asyncio
    async def test_very_short_text(self, minimal_optimizer):
        """Test optimization with very short text."""
        result = await minimal_optimizer.optimize_translation(
            text="Hi",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="Salut",
            baseline_quality=0.8,
            timeout=1.0
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.optimal_chunk_size >= minimal_optimizer.min_chunk_size
    
    @pytest.mark.asyncio
    async def test_optimization_with_perfect_baseline(self, minimal_optimizer):
        """Test optimization when baseline is already perfect."""
        result = await minimal_optimizer.optimize_translation(
            text="Perfect text",
            source_lang="en",
            target_lang="fr",
            api_key="test_key",
            baseline_translation="Texte parfait",
            baseline_quality=1.0,  # Perfect baseline
            timeout=1.0
        )
        
        assert isinstance(result, OptimizationResult)
        # Should still attempt optimization
        assert result.quality_improvement >= -0.1  # May not improve much
    
    def test_invalid_chunk_size_bounds(self):
        """Test optimizer with invalid chunk size bounds."""
        mock_translation = AsyncMock(return_value="translated")
        
        # Max smaller than min should be handled
        optimizer = BinarySearchOptimizer(
            translation_function=mock_translation,
            min_chunk_size=500,
            max_chunk_size=200  # Invalid: max < min
        )
        
        # Should not crash during initialization
        assert optimizer.min_chunk_size == 500
        assert optimizer.max_chunk_size == 200
    
    @pytest.mark.asyncio
    async def test_optimization_strategy_enum_values(self, minimal_optimizer):
        """Test all optimization strategy enum values."""
        strategies = list(OptimizationStrategy)
        
        for strategy in strategies:
            result = await minimal_optimizer.optimize_translation(
                text="Test strategy",
                source_lang="en",
                target_lang="fr",
                api_key="test_key",
                baseline_translation="baseline",
                baseline_quality=0.7,
                strategy=strategy,
                timeout=0.5
            )
            
            assert isinstance(result, OptimizationResult)
            assert result.metadata["strategy"] == strategy.value