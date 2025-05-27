#!/usr/bin/env python3
"""
Baseline Management Script
Updates performance baselines from successful test runs.
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def update_baseline(report_file: str, baseline_dir: str, model_name: str):
    """Update baseline from a performance report."""
    report_path = Path(report_file)
    baseline_path = Path(baseline_dir) / model_name
    
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_file}")
    
    # Load report
    with open(report_path) as f:
        report_data = json.load(f)
    
    # Create baseline entry
    baseline_data = {
        "model_name": model_name,
        "timestamp": datetime.now().isoformat(),
        "source_report": str(report_path),
        "data": report_data
    }
    
    # Ensure baseline directory exists
    baseline_path.mkdir(parents=True, exist_ok=True)
    
    # Determine baseline filename
    report_type = "unknown"
    if "baseline" in report_path.name or "loading" in report_path.name:
        report_type = "model_loading"
    elif "inference" in report_path.name:
        report_type = "inference"
    elif "memory" in report_path.name:
        report_type = "memory"
    elif "batch" in report_path.name:
        report_type = "batch"
    
    baseline_file = baseline_path / f"{report_type}_baseline.json"
    
    # Save baseline
    with open(baseline_file, 'w') as f:
        json.dump(baseline_data, f, indent=2)
    
    print(f"Updated baseline: {baseline_file}")


def main():
    parser = argparse.ArgumentParser(description="Update performance baselines")
    parser.add_argument("reports", nargs="+", help="Performance report files")
    parser.add_argument("--baseline-dir", default="performance_baselines", 
                       help="Baseline directory")
    parser.add_argument("--model", required=True, help="Model name")
    
    args = parser.parse_args()
    
    for report_file in args.reports:
        try:
            update_baseline(report_file, args.baseline_dir, args.model)
        except Exception as e:
            print(f"Error updating baseline from {report_file}: {e}")


if __name__ == "__main__":
    main()
