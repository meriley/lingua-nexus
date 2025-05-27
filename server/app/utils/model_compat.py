"""
PyTorch model compatibility layer for cross-version support.

This module provides compatibility utilities for working with different PyTorch versions,
particularly for device management and model loading operations.
"""

import torch
import logging
from typing import Union, Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_device(strategy: str = 'auto') -> torch.device:
    """
    Get torch device with compatibility across versions.
    
    Args:
        strategy: Device selection strategy ('auto', 'cuda', 'cpu', 'cuda:0', etc.)
        
    Returns:
        torch.device object
    """
    if strategy == 'auto':
        if torch.cuda.is_available():
            device = torch.device('cuda')
            logger.info(f"Auto-selected CUDA device: {device}")
        else:
            device = torch.device('cpu')
            logger.info("Auto-selected CPU device (CUDA not available)")
    elif strategy.startswith('cuda'):
        if torch.cuda.is_available():
            device = torch.device(strategy)
            logger.info(f"Using specified CUDA device: {device}")
        else:
            logger.warning(f"CUDA not available, falling back to CPU instead of {strategy}")
            device = torch.device('cpu')
    else:
        device = torch.device(strategy)
        logger.info(f"Using specified device: {device}")
    
    return device


def get_device_map(model_size_gb: float, available_memory: Optional[Dict[int, float]] = None) -> Union[Dict[str, Any], str]:
    """
    Create device map for model parallelism.
    
    Args:
        model_size_gb: Estimated model size in GB
        available_memory: Dict mapping GPU indices to available memory in GB
        
    Returns:
        Device map dict or 'auto' string for automatic mapping
    """
    if not torch.cuda.is_available():
        logger.info("No CUDA devices available, using CPU")
        return {"": "cpu"}
    
    # Get available memory if not provided
    if available_memory is None:
        available_memory = {}
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            # Get free memory (total - reserved)
            free_memory = props.total_memory / (1024**3)  # Convert to GB
            if torch.cuda.is_available():
                try:
                    allocated = torch.cuda.memory_allocated(i) / (1024**3)
                    free_memory -= allocated
                except:
                    pass
            available_memory[i] = free_memory
            logger.debug(f"GPU {i}: {free_memory:.2f} GB available")
    
    # Simple device mapping strategy
    if len(available_memory) == 0:
        return {"": "cpu"}
    
    # Check if model fits on single GPU
    for gpu_id, memory in available_memory.items():
        if memory > model_size_gb * 1.2:  # 20% buffer
            logger.info(f"Model fits on GPU {gpu_id} with {memory:.2f} GB available")
            return {"": f"cuda:{gpu_id}"}
    
    # For multi-GPU, use auto mapping
    logger.info("Model requires multi-GPU setup, using auto device map")
    return "auto"


def check_memory_availability(required_gb: float, device: Union[torch.device, str]) -> bool:
    """
    Check if device has sufficient memory.
    
    Args:
        required_gb: Required memory in GB
        device: Device to check
        
    Returns:
        True if sufficient memory available
    """
    if isinstance(device, str):
        device = torch.device(device)
    
    if device.type == 'cpu':
        # For CPU, we'll assume enough system RAM is available
        # Could implement psutil check here if needed
        logger.info("CPU device selected, assuming sufficient system memory")
        return True
    
    elif device.type == 'cuda':
        if not torch.cuda.is_available():
            logger.warning("CUDA device requested but not available")
            return False
        
        device_id = device.index if device.index is not None else 0
        
        try:
            props = torch.cuda.get_device_properties(device_id)
            total_memory_gb = props.total_memory / (1024**3)
            
            # Get current memory usage
            allocated_gb = torch.cuda.memory_allocated(device_id) / (1024**3)
            reserved_gb = torch.cuda.memory_reserved(device_id) / (1024**3)
            
            available_gb = total_memory_gb - reserved_gb
            
            logger.info(f"GPU {device_id} memory: {available_gb:.2f} GB available "
                       f"({total_memory_gb:.2f} GB total, {allocated_gb:.2f} GB allocated, "
                       f"{reserved_gb:.2f} GB reserved)")
            
            # Check with 10% buffer
            has_memory = available_gb > required_gb * 1.1
            
            if not has_memory:
                logger.warning(f"Insufficient GPU memory: need {required_gb:.2f} GB, "
                             f"have {available_gb:.2f} GB available")
            
            return has_memory
            
        except Exception as e:
            logger.error(f"Error checking GPU memory: {e}")
            return False
    
    else:
        logger.warning(f"Unknown device type: {device.type}")
        return False


