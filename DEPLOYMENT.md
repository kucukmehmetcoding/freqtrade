# 🚀 Freqtrade Coolify Deployment Guide

This guide will help you deploy your Freqtrade bot to a production server using Coolify.

## 📋 Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04+ or Debian 11+
- **RAM**: Minimum 2GB, Recommended 4GB+
- **CPU**: 2+ cores recommended
- **Storage**: 20GB+ SSD
- **Network**: Stable internet connection

### Software Requirements
- [Coolify](https://coolify.io/) installed on your server
- Domain name (for SSL certificate)
- Git repository access

## 🔧 Setup Steps

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Coolify
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

# Create directories for persistent storage
sudo mkdir -p /opt/freqtrade/data/{user_data,logs,db}
sudo mkdir -p /opt/freqtrade/backups
sudo chown -R 1000:1000 /opt/freqtrade/
```

### 2. Coolify Configuration

1. **Access Coolify Dashboard**
   - Navigate to `http://your-server-ip:8000`
   - Complete the initial setup

2. **Create New Project**
   - Click "New Project"
   - Name: "freqtrade-production"
   - Choose "Docker Compose" deployment

3. **Connect Repository**
   - Link your Git repository containing these files
   - Select branch: `main` or `master`
   - Set build context to root (`/`)

### 3. Environment Variables Setup

In Coolify, configure these environment variables:

#### 🔒 Critical Security Variables (Mark as "Encrypted")
```
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_api_secret
API_USERNAME=admin
API_PASSWORD=strong_password_here
JWT_SECRET=random_32_char_string
```

#### ⚙️ Configuration Variables
```
DRY_RUN=false
MAX_OPEN_TRADES=2
STAKE_AMOUNT=100
TZ=UTC
HOST_DATA_PATH=/opt/freqtrade/data/user_data
HOST_LOGS_PATH=/opt/freqtrade/data/logs
HOST_DB_PATH=/opt/freqtrade/data/db
```

### 4. Domain & SSL Setup

1. **Add Domain**
   - In Coolify project settings
   - Add your domain (e.g., `freqtrade.yourdomain.com`)
   - Enable "Generate SSL certificate"

2. **DNS Configuration**
   ```
   Type: A
   Name: freqtrade
   Value: your_server_ip
   TTL: 3600
   ```

### 5. Security Configuration

#### Firewall Setup
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # Coolify dashboard
sudo ufw enable
```

#### Binance API Security
1. Log into Binance
2. Go to API Management
3. Restrict API to:
   - ✅ Enable Futures Trading
   - ❌ Disable Spot & Margin Trading
   - ❌ Disable Withdrawals
4. Add server IP to whitelist

### 6. Deployment Process

#### Initial Deployment (Dry Run)
1. **Set DRY_RUN=true** in environment variables
2. Click "Deploy" in Coolify
3. Monitor deployment logs
4. Access web UI at your domain
5. Verify bot functionality

#### Production Deployment
1. **Set DRY_RUN=false** 
2. Redeploy the application
3. Monitor for first trades
4. Set up monitoring and backups

## 📊 Post-Deployment Setup

### 1. Monitoring Setup

```bash
# Make scripts executable
chmod +x /path/to/health-monitor.sh
chmod +x /path/to/backup.sh

# Setup cron jobs
crontab -e

# Add these lines:
# Health check every 5 minutes
*/5 * * * * /path/to/health-monitor.sh

# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

### 2. Telegram Notifications (Optional)

1. Create a Telegram bot via @BotFather
2. Get your chat ID from @userinfobot
3. Add to environment variables:
   ```
   TELEGRAM_ENABLED=true
   TELEGRAM_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### 3. Backup Configuration

For S3 backups, add:
```
S3_BUCKET_NAME=your-backup-bucket
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## 🚨 Troubleshooting

### Common Issues

1. **Container won't start**
   - Check environment variables
   - Verify API keys
   - Check Coolify logs

2. **API connection failed**
   - Verify Binance API keys
   - Check IP whitelist
   - Ensure futures trading enabled

3. **Web UI inaccessible**
   - Check domain DNS settings
   - Verify SSL certificate status
   - Check firewall rules

### Debug Commands

```bash
# View container logs
docker logs freqtrade-production -f

# Access container shell
docker exec -it freqtrade-production bash

# Check API health
curl https://your-domain.com/api/v1/ping

# View system resources
docker stats freqtrade-production
```

## 📋 Maintenance Checklist

### Daily
- [ ] Check bot status via web UI
- [ ] Verify recent trades
- [ ] Monitor system resources

### Weekly
- [ ] Review trading performance
- [ ] Check backup integrity
- [ ] Update strategy if needed

### Monthly
- [ ] Update Freqtrade version
- [ ] Review security settings
- [ ] Analyze trading statistics

## 🔒 Security Best Practices

1. **API Keys**
   - Use dedicated API keys for bot
   - Restrict permissions to futures only
   - Enable IP whitelisting
   - Rotate keys periodically

2. **Server Security**
   - Keep system updated
   - Use SSH key authentication
   - Configure fail2ban
   - Regular security audits

3. **Application Security**
   - Strong web UI passwords
   - Secure JWT secrets
   - HTTPS only access
   - Regular backups

## 📞 Support

For issues:
1. Check Coolify logs
2. Review Freqtrade documentation
3. Check the health monitoring logs
4. Consult the troubleshooting section above

---

🎉 **Congratulations!** Your Freqtrade bot is now running in production on Coolify!
