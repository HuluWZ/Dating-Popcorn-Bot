# 🚀 EC2 Deployment Guide for Dating Popcorn Bot

This guide will help you deploy the Dating Popcorn Bot to an EC2 instance with automatic CI/CD.

## 📋 Prerequisites

- AWS EC2 instance (t3.micro or t3.small recommended)
- GitHub repository with your bot code
- SSH access to your EC2 instance

## 🛠️ Step 1: Launch EC2 Instance

### Recommended Instance Settings:
- **Instance Type**: t3.micro (free tier) or t3.small
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 8GB (minimum)
- **Security Group**: Allow SSH (port 22) from your IP

### Create Security Group:
```
Inbound Rules:
- SSH (22) - Your IP
- HTTP (80) - 0.0.0.0/0 (if needed)
- HTTPS (443) - 0.0.0.0/0 (if needed)
```

## 🔧 Step 2: Setup EC2 Instance

### Connect to your EC2 instance:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### Run the setup script:
```bash
# Download and run the setup script
curl -O https://raw.githubusercontent.com/YOUR_USERNAME/dating-popcorn-bot/main/ec2-setup.sh
chmod +x ec2-setup.sh
./ec2-setup.sh
```

### Manual setup (alternative):
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt install git -y

# Create project directory
mkdir -p /home/ubuntu/dating-popcorn-bot
cd /home/ubuntu/dating-popcorn-bot
```

## 🔑 Step 3: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

### Required Secrets:
- `EC2_HOST`: Your EC2 public IP address (e.g., `54.123.45.67`)
- `EC2_USER`: SSH username (usually `ubuntu`)
- `EC2_SSH_KEY`: Your private SSH key content
- `BOT_TOKEN`: Your Telegram bot token

### How to get EC2_SSH_KEY:
```bash
# Copy your private key content
cat your-key.pem
# Copy the entire output including -----BEGIN and -----END lines
```

## 🚀 Step 4: Deploy

### Automatic Deployment (CI/CD):
1. Push your code to the `main` branch
2. GitHub Actions will automatically deploy to EC2
3. Check the Actions tab to see deployment progress

### Manual Deployment:
```bash
# On your EC2 instance
cd /home/ubuntu/dating-popcorn-bot
git clone https://github.com/YOUR_USERNAME/dating-popcorn-bot.git .
echo "BOT_TOKEN=your_bot_token_here" > .env
docker compose up -d
```

## 📊 Step 5: Verify Deployment

### Check if bot is running:
```bash
# On EC2 instance
docker ps
docker compose logs -f
```

### Expected output:
```
CONTAINER ID   IMAGE                    COMMAND             CREATED         STATUS         PORTS     NAMES
abc123def456   dating-popcorn-bot       "python main.py"    2 minutes ago   Up 2 minutes   8000/tcp  dating-popcorn-bot
```

## 🔧 Management Commands

### Start/Stop Bot:
```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart
```

### View Logs:
```bash
# All logs
docker compose logs

# Follow logs
docker compose logs -f

# Last 50 lines
docker compose logs --tail=50
```

### Update Bot:
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 💰 Cost Estimation

### EC2 Costs (eu-north-1):
- **t3.micro**: ~$8.50/month (free tier eligible)
- **t3.small**: ~$17/month
- **Storage (8GB)**: ~$1/month
- **Data transfer**: Minimal for bot usage

**Total: ~$9-18/month**

## 🔒 Security Best Practices

1. **Use IAM roles** instead of access keys when possible
2. **Restrict SSH access** to your IP only
3. **Regular updates**: `sudo apt update && sudo apt upgrade`
4. **Monitor logs** for any suspicious activity
5. **Backup your bot token** securely

## 🆘 Troubleshooting

### Bot not starting:
```bash
# Check logs
docker compose logs

# Check if port is in use
sudo netstat -tulpn | grep :8000

# Restart Docker
sudo systemctl restart docker
```

### Permission issues:
```bash
# Fix Docker permissions
sudo usermod -aG docker ubuntu
# Log out and back in
```

### Out of disk space:
```bash
# Clean up Docker
docker system prune -a
docker volume prune
```

## 📞 Support

If you encounter issues:
1. Check the GitHub Actions logs
2. Check EC2 instance logs: `docker compose logs`
3. Verify all secrets are set correctly
4. Ensure EC2 instance has internet access

## 🎉 Success!

Once deployed, your bot will:
- ✅ Start automatically on EC2 boot
- ✅ Deploy automatically when you push to main
- ✅ Restart automatically if it crashes
- ✅ Scale easily if needed

Your Dating Popcorn Bot is now running on AWS EC2 with full CI/CD! 🚀