def get_torch_dtype(dtype_config: Union[str, torch.dtype]) -> torch.dtype:
    """
    Convert dtype configuration to torch dtype.
    
    Args:
        dtype_config: String or torch.dtype
        
    Returns:
        torch.dtype object
    """
    if isinstance(dtype_config, torch.dtype):
        return dtype_config
    
    dtype_map = {
        'auto': torch.float16 if torch.cuda.is_available() else torch.float32,
        'float16': torch.float16,
        'fp16': torch.float16,
        'float32': torch.float32,
        'fp32': torch.float32,
        'bfloat16': torch.bfloat16,
        'bf16': torch.bfloat16,
        'float': torch.float32,
        'half': torch.float16,
    }
    
    if dtype_config in dtype_map:
        return dtype_map[dtype_config]
    else:
        logger.warning(f"Unknown dtype config: {dtype_config}, using float32")
        return torch.float32


def prepare_model_kwargs(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare model loading kwargs with compatibility adjustments.
    
    Args:
        config: Model configuration dict
        
    Returns:
        Kwargs dict for model.from_pretrained()
    """
    kwargs = {}
    
    # Handle device selection
    device = config.get('device', 'auto')
    if device != 'auto':
        # For specific device, we'll handle placement after loading
        kwargs['device_map'] = None
    else:
        # Let transformers handle auto device placement
        kwargs['device_map'] = 'auto'
    
    # Handle dtype
    if 'torch_dtype' in config:
        kwargs['torch_dtype'] = get_torch_dtype(config['torch_dtype'])
    elif device == 'cuda' or (device == 'auto' and torch.cuda.is_available()):
        kwargs['torch_dtype'] = torch.float16
    else:
        kwargs['torch_dtype'] = torch.float32
    
    # Memory optimization flags
    kwargs['low_cpu_mem_usage'] = config.get('low_cpu_mem_usage', True)
    
    # Trust remote code if specified
    if config.get('trust_remote_code'):
        kwargs['trust_remote_code'] = True
    
    # Quantization config should be passed separately
    if 'quantization_config' in config:
        kwargs['quantization_config'] = config['quantization_config']
    
    # Use cache
    kwargs['use_cache'] = config.get('use_cache', True)
    
    return kwargs


def clear_memory_cache():
    """Clear GPU memory cache if available."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        logger.info("Cleared GPU memory cache")


def get_model_memory_footprint(model: torch.nn.Module, include_buffers: bool = True) -> float:
    """
    Calculate approximate memory footprint of a model.
    
    Args:
        model: PyTorch model
        include_buffers: Include buffers in calculation
        
    Returns:
        Memory footprint in GB
    """
    total_params = 0
    total_buffers = 0
    
    # Count parameters
    for param in model.parameters():
        total_params += param.numel() * param.element_size()
    
    # Count buffers if requested
    if include_buffers:
        for buffer in model.buffers():
            total_buffers += buffer.numel() * buffer.element_size()
    
    total_bytes = total_params + total_buffers
    total_gb = total_bytes / (1024**3)
    
    logger.debug(f"Model memory footprint: {total_gb:.2f} GB "
                f"(params: {total_params/(1024**3):.2f} GB, "
                f"buffers: {total_buffers/(1024**3):.2f} GB)")
    
    return total_gb