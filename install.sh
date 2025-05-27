#!/bin/bash

# NLLB Translation System - Installation Script
# This script sets up the server component using Docker

set -e

echo "NLLB Translation System - Installation Script"
echo "============================================="
echo

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi

# Set up environment file
if [ ! -f "server/.env" ]; then
    echo "Creating environment file..."
    cp server/.env.example server/.env
    echo "Please edit server/.env file with your settings"
    echo
fi

# Build and start Docker container
echo "Building and starting Docker container..."
docker-compose up -d

echo
echo "Installation completed successfully!"
echo
echo "Next steps:"
echo "1. Check server status: docker-compose logs -f nllb-server"
echo "2. Install the UserScript in your browser (see userscript/README.md)"
echo "3. For Windows users, install the AutoHotkey script (see ahk/README.md)"
echo
echo "For more information, see the README.md files in each component folder."