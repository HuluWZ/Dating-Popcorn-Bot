#!/bin/bash

# Script to save SSH key retrieved from GitHub Secrets
# Usage: ./save-ssh-key.sh

KEY_PATH="$HOME/.ssh/dating-popcorn-bot-key.pem"
KEY_DIR="$HOME/.ssh"

# Create .ssh directory if it doesn't exist
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

echo "🔑 SSH Key Recovery Script"
echo "=========================="
echo ""
echo "This script will help you save your SSH key."
echo "You can retrieve the key from:"
echo "  GitHub → Settings → Secrets and variables → Actions → EC2_SSH_KEY"
echo ""
echo "Key will be saved to: $KEY_PATH"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Check if key already exists
if [ -f "$KEY_PATH" ]; then
    echo ""
    echo "⚠️  Warning: Key file already exists at $KEY_PATH"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 1
    fi
    rm "$KEY_PATH"
fi

echo ""
echo "Paste your SSH private key content below."
echo "The key should start with: -----BEGIN RSA PRIVATE KEY-----"
echo "or: -----BEGIN OPENSSH PRIVATE KEY-----"
echo ""
echo "Paste the entire key (including BEGIN and END lines),"
echo "then press Enter, then Ctrl+D to finish:"
echo ""

# Read the key content
cat > "$KEY_PATH"

# Set proper permissions
chmod 400 "$KEY_PATH"

echo ""
echo "✅ Key saved successfully!"
echo ""
echo "Verifying key format..."
if ssh-keygen -l -f "$KEY_PATH" >/dev/null 2>&1; then
    echo "✅ Key format is valid"
    echo ""
    echo "Key fingerprint:"
    ssh-keygen -l -f "$KEY_PATH"
else
    echo "❌ Warning: Key format validation failed"
    echo "Please verify the key content is correct"
fi

echo ""
echo "📝 Next steps:"
echo "1. Test your connection:"
echo "   ssh -i $KEY_PATH ubuntu@<your-ec2-host>"
echo ""
echo "2. Or add to your SSH config (~/.ssh/config):"
echo "   Host dating-popcorn-ec2"
echo "       HostName <your-ec2-ip>"
echo "       User ubuntu"
echo "       IdentityFile $KEY_PATH"
echo ""

