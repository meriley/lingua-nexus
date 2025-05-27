#!/usr/bin/env python3
"""
Check system resources for model loading debugging.
"""

import os
import psutil
import subprocess
from typing import Dict


def bytes_to_human(bytes_value: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def check_memory_info() -> Dict[str, any]:
    """Check system RAM and swap information."""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        "ram": {
            "total": bytes_to_human(memory.total),
            "available": bytes_to_human(memory.available),
            "used": bytes_to_human(memory.used),
            "percent": memory.percent,
            "available_gb": memory.available / (1024**3)
        },
        "swap": {
            "total": bytes_to_human(swap.total),
            "used": bytes_to_human(swap.used),
            "free": bytes_to_human(swap.free),
            "percent": swap.percent,
            "total_gb": swap.total / (1024**3)
        }
    }


def check_gpu_memory() -> Dict[str, any]:
    """Check GPU memory availability."""
    gpu_info = {"available": False}
    
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", 
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            gpu_info["available"] = True
            gpu_info["devices"] = []
            
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpu_info["devices"].append({
                        "id": i,
                        "name": parts[0],
                        "memory_total_mb": int(parts[1]),
                        "memory_used_mb": int(parts[2]),
                        "memory_free_mb": int(parts[3]),
                        "memory_free_gb": int(parts[3]) / 1024
                    })
    except FileNotFoundError:
        gpu_info["error"] = "nvidia-smi not found"
    
    return gpu_info


def analyze_resource_requirements() -> Dict[str, any]:
    """Analyze if system meets model loading requirements."""
    memory_info = check_memory_info()
    
    analysis = {
        "can_load_nllb": False,
        "can_load_aya": False,
        "issues": [],
        "warnings": []
    }
    
    # NLLB requirements (~5GB)
    nllb_required_gb = 5.0
    # Aya requirements (~16GB)
    aya_required_gb = 16.0
    
    available_gb = memory_info["ram"]["available_gb"]
    
    if available_gb >= nllb_required_gb:
        analysis["can_load_nllb"] = True
    else:
        analysis["issues"].append(f"Insufficient RAM for NLLB: {available_gb:.1f}GB available, {nllb_required_gb}GB required")
    
    if available_gb >= aya_required_gb:
        analysis["can_load_aya"] = True
    else:
        analysis["issues"].append(f"Insufficient RAM for Aya: {available_gb:.1f}GB available, {aya_required_gb}GB required")
    
    if memory_info["swap"]["total_gb"] < 2.0:
        analysis["warnings"].append("Limited swap space - consider adding more")
    
    return analysis


def main():
    """Main execution function."""
    print("System Resource Analysis")
    print("=" * 40)
    
    # Memory info
    memory_info = check_memory_info()
    print("\nMemory Information:")
    print(f"  RAM Total: {memory_info['ram']['total']}")
    print(f"  RAM Available: {memory_info['ram']['available']} ({memory_info['ram']['available_gb']:.1f} GB)")
    print(f"  RAM Used: {memory_info['ram']['used']} ({memory_info['ram']['percent']:.1f}%)")
    print(f"  Swap Total: {memory_info['swap']['total']}")
    print(f"  Swap Used: {memory_info['swap']['used']} ({memory_info['swap']['percent']:.1f}%)")
    
    # GPU info
    gpu_info = check_gpu_memory()
    print("\nGPU Information:")
    if gpu_info["available"]:
        for device in gpu_info["devices"]:
            print(f"  GPU {device['id']}: {device['name']}")
            print(f"    Total: {device['memory_total_mb']} MB")
            print(f"    Free: {device['memory_free_mb']} MB ({device['memory_free_gb']:.1f} GB)")
    else:
        print("  No GPU available")
    
    # Analysis
    analysis = analyze_resource_requirements()
    print("\nModel Loading Analysis:")
    print(f"  Can load NLLB (5GB): {'✓' if analysis['can_load_nllb'] else '✗'}")
    print(f"  Can load Aya (16GB): {'✓' if analysis['can_load_aya'] else '✗'}")
    
    if analysis["issues"]:
        print("\nISSUES:")
        for issue in analysis["issues"]:
            print(f"  ❌ {issue}")
    
    if analysis["warnings"]:
        print("\nWARNINGS:")
        for warning in analysis["warnings"]:
            print(f"  ⚠️  {warning}")
    
    print("\n" + "=" * 40)


if __name__ == "__main__":
    main()