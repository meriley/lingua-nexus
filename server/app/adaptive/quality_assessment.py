"""
Enhanced Quality Assessment Engine

Multi-dimensional quality metrics for translation assessment beyond simple confidence scores.
Evaluates translation quality using structural, semantic, and linguistic criteria.
"""

import re
import logging
import asyncio
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    """Quality assessment dimensions."""
    CONFIDENCE = "confidence"           # Model confidence score
    LENGTH_RATIO = "length_ratio"       # Length consistency
    STRUCTURE_INTEGRITY = "structure"   # Structural preservation
    NAMED_ENTITY_PRESERVATION = "entities"  # Named entity handling
    BOUNDARY_COHERENCE = "boundaries"   # Chunk boundary coherence
    SEMANTIC_SIMILARITY = "semantic"    # Semantic preservation
    FLUENCY = "fluency"                # Target language fluency
    CONSISTENCY = "consistency"         # Translation consistency


@dataclass
class QualityMetrics:
    """Comprehensive quality assessment result."""
    overall_score: float
    dimension_scores: Dict[QualityDimension, float]
    confidence_interval: Tuple[float, float]
    quality_grade: str  # A, B, C, D, F
    optimization_needed: bool
    improvement_suggestions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranslationPair:
    """Translation pair for quality assessment."""
    original: str
    translation: str
    chunks_original: Optional[List[str]] = None
    chunks_translated: Optional[List[str]] = None
    model_confidence: Optional[float] = None
    language_pair: Optional[Tuple[str, str]] = None


