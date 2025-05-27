"""
Model registry for managing translation model instances.

This module provides a centralized registry for managing different translation
models, enabling dynamic model loading, selection, and lifecycle management.
"""

from typing import Dict, List, Optional, Type, Any
import logging
import asyncio
from .base import TranslationModel, ModelError, ModelInitializationError

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry for managing available translation models."""
    
    def __init__(self):
        """Initialize empty model registry."""
        self._models: Dict[str, TranslationModel] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}
        self._default_model: Optional[str] = None
        self._model_factories: Dict[str, Type[TranslationModel]] = {}
        self._loading_tasks: Dict[str, asyncio.Task] = {}
        
        # Register default model factories
        self._register_default_factories()
    
    def _register_default_factories(self):
        """Register default model factories."""
        try:
            from .nllb_model import NLLBModel
            from .aya_model import AyaModel
            
            self._model_factories['nllb'] = NLLBModel
            self._model_factories['aya'] = AyaModel
            logger.info("Registered default model factories: nllb, aya")
        except ImportError as e:
            logger.warning(f"Could not register some model factories: {e}")
    
    def register_model_factory(self, model_type: str, model_class: Type[TranslationModel]):
        """
        Register a model factory class for a specific model type.
        
        Args:
            model_type: Type identifier for the model (e.g., 'nllb', 'aya')
            model_class: Class that implements TranslationModel interface
        """
        self._model_factories[model_type] = model_class
        logger.info(f"Registered model factory for type: {model_type}")
    
    def register_model(self, name: str, model: TranslationModel):
        """
        Register a translation model instance.
        
        Args:
            name: Unique identifier for the model
            model: TranslationModel instance
            
        Raises:
            ValueError: If model name already exists
        """
        if name in self._models:
            logger.warning(f"Model '{name}' already registered, replacing...")
        
        self._models[name] = model
        self._model_configs[name] = model.config.copy()
        
        # Set as default if it's the first model
        if self._default_model is None:
            self._default_model = name
            logger.info(f"Set '{name}' as default model")
        
        logger.info(f"Registered model: {name}")
    
    def create_and_register_model(self, name: str, model_type: str, config: Dict[str, Any]) -> TranslationModel:
        """
        Create a model instance from factory and register it.
        
        Args:
            name: Unique identifier for the model
            model_type: Type of model to create (must be registered factory)
            config: Configuration dictionary for model initialization
            
        Returns:
            Created and registered TranslationModel instance
            
        Raises:
            ValueError: If model type is not registered
            ModelInitializationError: If model creation fails
        """
        if model_type not in self._model_factories:
            available_types = list(self._model_factories.keys())
            raise ValueError(f"Model type '{model_type}' not registered. Available: {available_types}")
        
        model_class = self._model_factories[model_type]
        
        try:
            # Add name to config if not present
            if 'name' not in config:
                config['name'] = name
                
            model = model_class(config)
            self.register_model(name, model)
            return model
            
        except Exception as e:
            raise ModelInitializationError(f"Failed to create model '{name}' of type '{model_type}': {e}")
    
    def get_model(self, name: Optional[str] = None) -> TranslationModel:
        """
        Get model by name or return default model.
        
        Args:
            name: Model name to retrieve, None for default
            
        Returns:
            TranslationModel instance
            
        Raises:
            ValueError: If model name not found or no default set
        """
        model_name = name or self._default_model
        
        if not model_name:
            raise ValueError("No model specified and no default model set")
            
        if model_name not in self._models:
            available = list(self._models.keys())
            raise ValueError(f"Model '{model_name}' not found. Available: {available}")
        
        return self._models[model_name]
    
    def unregister_model(self, name: str) -> bool:
        """
        Unregister a model from the registry.
        
        Args:
            name: Name of model to unregister
            
        Returns:
            True if model was unregistered, False if not found
        """
        if name not in self._models:
            logger.warning(f"Cannot unregister model '{name}': not found")
            return False
        
        del self._models[name]
        del self._model_configs[name]
        
        # Update default if necessary
        if self._default_model == name:
            self._default_model = next(iter(self._models.keys())) if self._models else None
            if self._default_model:
                logger.info(f"Default model changed to: {self._default_model}")
            else:
                logger.info("No default model set (registry empty)")
        
        logger.info(f"Unregistered model: {name}")
        return True
    
    def list_models(self) -> List[str]:
        """
        Get list of registered model names.
        
        Returns:
            List of model names
        """
        return list(self._models.keys())
    
    def list_available_models(self) -> List[str]:
        """
        Get list of models that are currently available for use.
        
        Returns:
            List of available model names
        """
        return [name for name, model in self._models.items() if model.is_available()]
    
    def get_default_model(self) -> Optional[str]:
        """
        Get the name of the default model.
        
        Returns:
            Default model name or None if not set
        """
        return self._default_model
    
    def set_default_model(self, name: str):
        """
        Set the default model.
        
        Args:
            name: Name of model to set as default
            
        Raises:
            ValueError: If model name is not registered
        """
        if name not in self._models:
            available = list(self._models.keys())
            raise ValueError(f"Model '{name}' not registered. Available: {available}")
        
        old_default = self._default_model
        self._default_model = name
        logger.info(f"Default model changed from '{old_default}' to '{name}'")
    
    def get_model_info(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a model.
        
        Args:
            name: Model name, None for default
            
        Returns:
            Dictionary with model information
            
        Raises:
            ValueError: If model not found
        """
        model = self.get_model(name)
        info = model.get_model_info()
        
        # Add registry-specific information
        info.update({
            'is_default': model.model_name == self._default_model,
            'supported_languages': model.get_supported_languages()
        })
        
        return info
    
    def get_all_models_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered models.
        
        Returns:
            Dictionary mapping model names to their information
        """
        return {name: self.get_model_info(name) for name in self._models.keys()}
    
    def health_check(self) -> Dict[str, bool]:
        """
        Check health status of all registered models.
        
        Returns:
            Dictionary mapping model names to availability status
        """
        return {name: model.is_available() for name, model in self._models.items()}
    
    def get_models_by_language_support(self, source_lang: str, target_lang: str) -> List[str]:
        """
        Get models that support a specific language pair.
        
        Args:
            source_lang: Source language ISO code
            target_lang: Target language ISO code
            
        Returns:
            List of model names that support the language pair
        """
        supported_models = []
        
        for name, model in self._models.items():
            try:
                if model.supports_language_pair(source_lang, target_lang):
                    supported_models.append(name)
            except Exception as e:
                logger.warning(f"Error checking language support for model '{name}': {e}")
        
        return supported_models
    
    async def load_model(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Load a model asynchronously using predefined configurations.
        
        Args:
            model_name: Name/type of model to load ('nllb', 'aya')
            config: Optional configuration override
        """
        # Check if already loading
        if model_name in self._loading_tasks:
            logger.info(f"Model {model_name} is already being loaded, waiting...")
            await self._loading_tasks[model_name]
            return
        
        # Check if already loaded
        if model_name in self._models and self._models[model_name].is_available():
            logger.info(f"Model {model_name} is already loaded and available")
            return
        
        # Create loading task
        self._loading_tasks[model_name] = asyncio.create_task(
            self._async_load_model(model_name, config)
        )
        
        try:
            await self._loading_tasks[model_name]
        finally:
            if model_name in self._loading_tasks:
                del self._loading_tasks[model_name]
    
    async def _async_load_model(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """Internal async model loading implementation."""
        try:
            logger.info(f"Starting to load model: {model_name}")
            
            # Get default config for model type
            model_config = self._get_default_config(model_name)
            if config:
                model_config.update(config)
            
            # Add name to config
            model_config['name'] = model_name
            
            # Create model instance
            if model_name not in self._model_factories:
                # Try to use model_name as model_type
                model_type = model_name.lower()
                if model_type not in self._model_factories:
                    available_types = list(self._model_factories.keys())
                    raise ValueError(f"Model type '{model_type}' not registered. Available: {available_types}")
                model_class = self._model_factories[model_type]
            else:
                model_class = self._model_factories[model_name]
            
            # Run model creation in thread to avoid blocking
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(None, model_class, model_config)
            
            # Register the model
            self.register_model(model_name, model)
            
            logger.info(f"Successfully loaded model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise ModelInitializationError(f"Failed to load model {model_name}: {e}")
    
    def _get_default_config(self, model_name: str) -> Dict[str, Any]:
        """Get default configuration for a model."""
        configs = {
            'nllb': {
                'model_path': 'facebook/nllb-200-distilled-600M',
                'device': 'auto',
                'max_length': 512,
                'use_pipeline': True
            },
            'aya': {
                'model_path': 'CohereForAI/aya-101',
                'device': 'auto',
                'max_length': 512,
                'temperature': 0.3,
                'top_p': 0.9,
                'use_quantization': True,
                'load_in_8bit': True
            }
        }
        
        return configs.get(model_name.lower(), {})
    
    def unload_model(self, name: str):
        """
        Unload a model and clean up its resources.
        
        Args:
            name: Name of model to unload
        """
        if name not in self._models:
            logger.warning(f"Cannot unload model '{name}': not found")
            return
        
        # Clean up model resources
        try:
            model = self._models[name]
            if hasattr(model, 'cleanup'):
                model.cleanup()
        except Exception as e:
            logger.error(f"Error during model cleanup for '{name}': {e}")
        
        # Remove from registry
        self.unregister_model(name)
        logger.info(f"Unloaded model: {name}")
    
    def cleanup_all(self):
        """Clean up all models and clear registry."""
        logger.info("Cleaning up all models...")
        
        for name in list(self._models.keys()):
            try:
                self.unload_model(name)
            except Exception as e:
                logger.error(f"Error cleaning up model '{name}': {e}")
        
        # Cancel any pending loading tasks
        for task in self._loading_tasks.values():
            if not task.done():
                task.cancel()
        
        self._loading_tasks.clear()
        self.clear()
        logger.info("All models cleaned up")

    def clear(self):
        """Clear all registered models."""
        self._models.clear()
        self._model_configs.clear()
        self._default_model = None
        logger.info("Cleared all models from registry")
    
    def __len__(self) -> int:
        """Return number of registered models."""
        return len(self._models)
    
    def __contains__(self, name: str) -> bool:
        """Check if model name is registered."""
        return name in self._models
    
    def __iter__(self):
        """Iterate over model names."""
        return iter(self._models.keys())


class ModelFactory:
    """Factory for creating translation model instances."""
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> TranslationModel:
        """
        Create a model instance from configuration.
        
        Args:
            config: Configuration dictionary containing:
                - type: Model type ('nllb', 'aya', etc.)
                - Additional model-specific parameters
                
        Returns:
            Initialized TranslationModel instance
            
        Raises:
            ValueError: If required configuration is missing
            ModelInitializationError: If model creation fails
        """
        if 'type' not in config:
            raise ValueError("Model configuration must include 'type' field")
        
        model_type = config['type'].lower()
        
        # Import model classes dynamically to avoid circular imports
        if model_type == 'nllb':
            from .nllb_model import NLLBModel
            return NLLBModel(config)
        elif model_type == 'aya':
            from .aya_model import AyaModel
            return AyaModel(config)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    @staticmethod
    def create_nllb_model(config: Dict[str, Any]) -> 'NLLBModel':
        """Create NLLB model instance."""
        from .nllb_model import NLLBModel
        return NLLBModel(config)
    
    @staticmethod
    def create_aya_model(config: Dict[str, Any]) -> 'AyaModel':
        """Create Aya 8B model instance."""
        from .aya_model import AyaModel
        return AyaModel(config)