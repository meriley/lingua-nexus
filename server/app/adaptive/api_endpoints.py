"""
FastAPI Endpoints for Adaptive Translation System

Provides REST API endpoints for semantic chunking, adaptive translation,
and progressive translation with real-time updates.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from .adaptive_controller import (
    AdaptiveTranslationController, 
    AdaptiveTranslationRequest,
    TranslationResult,
    TranslationUpdate,
    TranslationStage
)
from .semantic_chunker import SemanticChunker, ContentType
from .quality_assessment import QualityMetricsEngine
from .cache_manager import IntelligentCacheManager

logger = logging.getLogger(__name__)

# Pydantic models for API

class SemanticChunkRequest(BaseModel):
    """Request for semantic chunking."""
    text: str = Field(..., description="Text to chunk")
    source_lang: str = Field(default="auto", description="Source language code")
    target_lang: str = Field(default="en", description="Target language code")
    min_chunk_size: int = Field(default=150, description="Minimum chunk size")
    max_chunk_size: int = Field(default=600, description="Maximum chunk size")


class SemanticChunkResponse(BaseModel):
    """Response for semantic chunking."""
    chunks: List[str]
    chunk_boundaries: List[tuple]
    content_type: str
    coherence_score: float
    optimal_size_estimate: int
    metadata: Dict[str, Any]


class AdaptiveTranslateRequest(BaseModel):
    """Request for adaptive translation."""
    text: str = Field(..., description="Text to translate")
    source_lang: str = Field(..., description="Source language code")
    target_lang: str = Field(..., description="Target language code")
    api_key: str = Field(..., description="API key for translation service")
    user_preference: str = Field(default="balanced", description="User preference: fast, balanced, quality")
    force_optimization: bool = Field(default=False, description="Force optimization regardless of quality")
    max_optimization_time: float = Field(default=5.0, description="Maximum time for optimization in seconds")


class TranslationResponse(BaseModel):
    """Response for translation."""
    translation: str
    original_text: str
    quality_score: float
    quality_grade: str
    optimization_applied: bool
    processing_time: float
    cache_hit: bool
    metadata: Dict[str, Any]


class QualityAssessmentRequest(BaseModel):
    """Request for quality assessment."""
    original: str = Field(..., description="Original text")
    translation: str = Field(..., description="Translated text")
    source_lang: str = Field(default="auto", description="Source language")
    target_lang: str = Field(default="en", description="Target language")


class QualityAssessmentResponse(BaseModel):
    """Response for quality assessment."""
    overall_score: float
    quality_grade: str
    dimension_scores: Dict[str, float]
    optimization_needed: bool
    improvement_suggestions: List[str]
    confidence_interval: tuple


class CacheStatsResponse(BaseModel):
    """Response for cache statistics."""
    hit_rate: float
    total_requests: int
    cache_hits: int
    cache_misses: int
    memory_usage: Dict[str, int]


# Global instances (will be initialized by the app)
chunker: Optional[SemanticChunker] = None
quality_engine: Optional[QualityMetricsEngine] = None
cache_manager: Optional[IntelligentCacheManager] = None
adaptive_controller: Optional[AdaptiveTranslationController] = None

# Router
router = APIRouter(prefix="/adaptive", tags=["adaptive-translation"])


async def get_translation_function():
    """Get the translation function (to be implemented by the main app)."""
    # This will be injected by the main application
    raise HTTPException(status_code=500, detail="Translation function not configured")


async def initialize_adaptive_system(translation_func, redis_url: str = "redis://localhost:6379"):
    """Initialize the adaptive translation system."""
    global chunker, quality_engine, cache_manager, adaptive_controller
    
    # Initialize components
    chunker = SemanticChunker()
    quality_engine = QualityMetricsEngine()
    
    # Initialize cache manager
    cache_manager = IntelligentCacheManager(redis_url=redis_url)
    await cache_manager.initialize()
    
    # Initialize adaptive controller
    adaptive_controller = AdaptiveTranslationController(
        translation_function=translation_func,
        chunker=chunker,
        quality_engine=quality_engine,
        cache_manager=cache_manager
    )
    
    logger.info("Adaptive translation system initialized successfully")


@router.post("/chunk", response_model=SemanticChunkResponse)
async def semantic_chunk_text(request: SemanticChunkRequest):
    """
    Perform semantic chunking of text.
    
    Returns optimized text chunks with discourse analysis and content type detection.
    """
    if not chunker:
        raise HTTPException(status_code=500, detail="Semantic chunker not initialized")
    
    try:
        # Create temporary chunker with custom parameters if provided
        temp_chunker = SemanticChunker(
            min_chunk_size=request.min_chunk_size,
            max_chunk_size=request.max_chunk_size
        )
        
        result = await temp_chunker.chunk_text(
            request.text, request.source_lang, request.target_lang
        )
        
        return SemanticChunkResponse(
            chunks=result.chunks,
            chunk_boundaries=result.chunk_boundaries,
            content_type=result.content_type.value,
            coherence_score=result.coherence_score,
            optimal_size_estimate=result.optimal_size_estimate,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Semantic chunking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chunking failed: {str(e)}")


@router.post("/translate", response_model=TranslationResponse)
async def adaptive_translate(request: AdaptiveTranslateRequest):
    """
    Perform adaptive translation with intelligent optimization.
    
    Uses semantic chunking, quality assessment, and optimization to provide
    the best possible translation quality within time constraints.
    """
    if not adaptive_controller:
        raise HTTPException(status_code=500, detail="Adaptive controller not initialized")
    
    try:
        # Convert to internal request format
        internal_request = AdaptiveTranslationRequest(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            api_key=request.api_key,
            user_preference=request.user_preference,
            force_optimization=request.force_optimization,
            max_optimization_time=request.max_optimization_time
        )
        
        # Perform translation
        result = await adaptive_controller.translate(internal_request)
        
        return TranslationResponse(
            translation=result.translation,
            original_text=result.original_text,
            quality_score=result.quality_metrics.overall_score,
            quality_grade=result.quality_metrics.quality_grade,
            optimization_applied=result.optimization_applied,
            processing_time=result.processing_time,
            cache_hit=result.cache_hit,
            metadata={
                **result.metadata,
                "stage_times": result.stage_times,
                "chunking_metadata": result.chunking_result.metadata if result.chunking_result else {}
            }
        )
        
    except Exception as e:
        logger.error(f"Adaptive translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/translate/progressive")
async def progressive_translate(request: AdaptiveTranslateRequest):
    """
    Perform progressive translation with real-time updates.
    
    Returns a streaming response with translation progress updates,
    allowing clients to show immediate results and quality improvements.
    """
    if not adaptive_controller:
        raise HTTPException(status_code=500, detail="Adaptive controller not initialized")
    
    async def generate_updates():
        """Generate streaming updates for progressive translation."""
        try:
            # Convert to internal request format
            internal_request = AdaptiveTranslationRequest(
                text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                api_key=request.api_key,
                user_preference=request.user_preference,
                force_optimization=request.force_optimization,
                max_optimization_time=request.max_optimization_time
            )
            
            # Track updates
            updates = []
            
            async def update_callback(update: TranslationUpdate):
                """Callback for receiving translation updates."""
                update_data = {
                    "stage": update.stage.value,
                    "translation": update.translation,
                    "progress": update.progress,
                    "status_message": update.status_message,
                    "quality_score": update.quality_metrics.overall_score if update.quality_metrics else None,
                    "quality_grade": update.quality_metrics.quality_grade if update.quality_metrics else None,
                    "metadata": update.metadata or {}
                }
                
                updates.append(update_data)
                
                # Send update as Server-Sent Event
                yield f"data: {json.dumps(update_data)}\n\n"
            
            # Perform progressive translation
            final_result = await adaptive_controller.progressive_translate(
                internal_request, update_callback
            )
            
            # Send final result
            final_data = {
                "stage": "completed",
                "translation": final_result.translation,
                "progress": 1.0,
                "status_message": "Translation completed",
                "quality_score": final_result.quality_metrics.overall_score,
                "quality_grade": final_result.quality_metrics.quality_grade,
                "optimization_applied": final_result.optimization_applied,
                "processing_time": final_result.processing_time,
                "cache_hit": final_result.cache_hit,
                "metadata": {
                    **final_result.metadata,
                    "stage_times": final_result.stage_times
                }
            }
            
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            logger.error(f"Progressive translation failed: {e}")
            error_data = {
                "stage": "error",
                "error": str(e),
                "progress": 0.0,
                "status_message": f"Translation failed: {str(e)}"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_updates(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@router.post("/quality/assess", response_model=QualityAssessmentResponse)
async def assess_translation_quality(request: QualityAssessmentRequest):
    """
    Assess translation quality using multi-dimensional metrics.
    
    Provides detailed quality analysis beyond simple confidence scores.
    """
    if not quality_engine:
        raise HTTPException(status_code=500, detail="Quality engine not initialized")
    
    try:
        from .quality_assessment import TranslationPair
        
        # Create translation pair
        translation_pair = TranslationPair(
            original=request.original,
            translation=request.translation,
            language_pair=(request.source_lang, request.target_lang)
        )
        
        # Assess quality
        quality_metrics = await quality_engine.assess_quality(translation_pair)
        
        return QualityAssessmentResponse(
            overall_score=quality_metrics.overall_score,
            quality_grade=quality_metrics.quality_grade,
            dimension_scores={
                dim.value: score for dim, score in quality_metrics.dimension_scores.items()
            },
            optimization_needed=quality_metrics.optimization_needed,
            improvement_suggestions=quality_metrics.improvement_suggestions,
            confidence_interval=quality_metrics.confidence_interval
        )
        
    except Exception as e:
        logger.error(f"Quality assessment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quality assessment failed: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_statistics():
    """
    Get cache performance statistics.
    
    Returns cache hit rates, memory usage, and performance metrics.
    """
    if not cache_manager:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    
    try:
        stats = await cache_manager.get_statistics()
        
        return CacheStatsResponse(
            hit_rate=stats.hit_rate,
            total_requests=stats.total_requests,
            cache_hits=stats.cache_hits,
            cache_misses=stats.cache_misses,
            memory_usage=stats.memory_usage or {}
        )
        
    except Exception as e:
        logger.error(f"Failed to get cache statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache statistics: {str(e)}")


@router.post("/cache/invalidate")
async def invalidate_cache(
    source_lang: str,
    target_lang: str,
    content_type: Optional[str] = None
):
    """
    Invalidate cache entries matching the specified pattern.
    
    Useful for clearing cache when translation models are updated.
    """
    if not cache_manager:
        raise HTTPException(status_code=500, detail="Cache manager not initialized")
    
    try:
        await cache_manager.invalidate_pattern(
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type
        )
        
        return {"message": f"Cache invalidated for {source_lang}->{target_lang}"}
        
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")


@router.get("/stats")
async def get_system_statistics():
    """
    Get comprehensive system statistics.
    
    Returns performance metrics for all components of the adaptive system.
    """
    if not adaptive_controller:
        raise HTTPException(status_code=500, detail="Adaptive controller not initialized")
    
    try:
        stats = await adaptive_controller.get_performance_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get system statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system statistics: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns the status of all system components.
    """
    health_status = {
        "status": "healthy",
        "components": {
            "chunker": chunker is not None,
            "quality_engine": quality_engine is not None,
            "cache_manager": cache_manager is not None,
            "adaptive_controller": adaptive_controller is not None
        }
    }
    
    # Check Redis connectivity if cache manager exists
    if cache_manager and cache_manager.redis_client:
        try:
            await cache_manager.redis_client.ping()
            health_status["components"]["redis"] = True
        except Exception:
            health_status["components"]["redis"] = False
            health_status["status"] = "degraded"
    
    # Overall health check
    if not all(health_status["components"].values()):
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status