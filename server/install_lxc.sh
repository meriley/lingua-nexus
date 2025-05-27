#!/bin/bash

# NLLB Translation Server - LXC Installation Script
# This script installs the NLLB Translation Server on a Proxmox LXC container

set -e

# Ensure script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root" >&2
    exit 1
fi

echo "Installing NLLB Translation Server..."

# Update system and install dependencies
apt update
apt install -y python3-pip python3-dev python3-venv git

# Create service user
useradd -r -s /bin/false nllb-service || echo "User nllb-service already exists"

# Create application directory
mkdir -p /opt/tg-text-translate
cd /opt/tg-text-translate

# Clone repository (if git URL is provided, otherwise copy files manually)
# git clone <your-repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt

# Set permissions
chown -R nllb-service:nllb-service /opt/tg-text-translate

# Configure environment
cp server/.env.example server/.env
echo "Please edit /opt/tg-text-translate/server/.env with your configuration"

# Install systemd service
cp server/systemd/nllb-translator.service /etc/systemd/system/
systemctl daemon-reload

echo "Installation complete!"
echo "Next steps:"
echo "1. Edit /opt/tg-text-translate/server/.env"
echo "2. Start the service: systemctl start nllb-translator"
echo "3. Enable service at boot: systemctl enable nllb-translator"
echo "4. Check service status: systemctl status nllb-translator"