class QualityMetricsEngine:
    """
    Enhanced quality assessment engine that evaluates translation quality
    across multiple dimensions beyond simple confidence scores.
    """
    
    def __init__(self, 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 quality_threshold: float = 0.75):
        """
        Initialize the quality metrics engine.
        
        Args:
            embedding_model: Model for semantic similarity assessment
            quality_threshold: Threshold for optimization decisions
        """
        self.quality_threshold = quality_threshold
        
        # Initialize embedding model for semantic analysis
        try:
            self.embedder = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model for quality assessment: {embedding_model}")
        except Exception as e:
            logger.warning(f"Failed to load embedding model {embedding_model}: {e}")
            self.embedder = None
        
        # Quality dimension weights
        self.dimension_weights = {
            QualityDimension.CONFIDENCE: 0.18,
            QualityDimension.LENGTH_RATIO: 0.12,
            QualityDimension.STRUCTURE_INTEGRITY: 0.12,
            QualityDimension.NAMED_ENTITY_PRESERVATION: 0.12,
            QualityDimension.BOUNDARY_COHERENCE: 0.10,
            QualityDimension.SEMANTIC_SIMILARITY: 0.15,
            QualityDimension.FLUENCY: 0.11,
            QualityDimension.CONSISTENCY: 0.10
        }
        
        # Named entity patterns
        self.entity_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Person names
            r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+(?:Inc|Corp|LLC|Ltd)\b',  # Company names
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Dates
            r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\b',  # Times
            r'\b[A-Z]{2,}\b',  # Acronyms
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?\b',  # Currency
        ]
        
        # Fluency indicators
        self.fluency_patterns = {
            'en': {
                'good': [r'\b(?:the|a|an)\s+\w+', r'\b\w+\s+(?:is|are|was|were)\s+', r'\b\w+ly\b'],
                'bad': [r'\b\w+\s+\w+\s+\w+\s+of\s+\w+\s+of\b', r'\bof\s+the\s+of\b']
            }
        }

    async def assess_quality(self, translation_pair: TranslationPair) -> QualityMetrics:
        """
        Perform comprehensive quality assessment of a translation.
        
        Args:
            translation_pair: Original and translated text with metadata
            
        Returns:
            QualityMetrics with detailed assessment results
        """
        if not translation_pair.translation.strip():
            return QualityMetrics(
                overall_score=0.0,
                dimension_scores={dim: 0.0 for dim in QualityDimension},
                confidence_interval=(0.0, 0.0),
                quality_grade="F",
                optimization_needed=True,
                improvement_suggestions=["Translation is empty"],
                metadata={"error": "Empty translation"}
            )
        
        # Calculate individual dimension scores
        dimension_scores = {}
        
        # 1. Model confidence (if available)
        dimension_scores[QualityDimension.CONFIDENCE] = self._assess_confidence(translation_pair)
        
        # 2. Length ratio consistency
        dimension_scores[QualityDimension.LENGTH_RATIO] = self._assess_length_ratio(translation_pair)
        
        # 3. Structure integrity
        dimension_scores[QualityDimension.STRUCTURE_INTEGRITY] = self._assess_structure_integrity(translation_pair)
        
        # 4. Named entity preservation
        dimension_scores[QualityDimension.NAMED_ENTITY_PRESERVATION] = self._assess_entity_preservation(translation_pair)
        
        # 5. Boundary coherence (for chunked translations)
        dimension_scores[QualityDimension.BOUNDARY_COHERENCE] = await self._assess_boundary_coherence(translation_pair)
        
        # 6. Semantic similarity
        dimension_scores[QualityDimension.SEMANTIC_SIMILARITY] = await self._assess_semantic_similarity(translation_pair)
        
        # 7. Target language fluency
        dimension_scores[QualityDimension.FLUENCY] = self._assess_fluency(translation_pair)
        
        # 8. Translation consistency
        dimension_scores[QualityDimension.CONSISTENCY] = self._assess_consistency(translation_pair)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores)
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(dimension_scores)
        
        # Determine quality grade
        quality_grade = self._assign_quality_grade(overall_score)
        
        # Determine if optimization is needed
        optimization_needed = overall_score < self.quality_threshold
        
        # Generate improvement suggestions
        improvement_suggestions = self._generate_improvement_suggestions(dimension_scores)
        
        return QualityMetrics(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            confidence_interval=confidence_interval,
            quality_grade=quality_grade,
            optimization_needed=optimization_needed,
            improvement_suggestions=improvement_suggestions,
            metadata={
                "assessment_timestamp": asyncio.get_event_loop().time(),
                "language_pair": translation_pair.language_pair,
                "original_length": len(translation_pair.original),
                "translation_length": len(translation_pair.translation),
                "chunked": translation_pair.chunks_original is not None
            }
        )

    def _assess_confidence(self, translation_pair: TranslationPair) -> float:
        """Assess translation confidence from model output."""
        if translation_pair.model_confidence is not None:
            # Normalize confidence to 0-1 range
            return max(0.0, min(1.0, translation_pair.model_confidence))
        
        # Fallback: estimate confidence based on translation characteristics
        original_len = len(translation_pair.original)
        translation_len = len(translation_pair.translation)
        
        # Heuristic: very short or very long translations compared to original suggest lower confidence
        if translation_len < original_len * 0.3 or translation_len > original_len * 3.0:
            return 0.4  # Lower confidence for extreme length ratios
        
        return 0.6  # Neutral confidence when model confidence unavailable

    def _assess_length_ratio(self, translation_pair: TranslationPair) -> float:
        """Assess length ratio consistency."""
        original_len = len(translation_pair.original.strip())
        translation_len = len(translation_pair.translation.strip())
        
        if original_len == 0:
            return 0.0
        
        ratio = translation_len / original_len
        
        # Expected ratios for different language pairs
        expected_ratios = {
            ('en', 'ru'): (1.1, 1.4),  # English to Russian typically 10-40% longer
            ('ru', 'en'): (0.7, 0.9),  # Russian to English typically 10-30% shorter
            ('en', 'es'): (1.0, 1.2),  # English to Spanish
            ('es', 'en'): (0.8, 1.0),  # Spanish to English
        }
        
        # Default range for unknown language pairs
        expected_min, expected_max = expected_ratios.get(
            translation_pair.language_pair, (0.7, 1.4)
        )
        
        if expected_min <= ratio <= expected_max:
            return 1.0  # Perfect score for expected ratio
        elif ratio < expected_min * 0.5 or ratio > expected_max * 2.0:
            return 0.2  # Very poor score for extreme ratios
        else:
            # Linear interpolation for intermediate values
            if ratio < expected_min:
                return 0.2 + 0.8 * (ratio / expected_min)
            else:
                return 1.0 - 0.8 * ((ratio - expected_max) / expected_max)

    def _assess_structure_integrity(self, translation_pair: TranslationPair) -> float:
        """Assess preservation of text structure (paragraphs, sentences, punctuation)."""
        original = translation_pair.original
        translation = translation_pair.translation
        
        scores = []
        
        # 1. Paragraph structure
        orig_paragraphs = len(original.split('\n\n'))
        trans_paragraphs = len(translation.split('\n\n'))
        paragraph_score = 1.0 - abs(orig_paragraphs - trans_paragraphs) / max(orig_paragraphs, 1)
        scores.append(paragraph_score)
        
        # 2. Sentence count similarity
        orig_sentences = len(re.findall(r'[.!?]+', original))
        trans_sentences = len(re.findall(r'[.!?]+', translation))
        sentence_score = 1.0 - abs(orig_sentences - trans_sentences) / max(orig_sentences, 1)
        scores.append(min(sentence_score, 1.0))
        
        # 3. Punctuation preservation
        orig_punct = re.findall(r'[,.;:!?()-]', original)
        trans_punct = re.findall(r'[,.;:!?()-]', translation)
        punct_score = 1.0 - abs(len(orig_punct) - len(trans_punct)) / max(len(orig_punct), 1)
        scores.append(min(punct_score, 1.0))
        
        return statistics.mean(scores)

    def _assess_entity_preservation(self, translation_pair: TranslationPair) -> float:
        """Assess preservation of named entities."""
        original = translation_pair.original
        translation = translation_pair.translation
        
        # Extract entities from original
        original_entities = set()
        for pattern in self.entity_patterns:
            entities = re.findall(pattern, original)
            original_entities.update(entities)
        
        if not original_entities:
            return 1.0  # Perfect score if no entities to preserve
        
        # Check preservation in translation
        preserved_count = 0
        for entity in original_entities:
            # Simple check: entity appears in translation
            # More sophisticated: check for transliterated versions
            if entity.lower() in translation.lower():
                preserved_count += 1
            # Check for partial matches (for transliterated names)
            elif any(word.lower() in translation.lower() for word in entity.split() if len(word) > 2):
                preserved_count += 0.5
        
        return preserved_count / len(original_entities)

    async def _assess_boundary_coherence(self, translation_pair: TranslationPair) -> float:
        """Assess coherence at chunk boundaries for chunked translations."""
        if not translation_pair.chunks_translated or len(translation_pair.chunks_translated) <= 1:
            return 1.0  # Perfect score for single chunk or no chunks
        
        if not self.embedder:
            return 0.7  # Neutral score when embeddings unavailable
        
        try:
            # Calculate semantic coherence between adjacent chunks
            chunks = translation_pair.chunks_translated
            embeddings = self.embedder.encode(chunks)
            
            coherence_scores = []
            for i in range(len(embeddings) - 1):
                similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
                coherence_scores.append(similarity)
            
            return float(np.mean(coherence_scores))
            
        except Exception as e:
            logger.warning(f"Boundary coherence assessment failed: {e}")
            return 0.7

    async def _assess_semantic_similarity(self, translation_pair: TranslationPair) -> float:
        """Assess semantic similarity between original and translation."""
        if not self.embedder:
            return 0.7  # Neutral score when embeddings unavailable
        
        try:
            # Get embeddings for both texts
            texts = [translation_pair.original, translation_pair.translation]
            embeddings = self.embedder.encode(texts)
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Convert to 0-1 scale (cosine similarity can be negative)
            return max(0.0, float(similarity))
            
        except Exception as e:
            logger.warning(f"Semantic similarity assessment failed: {e}")
            return 0.7

    def _assess_fluency(self, translation_pair: TranslationPair) -> float:
        """Assess target language fluency."""
        translation = translation_pair.translation
        
        # Get target language (assume English if not specified)
        target_lang = 'en'
        if translation_pair.language_pair:
            target_lang = translation_pair.language_pair[1]
        
        if target_lang not in self.fluency_patterns:
            return 0.7  # Neutral score for unsupported languages
        
        patterns = self.fluency_patterns[target_lang]
        scores = []
        
        # Check for good fluency indicators
        good_indicators = 0
        for pattern in patterns.get('good', []):
            good_indicators += len(re.findall(pattern, translation, re.IGNORECASE))
        
        # Check for bad fluency indicators
        bad_indicators = 0
        for pattern in patterns.get('bad', []):
            bad_indicators += len(re.findall(pattern, translation, re.IGNORECASE))
        
        # Calculate fluency score
        word_count = len(translation.split())
        if word_count == 0:
            return 0.0
        
        good_ratio = good_indicators / word_count
        bad_ratio = bad_indicators / word_count
        
        # Fluency score based on good vs bad indicators
        fluency_score = min(1.0, good_ratio * 2) - min(0.5, bad_ratio * 5)
        
        return max(0.0, fluency_score)

    def _assess_consistency(self, translation_pair: TranslationPair) -> float:
        """Assess translation consistency."""
        # For single translations, consistency is based on internal coherence
        translation = translation_pair.translation
        
        if not translation.strip():
            return 0.0
        
        # Basic consistency checks
        consistency_score = 1.0
        
        # Check for repeated words (could indicate inconsistency)
        words = translation.lower().split()
        if len(words) > 0:
            unique_words = set(words)
            repetition_ratio = len(words) / len(unique_words)
            if repetition_ratio > 2.0:  # High repetition
                consistency_score -= 0.2
        
        # Check for contradictory patterns (simple heuristics)
        contradictions = [
            ('yes', 'no'), ('true', 'false'), ('on', 'off'),
            ('always', 'never'), ('all', 'none')
        ]
        
        for word1, word2 in contradictions:
            if word1 in translation.lower() and word2 in translation.lower():
                consistency_score -= 0.1
        
        # Check sentence structure consistency
        sentences = translation.split('.')
        if len(sentences) > 1:
            # Simple check: sentences should have similar structure
            sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
            if sentence_lengths:
                avg_length = sum(sentence_lengths) / len(sentence_lengths)
                variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
                if variance > avg_length * 0.5:  # High variance in sentence lengths
                    consistency_score -= 0.1
        
        return max(0.0, min(1.0, consistency_score))

    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, float]) -> float:
        """Calculate weighted overall quality score."""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for dimension, score in dimension_scores.items():
            weight = self.dimension_weights.get(dimension, 0.1)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight

    def _calculate_confidence_interval(self, dimension_scores: Dict[QualityDimension, float]) -> Tuple[float, float]:
        """Calculate confidence interval for the overall score."""
        scores = list(dimension_scores.values())
        
        if len(scores) < 2:
            return (0.0, 1.0)
        
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores)
        
        # 95% confidence interval (approximation)
        margin = 1.96 * std_dev / len(scores) ** 0.5
        
        return (
            max(0.0, mean_score - margin),
            min(1.0, mean_score + margin)
        )

    def _assign_quality_grade(self, overall_score: float) -> str:
        """Assign letter grade based on overall score."""
        if overall_score >= 0.9:
            return "A"
        elif overall_score >= 0.8:
            return "B"
        elif overall_score >= 0.7:
            return "C"
        elif overall_score >= 0.6:
            return "D"
        else:
            return "F"

    def _generate_improvement_suggestions(self, dimension_scores: Dict[QualityDimension, float]) -> List[str]:
        """Generate specific improvement suggestions based on dimension scores."""
        suggestions = []
        
        for dimension, score in dimension_scores.items():
            if score < 0.6:  # Poor scores need attention
                if dimension == QualityDimension.CONFIDENCE:
                    suggestions.append("Consider using different chunking strategy for better model confidence")
                elif dimension == QualityDimension.LENGTH_RATIO:
                    suggestions.append("Translation length ratio suggests potential over/under-translation")
                elif dimension == QualityDimension.STRUCTURE_INTEGRITY:
                    suggestions.append("Text structure not well preserved - adjust chunking boundaries")
                elif dimension == QualityDimension.NAMED_ENTITY_PRESERVATION:
                    suggestions.append("Named entities not properly preserved - use entity-aware chunking")
                elif dimension == QualityDimension.BOUNDARY_COHERENCE:
                    suggestions.append("Chunk boundaries create semantic discontinuity")
                elif dimension == QualityDimension.SEMANTIC_SIMILARITY:
                    suggestions.append("Semantic meaning not well preserved - try larger chunks")
                elif dimension == QualityDimension.FLUENCY:
                    suggestions.append("Target language fluency could be improved")
        
        if not suggestions:
            suggestions.append("Quality is acceptable - minor optimizations possible")
        
        return suggestions

    async def compare_translations(self, 
                                 original: str,
                                 translation1: str,
                                 translation2: str,
                                 language_pair: Optional[Tuple[str, str]] = None) -> Dict[str, Any]:
        """
        Compare two translations of the same original text.
        
        Args:
            original: Original text
            translation1: First translation
            translation2: Second translation
            language_pair: Optional language pair tuple
            
        Returns:
            Comparison results with quality metrics for both translations
        """
        pair1 = TranslationPair(original, translation1, language_pair=language_pair)
        pair2 = TranslationPair(original, translation2, language_pair=language_pair)
        
        quality1 = await self.assess_quality(pair1)
        quality2 = await self.assess_quality(pair2)
        
        return {
            "translation1_quality": quality1,
            "translation2_quality": quality2,
            "winner": "translation1" if quality1.overall_score > quality2.overall_score else "translation2",
            "score_difference": abs(quality1.overall_score - quality2.overall_score),
            "dimension_comparison": {
                dim.value: {
                    "translation1": quality1.dimension_scores[dim],
                    "translation2": quality2.dimension_scores[dim],
                    "difference": quality1.dimension_scores[dim] - quality2.dimension_scores[dim]
                }
                for dim in QualityDimension
            }
        }


# Utility functions for external use
async def assess_translation_quality(original: str,
                                   translation: str,
                                   model_confidence: Optional[float] = None,
                                   language_pair: Optional[Tuple[str, str]] = None,
                                   engine: Optional[QualityMetricsEngine] = None) -> QualityMetrics:
    """
    Convenience function for quality assessment.
    
    Args:
        original: Original text
        translation: Translated text
        model_confidence: Optional model confidence score
        language_pair: Optional language pair tuple
        engine: Optional pre-initialized engine
        
    Returns:
        QualityMetrics with assessment results
    """
    if engine is None:
        engine = QualityMetricsEngine()
    
    pair = TranslationPair(
        original=original,
        translation=translation,
        model_confidence=model_confidence,
        language_pair=language_pair
    )
    
    return await engine.assess_quality(pair)