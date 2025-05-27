"""
Unit tests for the Quality Assessment Engine.

Tests multi-dimensional quality metrics, translation assessment, and comparison functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.adaptive.quality_assessment import (
    QualityMetricsEngine,
    QualityMetrics,
    QualityDimension,
    TranslationPair,
    assess_translation_quality
)


class TestQualityMetricsEngine:
    """Test suite for QualityMetricsEngine class."""
    
    @pytest.fixture
    def quality_engine(self):
        """Create quality engine with mocked embeddings."""
        with patch('app.adaptive.quality_assessment.SentenceTransformer') as mock_transformer:
            mock_embedder = Mock()
            mock_embedder.encode.return_value = np.array([[0.8, 0.1, 0.1], [0.7, 0.2, 0.1]])
            mock_transformer.return_value = mock_embedder
            
            engine = QualityMetricsEngine()
            engine.embedder = mock_embedder
            return engine
    
    @pytest.fixture
    def sample_translation_pairs(self):
        """Sample translation pairs for testing."""
        return {
            'good_translation': TranslationPair(
                original="Hello, how are you today?",
                translation="Bonjour, comment allez-vous aujourd'hui?",
                language_pair=("en", "fr")
            ),
            'poor_translation': TranslationPair(
                original="Hello, how are you today?",
                translation="Bonjour comment",  # Incomplete translation
                language_pair=("en", "fr")
            ),
            'with_entities': TranslationPair(
                original="John Smith works at Microsoft Inc. on January 15, 2024.",
                translation="Jean Smith travaille chez Microsoft Inc. le 15 janvier 2024.",
                chunks_original=["John Smith works at Microsoft Inc.", "on January 15, 2024."],
                language_pair=("en", "fr")
            ),
            'empty_translation': TranslationPair(
                original="Hello world",
                translation="",
                language_pair=("en", "fr")
            ),
            'with_confidence': TranslationPair(
                original="Test message",
                translation="Message de test",
                model_confidence=0.95,
                language_pair=("en", "fr")
            )
        }
    
    @pytest.mark.asyncio
    async def test_assess_quality_good_translation(self, quality_engine, sample_translation_pairs):
        """Test quality assessment for good translation."""
        pair = sample_translation_pairs['good_translation']
        result = await quality_engine.assess_quality(pair)
        
        assert isinstance(result, QualityMetrics)
        assert 0.0 <= result.overall_score <= 1.0
        assert result.quality_grade in ['A', 'B', 'C', 'D', 'F']
        assert not result.optimization_needed or result.overall_score < quality_engine.quality_threshold
        assert len(result.dimension_scores) == len(QualityDimension)
        assert len(result.improvement_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_assess_quality_poor_translation(self, quality_engine, sample_translation_pairs):
        """Test quality assessment for poor translation."""
        pair = sample_translation_pairs['poor_translation']
        result = await quality_engine.assess_quality(pair)
        
        assert result.overall_score < 0.85  # Should be lower quality than good translation
        assert result.quality_grade in ['C', 'D', 'F']
        # optimization_needed depends on threshold, so don't assert it
        assert "ratio" in " ".join(result.improvement_suggestions).lower() or "structure" in " ".join(result.improvement_suggestions).lower()  # Should suggest improvements
    
    @pytest.mark.asyncio
    async def test_assess_quality_empty_translation(self, quality_engine, sample_translation_pairs):
        """Test quality assessment for empty translation."""
        pair = sample_translation_pairs['empty_translation']
        result = await quality_engine.assess_quality(pair)
        
        assert result.overall_score == 0.0
        assert result.quality_grade == 'F'
        assert result.optimization_needed
        assert "empty" in " ".join(result.improvement_suggestions).lower()
        assert "error" in result.metadata
    
    def test_assess_confidence(self, quality_engine, sample_translation_pairs):
        """Test confidence assessment."""
        # Test with model confidence
        pair = sample_translation_pairs['with_confidence']
        confidence = quality_engine._assess_confidence(pair)
        assert confidence == 0.95
        
        # Test without model confidence (fallback)
        pair = sample_translation_pairs['good_translation']
        confidence = quality_engine._assess_confidence(pair)
        assert 0.0 <= confidence <= 1.0
        
        # Test extreme length ratio
        extreme_pair = TranslationPair(
            original="Short",
            translation="This is an extremely long translation that doesn't match the original length at all",
            language_pair=("en", "fr")
        )
        confidence = quality_engine._assess_confidence(extreme_pair)
        assert confidence < 0.6  # Should be low confidence
    
    def test_assess_length_ratio(self, quality_engine):
        """Test length ratio assessment."""
        # Good ratio for English to French
        good_pair = TranslationPair(
            original="Hello world",  # 11 chars
            translation="Bonjour monde",  # 13 chars, good ratio
            language_pair=("en", "fr")
        )
        ratio_score = quality_engine._assess_length_ratio(good_pair)
        assert ratio_score >= 0.8
        
        # Poor ratio (too short)
        poor_pair = TranslationPair(
            original="This is a long sentence with many words",
            translation="Court",  # Too short
            language_pair=("en", "fr")
        )
        ratio_score = quality_engine._assess_length_ratio(poor_pair)
        assert ratio_score < 0.5
        
        # Empty original
        empty_pair = TranslationPair(
            original="",
            translation="Something",
            language_pair=("en", "fr")
        )
        ratio_score = quality_engine._assess_length_ratio(empty_pair)
        assert ratio_score == 0.0
    
    def test_assess_structure_integrity(self, quality_engine):
        """Test structure integrity assessment."""
        # Good structure preservation
        good_pair = TranslationPair(
            original="Hello world! How are you? Fine, thanks.",
            translation="Bonjour monde! Comment allez-vous? Bien, merci.",
            language_pair=("en", "fr")
        )
        structure_score = quality_engine._assess_structure_integrity(good_pair)
        assert structure_score >= 0.8
        
        # Poor structure (missing punctuation)
        poor_pair = TranslationPair(
            original="Hello! How are you? Good.",
            translation="Bonjour Comment allez-vous Bien",  # Missing punctuation
            language_pair=("en", "fr")
        )
        structure_score = quality_engine._assess_structure_integrity(poor_pair)
        assert structure_score < 0.8
    
    def test_assess_entity_preservation(self, quality_engine, sample_translation_pairs):
        """Test named entity preservation assessment."""
        pair = sample_translation_pairs['with_entities']
        entity_score = quality_engine._assess_entity_preservation(pair)
        
        # Should detect and preserve "Microsoft Inc." and date
        assert entity_score > 0.0
        
        # Test with no entities
        no_entities_pair = TranslationPair(
            original="The weather is nice today",
            translation="Le temps est beau aujourd'hui",
            language_pair=("en", "fr")
        )
        entity_score = quality_engine._assess_entity_preservation(no_entities_pair)
        assert entity_score == 1.0  # Perfect score when no entities to preserve
    
    @pytest.mark.asyncio
    async def test_assess_boundary_coherence(self, quality_engine):
        """Test boundary coherence assessment."""
        # Test with chunked translation
        chunked_pair = TranslationPair(
            original="First part. Second part.",
            translation="Première partie. Deuxième partie.",
            chunks_translated=["Première partie.", "Deuxième partie."],
            language_pair=("en", "fr")
        )
        coherence_score = await quality_engine._assess_boundary_coherence(chunked_pair)
        assert 0.0 <= coherence_score <= 1.0
        
        # Test single chunk (should be perfect)
        single_pair = TranslationPair(
            original="Single chunk",
            translation="Bloc unique",
            chunks_translated=["Bloc unique"],
            language_pair=("en", "fr")
        )
        coherence_score = await quality_engine._assess_boundary_coherence(single_pair)
        assert coherence_score == 1.0
        
        # Test no chunks
        no_chunks_pair = TranslationPair(
            original="No chunks",
            translation="Pas de blocs",
            language_pair=("en", "fr")
        )
        coherence_score = await quality_engine._assess_boundary_coherence(no_chunks_pair)
        assert coherence_score == 1.0
    
    @pytest.mark.asyncio
    async def test_assess_semantic_similarity(self, quality_engine):
        """Test semantic similarity assessment."""
        # Mock high similarity
        quality_engine.embedder.encode.return_value = np.array([[0.9, 0.1], [0.8, 0.2]])
        
        pair = TranslationPair(
            original="Good morning",
            translation="Bonjour",
            language_pair=("en", "fr")
        )
        similarity_score = await quality_engine._assess_semantic_similarity(pair)
        assert similarity_score > 0.7  # Should be high with mocked similarity
        
        # Test without embedder
        quality_engine.embedder = None
        similarity_score = await quality_engine._assess_semantic_similarity(pair)
        assert similarity_score == 0.7  # Neutral score
    
    def test_assess_fluency(self, quality_engine):
        """Test target language fluency assessment."""
        # Good English fluency
        good_pair = TranslationPair(
            original="Texte français",
            translation="The quick brown fox jumps over the lazy dog",
            language_pair=("fr", "en")
        )
        fluency_score = quality_engine._assess_fluency(good_pair)
        assert fluency_score >= 0.0
        
        # Poor fluency (word repetition)
        poor_pair = TranslationPair(
            original="Texte français",
            translation="The the the of the of the",  # Poor fluency pattern
            language_pair=("fr", "en")
        )
        fluency_score = quality_engine._assess_fluency(poor_pair)
        assert fluency_score < 0.5
        
        # Unsupported language
        unsupported_pair = TranslationPair(
            original="Text",
            translation="テキスト",
            language_pair=("en", "ja")
        )
        fluency_score = quality_engine._assess_fluency(unsupported_pair)
        assert fluency_score == 0.7  # Neutral score
    
    def test_calculate_overall_score(self, quality_engine):
        """Test overall score calculation."""
        # Mock dimension scores
        dimension_scores = {
            QualityDimension.CONFIDENCE: 0.9,
            QualityDimension.LENGTH_RATIO: 0.8,
            QualityDimension.STRUCTURE_INTEGRITY: 0.85,
            QualityDimension.NAMED_ENTITY_PRESERVATION: 1.0,
            QualityDimension.BOUNDARY_COHERENCE: 0.9,
            QualityDimension.SEMANTIC_SIMILARITY: 0.8,
            QualityDimension.FLUENCY: 0.7
        }
        
        overall_score = quality_engine._calculate_overall_score(dimension_scores)
        
        assert 0.0 <= overall_score <= 1.0
        # Should be weighted average
        expected_min = 0.7  # Lowest score
        expected_max = 1.0  # Highest score
        assert expected_min <= overall_score <= expected_max
    
    def test_assign_quality_grade(self, quality_engine):
        """Test quality grade assignment."""
        assert quality_engine._assign_quality_grade(0.95) == "A"
        assert quality_engine._assign_quality_grade(0.85) == "B"
        assert quality_engine._assign_quality_grade(0.75) == "C"
        assert quality_engine._assign_quality_grade(0.65) == "D"
        assert quality_engine._assign_quality_grade(0.45) == "F"
    
    def test_generate_improvement_suggestions(self, quality_engine):
        """Test improvement suggestion generation."""
        # Poor scores should generate specific suggestions
        poor_scores = {
            QualityDimension.CONFIDENCE: 0.3,
            QualityDimension.LENGTH_RATIO: 0.4,
            QualityDimension.STRUCTURE_INTEGRITY: 0.5,
            QualityDimension.NAMED_ENTITY_PRESERVATION: 0.2,
            QualityDimension.BOUNDARY_COHERENCE: 0.3,
            QualityDimension.SEMANTIC_SIMILARITY: 0.4,
            QualityDimension.FLUENCY: 0.3
        }
        
        suggestions = quality_engine._generate_improvement_suggestions(poor_scores)
        
        assert len(suggestions) > 0
        assert any("confidence" in s.lower() for s in suggestions)
        assert any("length" in s.lower() for s in suggestions)
        assert any("entities" in s.lower() for s in suggestions)
        
        # Good scores should generate minimal suggestions
        good_scores = {dim: 0.9 for dim in QualityDimension}
        suggestions = quality_engine._generate_improvement_suggestions(good_scores)
        assert len(suggestions) > 0
        assert "acceptable" in suggestions[0].lower()
    
    def test_calculate_confidence_interval(self, quality_engine):
        """Test confidence interval calculation."""
        # Test with multiple scores
        scores = {
            QualityDimension.CONFIDENCE: 0.8,
            QualityDimension.LENGTH_RATIO: 0.85,
            QualityDimension.SEMANTIC_SIMILARITY: 0.75
        }
        
        interval = quality_engine._calculate_confidence_interval(scores)
        
        assert len(interval) == 2
        assert interval[0] <= interval[1]
        assert 0.0 <= interval[0] <= 1.0
        assert 0.0 <= interval[1] <= 1.0
        
        # Test with single score
        single_score = {QualityDimension.CONFIDENCE: 0.8}
        interval = quality_engine._calculate_confidence_interval(single_score)
        assert interval == (0.0, 1.0)  # Default wide interval
    
    @pytest.mark.asyncio
    async def test_compare_translations(self, quality_engine):
        """Test translation comparison functionality."""
        original = "Hello world"
        translation1 = "Bonjour monde"
        translation2 = "Salut univers"
        
        comparison = await quality_engine.compare_translations(
            original, translation1, translation2, ("en", "fr")
        )
        
        assert "translation1_quality" in comparison
        assert "translation2_quality" in comparison
        assert "winner" in comparison
        assert comparison["winner"] in ["translation1", "translation2"]
        assert "score_difference" in comparison
        assert "dimension_comparison" in comparison
        
        # Check dimension comparison structure
        dim_comp = comparison["dimension_comparison"]
        assert len(dim_comp) == len(QualityDimension)
        for dim_name, comp_data in dim_comp.items():
            assert "translation1" in comp_data
            assert "translation2" in comp_data
            assert "difference" in comp_data


class TestQualityAssessmentUtility:
    """Test the utility function."""
    
    @pytest.mark.asyncio
    async def test_assess_translation_quality_function(self):
        """Test the assess_translation_quality utility function."""
        with patch('app.adaptive.quality_assessment.QualityMetricsEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_result = QualityMetrics(
                overall_score=0.85,
                dimension_scores={QualityDimension.CONFIDENCE: 0.8},
                confidence_interval=(0.7, 0.9),
                quality_grade="B",
                optimization_needed=False,
                improvement_suggestions=["Good quality"],
                metadata={}
            )
            mock_engine.assess_quality = AsyncMock(return_value=mock_result)
            mock_engine_class.return_value = mock_engine
            
            result = await assess_translation_quality(
                original="Hello",
                translation="Bonjour",
                model_confidence=0.9,
                language_pair=("en", "fr")
            )
            
            assert result == mock_result
            mock_engine.assess_quality.assert_called_once()
            
            # Check that TranslationPair was created correctly
            call_args = mock_engine.assess_quality.call_args[0][0]
            assert call_args.original == "Hello"
            assert call_args.translation == "Bonjour"
            assert call_args.model_confidence == 0.9
            assert call_args.language_pair == ("en", "fr")
    
    @pytest.mark.asyncio
    async def test_assess_translation_quality_with_engine(self):
        """Test utility function with provided engine."""
        mock_engine = Mock()
        mock_result = QualityMetrics(
            overall_score=0.75,
            dimension_scores={QualityDimension.CONFIDENCE: 0.7},
            confidence_interval=(0.6, 0.8),
            quality_grade="C",
            optimization_needed=True,
            improvement_suggestions=["Could be better"],
            metadata={}
        )
        mock_engine.assess_quality = AsyncMock(return_value=mock_result)
        
        result = await assess_translation_quality(
            original="Test",
            translation="Essai",
            engine=mock_engine
        )
        
        assert result == mock_result
        mock_engine.assess_quality.assert_called_once()


class TestQualityEngineEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def engine_no_embedder(self):
        """Create engine without embedder."""
        with patch('app.adaptive.quality_assessment.SentenceTransformer') as mock_transformer:
            mock_transformer.side_effect = Exception("No embedder")
            engine = QualityMetricsEngine()
            assert engine.embedder is None
            return engine
    
    @pytest.mark.asyncio
    async def test_engine_without_embedder(self, engine_no_embedder):
        """Test engine operation without embedder."""
        pair = TranslationPair(
            original="Test text",
            translation="Texte de test",
            language_pair=("en", "fr")
        )
        
        result = await engine_no_embedder.assess_quality(pair)
        
        assert isinstance(result, QualityMetrics)
        assert 0.0 <= result.overall_score <= 1.0
        # Should still work with fallback scores
        assert QualityDimension.SEMANTIC_SIMILARITY in result.dimension_scores
        assert result.dimension_scores[QualityDimension.SEMANTIC_SIMILARITY] == 0.7
    
    @pytest.mark.asyncio
    async def test_very_long_translation(self, engine_no_embedder):
        """Test with very long translation."""
        long_translation = "Word " * 1000
        pair = TranslationPair(
            original="Short text",
            translation=long_translation,
            language_pair=("en", "fr")
        )
        
        result = await engine_no_embedder.assess_quality(pair)
        
        assert result.overall_score < 0.75  # Should be poor due to length ratio
        assert result.dimension_scores[QualityDimension.LENGTH_RATIO] < 0.5
    
    @pytest.mark.asyncio
    async def test_special_characters_and_unicode(self, engine_no_embedder):
        """Test with special characters and Unicode."""
        pair = TranslationPair(
            original="Hello 😊 $100 @ user@domain.com",
            translation="Bonjour 😊 100$ @ utilisateur@domaine.com",
            language_pair=("en", "fr")
        )
        
        result = await engine_no_embedder.assess_quality(pair)
        
        assert isinstance(result, QualityMetrics)
        assert 0.0 <= result.overall_score <= 1.0
        # Should handle Unicode gracefully
    
    def test_empty_dimension_scores(self, engine_no_embedder):
        """Test with empty dimension scores."""
        overall_score = engine_no_embedder._calculate_overall_score({})
        assert overall_score == 0.0
        
        suggestions = engine_no_embedder._generate_improvement_suggestions({})
        assert len(suggestions) > 0
    
    def test_malformed_language_pairs(self, engine_no_embedder):
        """Test with malformed language pairs."""
        pair = TranslationPair(
            original="Test",
            translation="Test",
            language_pair=None  # Malformed
        )
        
        # Should not crash
        score = engine_no_embedder._assess_length_ratio(pair)
        assert 0.0 <= score <= 1.0