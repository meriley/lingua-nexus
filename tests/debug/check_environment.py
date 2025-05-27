#!/usr/bin/env python3
"""
Check environment and package compatibility for model loading debugging.

This script verifies the compatibility between PyTorch, Transformers, and other
critical packages to identify potential version conflicts.
"""

import sys
import subprocess
import importlib
from typing import Dict, List, Tuple, Optional


def check_python_version() -> Dict[str, str]:
    """Check Python version information."""
    version_info = {
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "full_version": sys.version,
        "executable": sys.executable,
    }
    return version_info


def check_package_version(package_name: str) -> Optional[str]:
    """Get version of an installed package."""
    try:
        module = importlib.import_module(package_name)
        if hasattr(module, "__version__"):
            return module.__version__
        elif hasattr(module, "version"):
            return module.version
        else:
            # Try pip show as fallback
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        return line.split(":")[1].strip()
    except ImportError:
        pass
    return None


def check_cuda_availability() -> Dict[str, any]:
    """Check CUDA availability and version."""
    cuda_info = {"available": False}
    
    try:
        import torch
        cuda_info["available"] = torch.cuda.is_available()
        if cuda_info["available"]:
            cuda_info["device_count"] = torch.cuda.device_count()
            cuda_info["current_device"] = torch.cuda.current_device()
            cuda_info["device_name"] = torch.cuda.get_device_name(0)
            cuda_info["capability"] = torch.cuda.get_device_capability(0)
            cuda_info["cuda_version"] = torch.version.cuda
    except Exception as e:
        cuda_info["error"] = str(e)
    
    # Check nvcc version
    try:
        result = subprocess.run(
            ["nvcc", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            cuda_info["nvcc_output"] = result.stdout
    except FileNotFoundError:
        cuda_info["nvcc"] = "Not found"
    
    return cuda_info


def check_compatibility_matrix() -> Dict[str, any]:
    """Check known compatibility issues between packages."""
    compatibility = {
        "issues": [],
        "warnings": [],
        "recommendations": []
    }
    
    # Get versions
    torch_version = check_package_version("torch")
    transformers_version = check_package_version("transformers")
    tokenizers_version = check_package_version("tokenizers")
    
    if torch_version and transformers_version:
        # PyTorch 2.1.2 + Transformers compatibility
        if torch_version.startswith("2.1."):
            if transformers_version.startswith("4.52."):
                compatibility["issues"].append(
                    "PyTorch 2.1.x is incompatible with Transformers 4.52.x due to "
                    "torch.get_default_device() not being available"
                )
                compatibility["recommendations"].append(
                    "Downgrade transformers to 4.40.2 or earlier"
                )
            elif transformers_version.startswith("4.40."):
                compatibility["warnings"].append(
                    "PyTorch 2.1.x + Transformers 4.40.x combination may have "
                    "stability issues during model loading"
                )
                compatibility["recommendations"].append(
                    "Consider using transformers 4.36.2 for better stability"
                )
    
    # Check tokenizers compatibility
    if transformers_version and tokenizers_version:
        trans_major = int(transformers_version.split(".")[1])
        tok_minor = int(tokenizers_version.split(".")[1])
        
        if trans_major >= 40 and tok_minor < 15:
            compatibility["warnings"].append(
                f"Tokenizers {tokenizers_version} may be too old for "
                f"Transformers {transformers_version}"
            )
            compatibility["recommendations"].append(
                "Update tokenizers to 0.15.0 or later"
            )
    
    return compatibility


def generate_report() -> str:
    """Generate comprehensive environment report."""
    report_lines = ["# Environment Compatibility Report\n"]
    
    # Python version
    python_info = check_python_version()
    report_lines.append("## Python Environment")
    report_lines.append(f"- Version: {python_info['version']}")
    report_lines.append(f"- Executable: {python_info['executable']}")
    report_lines.append("")
    
    # Critical packages
    report_lines.append("## Package Versions")
    critical_packages = [
        "torch", "transformers", "tokenizers", "accelerate",
        "sentencepiece", "protobuf", "numpy", "scipy"
    ]
    
    for package in critical_packages:
        version = check_package_version(package)
        status = "✓" if version else "✗"
        report_lines.append(f"- {package}: {version or 'Not installed'} {status}")
    report_lines.append("")
    
    # CUDA information
    cuda_info = check_cuda_availability()
    report_lines.append("## CUDA Information")
    report_lines.append(f"- Available: {cuda_info['available']}")
    if cuda_info["available"]:
        report_lines.append(f"- CUDA Version: {cuda_info.get('cuda_version', 'Unknown')}")
        report_lines.append(f"- Device: {cuda_info.get('device_name', 'Unknown')}")
        report_lines.append(f"- Capability: {cuda_info.get('capability', 'Unknown')}")
    report_lines.append("")
    
    # Compatibility analysis
    compatibility = check_compatibility_matrix()
    report_lines.append("## Compatibility Analysis")
    
    if compatibility["issues"]:
        report_lines.append("### ❌ Critical Issues")
        for issue in compatibility["issues"]:
            report_lines.append(f"- {issue}")
        report_lines.append("")
    
    if compatibility["warnings"]:
        report_lines.append("### ⚠️  Warnings")
        for warning in compatibility["warnings"]:
            report_lines.append(f"- {warning}")
        report_lines.append("")
    
    if compatibility["recommendations"]:
        report_lines.append("### 💡 Recommendations")
        for rec in compatibility["recommendations"]:
            report_lines.append(f"- {rec}")
        report_lines.append("")
    
    # System info
    report_lines.append("## System Information")
    try:
        import platform
        report_lines.append(f"- Platform: {platform.system()}")
        report_lines.append(f"- Release: {platform.release()}")
        report_lines.append(f"- Machine: {platform.machine()}")
    except:
        report_lines.append("- Unable to get system information")
    
    # Test imports
    report_lines.append("\n## Import Tests")
    test_imports = [
        ("transformers.AutoModelForSeq2SeqLM", "from transformers import AutoModelForSeq2SeqLM"),
        ("transformers.AutoTokenizer", "from transformers import AutoTokenizer"),
        ("torch.cuda", "import torch.cuda"),
        ("accelerate", "import accelerate"),
    ]
    
    for name, import_stmt in test_imports:
        try:
            exec(import_stmt)
            report_lines.append(f"- {name}: ✓ Success")
        except Exception as e:
            report_lines.append(f"- {name}: ✗ Failed - {type(e).__name__}: {str(e)}")
    
    return "\n".join(report_lines)


def main():
    """Main execution function."""
    print("Checking environment compatibility...")
    print("=" * 60)
    
    report = generate_report()
    print(report)
    
    # Save report
    with open("environment_compatibility_report.md", "w") as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print("Report saved to: environment_compatibility_report.md")
    
    # Check for critical issues
    compatibility = check_compatibility_matrix()
    if compatibility["issues"]:
        print("\n⚠️  CRITICAL ISSUES FOUND! See report for details.")
        sys.exit(1)
    else:
        print("\n✓ No critical compatibility issues found.")


if __name__ == "__main__":
    main()