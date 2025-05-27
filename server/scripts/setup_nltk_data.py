#!/usr/bin/env python3
"""
Setup script to download required NLTK data for offline testing environments.
This ensures tests don't fail due to network issues when downloading NLTK resources.
"""

import os
import sys
import ssl
import nltk
from pathlib import Path

def download_nltk_data():
    """Download required NLTK data packages for semantic chunking tests."""
    
    # Handle SSL certificate issues in some environments
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    # Set NLTK data path for consistent storage
    nltk_data_dir = Path.home() / 'nltk_data'
    nltk_data_dir.mkdir(exist_ok=True)
    nltk.data.path.append(str(nltk_data_dir))
    
    # Required packages for semantic chunking and text processing
    required_packages = [
        'punkt',           # Sentence tokenization
        'stopwords',       # Stop words for multiple languages
        'averaged_perceptron_tagger',  # POS tagging
        'wordnet',         # WordNet lexical database
        'vader_lexicon',   # Sentiment analysis
        'omw-1.4'          # Open Multilingual Wordnet
    ]
    
    print("Downloading required NLTK data packages...")
    
    for package in required_packages:
        try:
            print(f"Downloading {package}...")
            nltk.download(package, download_dir=str(nltk_data_dir), quiet=False)
            print(f"✓ {package} downloaded successfully")
        except Exception as e:
            print(f"✗ Failed to download {package}: {e}")
            # Don't fail completely - some packages might not be critical
            continue
    
    print(f"NLTK data stored in: {nltk_data_dir}")
    print("Setup complete!")

if __name__ == "__main__":
    download_nltk_data()