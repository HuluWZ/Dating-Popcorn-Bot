#!/bin/bash

# EC2 Setup Script for Dating Popcorn Bot
# Run this script on your EC2 instance to prepare it for deployment

echo "🚀 Setting up EC2 instance for Dating Popcorn Bot..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose already installed"
fi

# Install Git
echo "📚 Installing Git..."
sudo apt install git -y

# Create project directory
echo "📁 Creating project directory..."
mkdir -p /home/ubuntu/dating-popcorn-bot
cd /home/ubuntu/dating-popcorn-bot

# Clone repository (replace with your actual repository URL)
echo "📥 Cloning repository..."
git clone https://github.com/HuluWZ/dating-popcorn-bot.git . || echo "Repository already exists"

# Create environment file
echo "⚙️ Creating environment file..."
cat > .env << EOF
BOT_TOKEN=your_bot_token_here
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
EOF

echo "📝 Please edit .env file and add your BOT_TOKEN:"
echo "   nano .env"

# Set up firewall (optional)
echo "🔥 Setting up firewall..."
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP (if needed)
sudo ufw allow 443   # HTTPS (if needed)
sudo ufw --force enable

# Create systemd service for auto-start (optional)
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/dating-popcorn-bot.service > /dev/null << EOF
[Unit]
Description=Dating Popcorn Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/dating-popcorn-bot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable dating-popcorn-bot.service

echo "✅ EC2 setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file: nano .env"
echo "2. Add your BOT_TOKEN to the .env file"
echo "3. Start the bot: docker compose up -d"
echo "4. Check logs: docker compose logs -f"
echo ""
echo "🔧 To start the bot manually:"
echo "   cd /home/ubuntu/dating-popcorn-bot"
echo "   docker compose up -d"
echo ""
echo "📊 To check bot status:"
echo "   docker ps"
echo "   docker compose logs"
echo ""
echo "🔄 To enable auto-start on boot:"
echo "   sudo systemctl start dating-popcorn-bot"
echo ""
echo "🎉 Setup complete! Your EC2 instance is ready for deployment."
