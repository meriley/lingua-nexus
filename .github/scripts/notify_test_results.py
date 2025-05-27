#!/usr/bin/env python3
"""
Test Results Notification Script
Sends notifications about test results to configured channels.
"""

import json
import os
import sys
import requests
from typing import Dict, Optional


def send_slack_notification(webhook_url: str, message: str, color: str = "good"):
    """Send notification to Slack."""
    payload = {
        "attachments": [
            {
                "color": color,
                "text": message,
                "mrkdwn_in": ["text"]
            }
        ]
    }
    
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()


def generate_test_summary(workflow_result: str, test_results: Dict) -> tuple[str, str]:
    """Generate test summary message and determine color."""
    if workflow_result == "success":
        color = "good"
        message = "✅ E2E Tests Passed"
    elif workflow_result == "failure":
        color = "danger"
        message = "❌ E2E Tests Failed"
    else:
        color = "warning"
        message = "⚠️ E2E Tests Completed with Issues"
    
    details = []
    for test_type, result in test_results.items():
        if result == "success":
            details.append(f"• {test_type}: ✅")
        elif result == "failure":
            details.append(f"• {test_type}: ❌")
        else:
            details.append(f"• {test_type}: ⚠️")
    
    if details:
        message += "\n" + "\n".join(details)
    
    return message, color


def main():
    # Get environment variables
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    workflow_result = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    
    # Parse test results from environment or arguments
    test_results = {
        "Infrastructure": os.environ.get("INFRASTRUCTURE_RESULT", "unknown"),
        "Smoke Tests": os.environ.get("SMOKE_RESULT", "unknown"),
        "Model Tests": os.environ.get("MODEL_RESULT", "unknown"),
        "Performance": os.environ.get("PERFORMANCE_RESULT", "unknown")
    }
    
    # Generate message
    message, color = generate_test_summary(workflow_result, test_results)
    
    # Add repository and commit info
    repo = os.environ.get("GITHUB_REPOSITORY", "unknown")
    commit = os.environ.get("GITHUB_SHA", "unknown")[:8]
    branch = os.environ.get("GITHUB_REF_NAME", "unknown")
    run_url = f"https://github.com/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    
    message += f"\n\nRepo: {repo} (branch: {branch})"
    message += f"\nCommit: {commit}"
    message += f"\n<{run_url}|View Details>"
    
    # Send notification if webhook is configured
    if webhook_url:
        try:
            send_slack_notification(webhook_url, message, color)
            print("Notification sent successfully")
        except Exception as e:
            print(f"Failed to send notification: {e}")
    else:
        print("No webhook URL configured, skipping notification")
        print(f"Message would be: {message}")


if __name__ == "__main__":
    main()
