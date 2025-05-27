"""
Context-Aware Semantic Chunker

Implements intelligent text segmentation with discourse analysis for optimal translation quality.
Handles emotional text, technical content, and conversational messages with appropriate chunking strategies.
"""

import re
import logging
import asyncio
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

import nltk
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger')

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content type classification for adaptive chunking strategies."""
    EMOTIONAL = "emotional"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"
    FORMAL = "formal"
    NARRATIVE = "narrative"


@dataclass
class ChunkingResult:
    """Result of semantic chunking operation."""
    chunks: List[str]
    chunk_boundaries: List[Tuple[int, int]]
    content_type: ContentType
    coherence_score: float
    optimal_size_estimate: int
    metadata: Dict[str, Any]


@dataclass
class DiscourseFeatures:
    """Discourse analysis features for chunking decisions."""
    sentence_count: int
    avg_sentence_length: float
    punctuation_density: float
    connector_count: int
    emotion_indicators: int
    technical_terms: int
    coreference_chains: List[List[int]]


class SemanticChunker:
    """
    Context-aware semantic chunker that uses discourse analysis and semantic similarity
    to create optimal text chunks for translation quality.
    """
    
    def __init__(self, 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 min_chunk_size: int = 150,
                 max_chunk_size: int = 600,
                 similarity_threshold: float = 0.7):
        """
        Initialize the semantic chunker.
        
        Args:
            embedding_model: SentenceTransformer model for semantic analysis
            min_chunk_size: Minimum characters per chunk
            max_chunk_size: Maximum characters per chunk  
            similarity_threshold: Threshold for semantic similarity grouping
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.similarity_threshold = similarity_threshold
        
        # Initialize embedding model
        try:
            self.embedder = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model: {embedding_model}")
        except Exception as e:
            logger.warning(f"Failed to load embedding model {embedding_model}: {e}")
            self.embedder = None
            
        # Discourse markers and patterns
        self.discourse_connectors = {
            'en': ['however', 'therefore', 'furthermore', 'moreover', 'consequently', 'meanwhile'],
            'ru': ['однако', 'поэтому', 'кроме того', 'более того', 'следовательно', 'тем временем'],
            'default': ['but', 'and', 'or', 'so', 'then', 'also']
        }
        
        self.emotion_indicators = {
            'en': ['!', '?', 'amazing', 'terrible', 'wonderful', 'awful', 'love', 'hate'],
            'ru': ['!', '?', 'удивительно', 'ужасно', 'замечательно', 'отвратительно', 'люблю', 'ненавижу'],
            'default': ['!', '?', ':)', ':(', '😊', '😢', '😍', '😠']
        }
        
        self.technical_patterns = [
            r'\b\w+\(\)',  # Function calls
            r'\b[A-Z]{2,}[a-z]*\b',  # Acronyms
            r'\b\d+\.\d+\b',  # Version numbers
            r'\b[a-zA-Z]+_[a-zA-Z]+\b',  # Technical terms with underscores
        ]

    async def chunk_text(self, 
                        text: str, 
                        source_lang: str = 'auto',
                        target_lang: str = 'en') -> ChunkingResult:
        """
        Perform context-aware semantic chunking of input text.
        
        Args:
            text: Input text to chunk
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            ChunkingResult with optimized chunks and metadata
        """
        if not text.strip():
            return ChunkingResult(
                chunks=[],
                chunk_boundaries=[],
                content_type=ContentType.CONVERSATIONAL,
                coherence_score=0.0,
                optimal_size_estimate=0,
                metadata={"error": "Empty input text"}
            )
        
        # Analyze discourse features
        discourse_features = self._analyze_discourse(text, source_lang)
        
        # Classify content type
        content_type = self._classify_content_type(text, discourse_features, source_lang)
        
        # Select chunking strategy based on content type
        if content_type == ContentType.EMOTIONAL:
            chunks, boundaries = await self._chunk_emotional_content(text, discourse_features)
        elif content_type == ContentType.TECHNICAL:
            chunks, boundaries = await self._chunk_technical_content(text, discourse_features)
        elif content_type == ContentType.CONVERSATIONAL:
            chunks, boundaries = await self._chunk_conversational_content(text, discourse_features)
        else:
            chunks, boundaries = await self._chunk_semantic_similarity(text, discourse_features)
        
        # Calculate coherence score
        coherence_score = await self._calculate_coherence_score(chunks)
        
        # Estimate optimal chunk size for this content type
        optimal_size = self._estimate_optimal_size(text, content_type, discourse_features)
        
        return ChunkingResult(
            chunks=chunks,
            chunk_boundaries=boundaries,
            content_type=content_type,
            coherence_score=coherence_score,
            optimal_size_estimate=optimal_size,
            metadata={
                "discourse_features": discourse_features,
                "total_length": len(text),
                "num_chunks": len(chunks),
                "avg_chunk_size": sum(len(c) for c in chunks) // len(chunks) if chunks else 0
            }
        )

    def _analyze_discourse(self, text: str, source_lang: str) -> DiscourseFeatures:
        """Analyze discourse features for informed chunking decisions."""
        sentences = nltk.sent_tokenize(text)
        
        # Basic sentence analysis
        sentence_count = len(sentences)
        avg_sentence_length = sum(len(s) for s in sentences) / sentence_count if sentences else 0
        
        # Punctuation analysis
        punctuation_count = sum(1 for char in text if char in '!?.,;:')
        punctuation_density = punctuation_count / len(text) if text else 0
        
        # Discourse connectors
        connectors = self.discourse_connectors.get(source_lang, self.discourse_connectors['default'])
        connector_count = sum(1 for connector in connectors if connector.lower() in text.lower())
        
        # Emotion indicators
        emotions = self.emotion_indicators.get(source_lang, self.emotion_indicators['default'])
        emotion_count = sum(1 for emotion in emotions if emotion.lower() in text.lower())
        
        # Technical terms
        technical_count = sum(len(re.findall(pattern, text)) for pattern in self.technical_patterns)
        
        # Simple coreference detection (pronouns and repeated entities)
        coreference_chains = self._detect_coreference_chains(sentences)
        
        return DiscourseFeatures(
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            punctuation_density=punctuation_density,
            connector_count=connector_count,
            emotion_indicators=emotion_count,
            technical_terms=technical_count,
            coreference_chains=coreference_chains
        )

    def _classify_content_type(self, text: str, features: DiscourseFeatures, source_lang: str) -> ContentType:
        """Classify content type for appropriate chunking strategy."""
        # Score different content types
        emotional_score = features.emotion_indicators * 2 + features.punctuation_density * 10
        technical_score = features.technical_terms * 3 + (1 if features.avg_sentence_length > 25 else 0)
        
        # Enhanced emotional detection
        text_lower = text.lower()
        emotional_words = ['amazing', 'incredible', 'grateful', 'terrified', 'overwhelming', 'crying', 'joy', 'believe', 'absolutely']
        emotional_phrases = ['can\'t believe', 'so grateful', 'absolutely amazing', 'this is incredible']
        
        emotional_word_count = sum(1 for word in emotional_words if word in text_lower)
        emotional_phrase_count = sum(1 for phrase in emotional_phrases if phrase in text_lower)
        
        if emotional_word_count >= 2 or emotional_phrase_count >= 1:
            emotional_score += 5
        
        # Conversational detection (more specific)
        conversational_indicators = 0
        conversational_indicators += 1 if features.avg_sentence_length < 20 else 0  # Shorter sentences
        conversational_indicators += 1 if len(text) < 500 else 0  # Shorter text
        
        # Check for specific conversational patterns (not emotional)
        conversational_words = ['hey', 'how are you', 'did you', 'pretty crazy', 'stuff happening']
        if any(word in text_lower for word in conversational_words):
            conversational_indicators += 2
        
        # Determine content type (emotional takes priority)
        if emotional_score > 3:
            return ContentType.EMOTIONAL
        elif technical_score > 2:
            return ContentType.TECHNICAL
        elif conversational_indicators >= 2:
            return ContentType.CONVERSATIONAL
        elif features.sentence_count > 5 and features.avg_sentence_length > 20:
            return ContentType.NARRATIVE
        else:
            return ContentType.FORMAL

    async def _chunk_emotional_content(self, text: str, features: DiscourseFeatures) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Chunk emotional content preserving emotional context and flow."""
        sentences = nltk.sent_tokenize(text)
        chunks = []
        boundaries = []
        
        current_chunk = ""
        current_start = 0
        
        for i, sentence in enumerate(sentences):
            # Check if adding this sentence would exceed max size
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(current_chunk.strip())
                boundaries.append((current_start, current_start + len(current_chunk)))
                
                # Start new chunk
                current_start = current_start + len(current_chunk)
                current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            boundaries.append((current_start, current_start + len(current_chunk)))
        
        return chunks, boundaries

    async def _chunk_technical_content(self, text: str, features: DiscourseFeatures) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Chunk technical content preserving technical terms and concepts."""
        # Split on paragraph boundaries first for technical content
        paragraphs = text.split('\n\n')
        chunks = []
        boundaries = []
        
        current_chunk = ""
        current_start = 0
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # If paragraph itself is too long, split it by sentences
            if len(paragraph) > self.max_chunk_size:
                sentences = nltk.sent_tokenize(paragraph)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                        # Save current chunk
                        chunks.append(current_chunk.strip())
                        boundaries.append((current_start, current_start + len(current_chunk)))
                        
                        # Start new chunk
                        current_start = current_start + len(current_chunk)
                        current_chunk = sentence + " "
                    else:
                        current_chunk += sentence + " "
            elif len(current_chunk) + len(paragraph) > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(current_chunk.strip())
                boundaries.append((current_start, current_start + len(current_chunk)))
                
                # Start new chunk
                current_start = current_start + len(current_chunk)
                current_chunk = paragraph + "\n\n"
            else:
                current_chunk += paragraph + "\n\n"
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            boundaries.append((current_start, current_start + len(current_chunk)))
        
        return chunks, boundaries

    async def _chunk_conversational_content(self, text: str, features: DiscourseFeatures) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Chunk conversational content preserving dialogue flow."""
        # For short conversational content, often no chunking needed
        if len(text) <= self.max_chunk_size:
            return [text], [(0, len(text))]
        
        # Split on dialogue markers or sentence boundaries
        sentences = nltk.sent_tokenize(text)
        return await self._chunk_by_similarity(sentences, text)

    async def _chunk_semantic_similarity(self, text: str, features: DiscourseFeatures) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Chunk using semantic similarity between sentences."""
        sentences = nltk.sent_tokenize(text)
        
        if not self.embedder or len(sentences) <= 2:
            # Fallback to simple sentence-based chunking
            return await self._chunk_by_size(sentences, text)
        
        return await self._chunk_by_similarity(sentences, text)

    async def _chunk_by_similarity(self, sentences: List[str], full_text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Group sentences by semantic similarity."""
        if not self.embedder:
            return await self._chunk_by_size(sentences, full_text)
        
        try:
            # Get embeddings for all sentences
            embeddings = self.embedder.encode(sentences)
            
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(embeddings)
            
            # Group sentences by similarity
            groups = []
            used = set()
            
            for i, sentence in enumerate(sentences):
                if i in used:
                    continue
                    
                current_group = [i]
                current_length = len(sentence)
                used.add(i)
                
                # Find similar sentences to group together
                for j in range(i + 1, len(sentences)):
                    if j in used:
                        continue
                    
                    if (similarity_matrix[i][j] > self.similarity_threshold and 
                        current_length + len(sentences[j]) < self.max_chunk_size):
                        current_group.append(j)
                        current_length += len(sentences[j])
                        used.add(j)
                
                groups.append(current_group)
            
            # Convert groups to chunks
            chunks = []
            boundaries = []
            current_pos = 0
            
            for group in groups:
                chunk_sentences = [sentences[i] for i in sorted(group)]
                chunk_text = " ".join(chunk_sentences)
                chunks.append(chunk_text)
                
                boundaries.append((current_pos, current_pos + len(chunk_text)))
                current_pos += len(chunk_text) + 1  # +1 for space between chunks
            
            return chunks, boundaries
            
        except Exception as e:
            logger.warning(f"Similarity-based chunking failed: {e}, falling back to size-based")
            return await self._chunk_by_size(sentences, full_text)

    async def _chunk_by_size(self, sentences: List[str], full_text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """Fallback chunking by size limits."""
        chunks = []
        boundaries = []
        
        current_chunk = ""
        current_start = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size and current_chunk:
                # Save current chunk
                chunks.append(current_chunk.strip())
                boundaries.append((current_start, current_start + len(current_chunk)))
                
                # Start new chunk
                current_start = current_start + len(current_chunk)
                current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            boundaries.append((current_start, current_start + len(current_chunk)))
        
        return chunks, boundaries

    async def _calculate_coherence_score(self, chunks: List[str]) -> float:
        """Calculate coherence score for the chunking result."""
        if not chunks or not self.embedder:
            return 0.5  # Neutral score
        
        try:
            if len(chunks) == 1:
                return 1.0  # Single chunk is perfectly coherent
            
            # Get embeddings for chunks
            embeddings = self.embedder.encode(chunks)
            
            # Calculate average similarity between adjacent chunks
            similarities = []
            for i in range(len(embeddings) - 1):
                sim = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
                similarities.append(sim)
            
            return float(np.mean(similarities))
            
        except Exception as e:
            logger.warning(f"Coherence calculation failed: {e}")
            return 0.5

    def _detect_coreference_chains(self, sentences: List[str]) -> List[List[int]]:
        """Simple coreference detection for discourse analysis."""
        # Basic implementation - look for pronouns and repeated entities
        chains = []
        pronouns = ['he', 'she', 'it', 'they', 'this', 'that', 'these', 'those']
        
        # Track entities mentioned in each sentence
        for i, sentence in enumerate(sentences):
            words = sentence.lower().split()
            
            # Look for pronouns that might refer to previous entities
            for pronoun in pronouns:
                if pronoun in words:
                    # Simple heuristic: create chain with previous sentence
                    if i > 0:
                        chains.append([i - 1, i])
        
        return chains

    def _estimate_optimal_size(self, text: str, content_type: ContentType, features: DiscourseFeatures) -> int:
        """Estimate optimal chunk size based on content analysis."""
        base_size = 300  # Base optimal size
        
        # Adjust based on content type
        if content_type == ContentType.EMOTIONAL:
            # Emotional content often needs larger chunks for context
            base_size = 400
        elif content_type == ContentType.TECHNICAL:
            # Technical content can be chunked smaller
            base_size = 250
        elif content_type == ContentType.CONVERSATIONAL:
            # Conversational content is often already short
            base_size = 200
        
        # Adjust based on sentence length
        if features.avg_sentence_length > 30:
            base_size += 100  # Longer sentences need bigger chunks
        elif features.avg_sentence_length < 10:
            base_size -= 50   # Shorter sentences can use smaller chunks
        
        # Ensure within bounds
        return max(self.min_chunk_size, min(self.max_chunk_size, base_size))


# Utility function for external use
async def chunk_text_semantically(text: str, 
                                 source_lang: str = 'auto',
                                 target_lang: str = 'en',
                                 chunker: Optional[SemanticChunker] = None) -> ChunkingResult:
    """
    Convenience function for semantic text chunking.
    
    Args:
        text: Input text to chunk
        source_lang: Source language code
        target_lang: Target language code
        chunker: Optional pre-initialized chunker
        
    Returns:
        ChunkingResult with optimized chunks
    """
    if chunker is None:
        chunker = SemanticChunker()
    
    return await chunker.chunk_text(text, source_lang, target_lang)