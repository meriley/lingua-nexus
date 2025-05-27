"""
Main entry point for Lingua Nexus Single-Model Translation API.

This module serves as the primary entry point for the new single-model-per-instance
translation architecture. It automatically configures and starts the appropriate
server based on environment variables.
"""

import os
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_server_type() -> str:
    """
    Determine which server type to use based on environment configuration.
    
    Returns:
        str: Server type ('single-model', 'legacy', 'multimodel')
    """
    # Check for explicit server type configuration
    server_type = os.getenv("LINGUA_NEXUS_SERVER_TYPE", "single-model")
    
    # Legacy compatibility: if MODELS_TO_LOAD is set with multiple models, use multimodel
    models_to_load = os.getenv("MODELS_TO_LOAD", "").strip()
    if models_to_load and "," in models_to_load:
        logger.info("Multiple models detected, using multimodel server")
        return "multimodel"
    
    # If specific model is set, use single-model
    model_name = os.getenv("LINGUA_NEXUS_MODEL", "").strip()
    if model_name and server_type == "auto":
        logger.info(f"Single model specified ({model_name}), using single-model server")
        return "single-model"
    
    return server_type


def create_app():
    """
    Create the appropriate FastAPI application based on configuration.
    
    Returns:
        FastAPI: Configured application instance
    """
    server_type = get_server_type()
    
    logger.info(f"Initializing Lingua Nexus server (type: {server_type})")
    
    if server_type == "single-model":
        from .single_model_main import create_app
        model_name = os.getenv("LINGUA_NEXUS_MODEL", "nllb")
        logger.info(f"Starting single-model server for: {model_name}")
        return create_app()
    
    elif server_type == "multimodel":
        # Import the multimodel server
        try:
            from .main_multimodel import app
            logger.info("Starting multimodel server")
            return app
        except ImportError as e:
            logger.error(f"Failed to import multimodel server: {e}")
            logger.info("Falling back to single-model server")
            from .single_model_main import create_app
            return create_app()
    
    elif server_type == "legacy":
        # Import the legacy server
        try:
            from .main import app
            logger.info("Starting legacy NLLB server")
            return app
        except ImportError as e:
            logger.error(f"Failed to import legacy server: {e}")
            logger.info("Falling back to single-model server")
            from .single_model_main import create_app
            return create_app()
    
    else:
        logger.warning(f"Unknown server type: {server_type}, using single-model server")
        from .single_model_main import create_app
        return create_app()


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    
    # Log startup configuration
    model_name = os.getenv("LINGUA_NEXUS_MODEL", "nllb")
    server_type = get_server_type()
    
    logger.info("=" * 60)
    logger.info("Lingua Nexus Translation API")
    logger.info("=" * 60)
    logger.info(f"Server Type: {server_type}")
    logger.info(f"Model: {model_name}")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Workers: {workers}")
    logger.info("=" * 60)
    
    # Run server
    uvicorn.run(
        "app.main_new:app",
        host=host,
        port=port,
        workers=workers if workers > 1 else None,
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )