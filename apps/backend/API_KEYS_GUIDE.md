# API Keys & Credentials Setup Guide

This guide shows you where to get all the API keys and credentials needed for R.E.M.I.

## 🚀 Quick Start (Minimum Required)

For basic local development, you only need:

1. **PostgreSQL** - Local database (no API key needed)
2. **Redis** - Local cache (no API key needed)
3. **Ollama** - Local AI (no API key needed)

Everything else is optional depending on which platforms you want to integrate.

---

## 📧 Email Integrations

### Gmail (OAuth 2.0)

**Where to get:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Add authorized redirect URI: `http://localhost:8000/auth/gmail/callback`
5. Download credentials JSON or copy:
   - Client ID
   - Client Secret

**Required env vars:**
```bash
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback
```

**Documentation:** https://developers.google.com/gmail/api/quickstart/python

---

### Yahoo Mail (IMAP)

**Where to get:**
1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security)
2. Enable "Allow apps that use less secure sign in"
3. Generate an app-specific password:
   - Click "Generate app password"
   - Select "Other App" and name it "REMI"
   - Copy the 16-character password

**Required env vars:**
```bash
YAHOO_EMAIL=your-email@yahoo.com
YAHOO_APP_PASSWORD=your-16-char-password
```

**Documentation:** https://help.yahoo.com/kb/generate-manage-third-party-passwords-sln15241.html

---

## 💬 Chat Platform Integrations

### Slack (Events API)

**Where to get:**
1. Go to [Slack API](https://api.slack.com/apps)
2. Click "Create New App" > "From scratch"
3. Name your app and select workspace
4. Get credentials from "Basic Information":
   - Client ID
   - Client Secret
   - Signing Secret
5. Install app to workspace to get tokens:
   - Go to "OAuth & Permissions"
   - Click "Install to Workspace"
   - Copy Bot User OAuth Token (starts with `xoxb-`)
   - Copy User OAuth Token (starts with `xoxp-`)
6. For Socket Mode (optional):
   - Go to "Socket Mode" and enable it
   - Generate App-Level Token (starts with `xapp-`)

**Required scopes:**
- `channels:history`
- `channels:read`
- `chat:write`
- `users:read`
- `im:history`
- `groups:history`

**Required env vars:**
```bash
SLACK_CLIENT_ID=your-client-id
SLACK_CLIENT_SECRET=your-client-secret
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_USER_TOKEN=xoxp-your-user-token
```

**Documentation:** https://api.slack.com/start/quickstart

---

### Discord (Bot)

**Where to get:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" section:
   - Click "Add Bot"
   - Copy Bot Token (keep this secret!)
4. Get Client ID and Secret from "OAuth2" section
5. Enable required intents:
   - Message Content Intent
   - Server Members Intent
   - Presence Intent

**Required env vars:**
```bash
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CLIENT_ID=your-client-id
DISCORD_CLIENT_SECRET=your-client-secret
```

**Documentation:** https://discord.com/developers/docs/intro

---

### Telegram (Bot API)

**Where to get:**
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Required env vars:**
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Documentation:** https://core.telegram.org/bots/tutorial

---

### Twitter/X (API v2)

**Where to get:**
1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new project and app
3. Go to "Keys and tokens" tab
4. Generate and copy:
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)
   - Access Token
   - Access Token Secret
   - Bearer Token
5. For OAuth 2.0 (optional):
   - Client ID
   - Client Secret

**Required env vars:**
```bash
X_API_KEY=your-api-key
X_API_SECRET=your-api-secret
X_ACCESS_TOKEN=your-access-token
X_ACCESS_TOKEN_SECRET=your-access-token-secret
X_BEARER_TOKEN=your-bearer-token
```

**Documentation:** https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api

---

## 🤖 AI Services

### Ollama (Local - Recommended)

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2:3b
ollama pull nomic-embed-text:latest

# Verify it's running
curl http://localhost:11434/api/tags
```

**Required env vars:**
```bash
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_CHAT_MODEL=llama3.2:3b
DEFAULT_EMBEDDING_MODEL=nomic-embed-text:latest
```

**No API key needed!** Runs completely locally.

**Documentation:** https://ollama.com/

---

### OpenAI (Optional Cloud Fallback)

**Where to get:**
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to [API Keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)

**Required env vars:**
```bash
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

**Documentation:** https://platform.openai.com/docs/quickstart

---

### Anthropic Claude (Optional Cloud Fallback)

**Where to get:**
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Go to [API Keys](https://console.anthropic.com/settings/keys)
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)

**Required env vars:**
```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

**Documentation:** https://docs.anthropic.com/claude/docs

---

### Hugging Face (Optional)

**Where to get:**
1. Go to [Hugging Face](https://huggingface.co/)
2. Sign up or log in
3. Go to [Settings > Access Tokens](https://huggingface.co/settings/tokens)
4. Click "New token"
5. Select "Read" access
6. Copy the token (starts with `hf_`)

**Required env vars:**
```bash
HF_API_TOKEN=hf_your_token
HF_USE_LOCAL=true  # Set to false to use API
```

**Documentation:** https://huggingface.co/docs/hub/security-tokens

---

## 🔐 Security & Encryption

### Secret Keys (Generate Your Own)

**Generate secure keys:**
```bash
# Generate SECRET_KEY (for general app security)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY (for JWT tokens)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY (32-byte base64 encoded)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate WEBHOOK_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

**Required env vars:**
```bash
SECRET_KEY=your-generated-secret-key
JWT_SECRET_KEY=your-generated-jwt-secret
ENCRYPTION_KEY=your-generated-encryption-key
WEBHOOK_SECRET=your-generated-webhook-secret
```

---

## ☁️ Cloud Storage (Optional)

### AWS S3

**Where to get:**
1. Go to [AWS Console](https://console.aws.amazon.com/)
2. Create IAM user with S3 access:
   - Go to IAM > Users > Create user
   - Attach policy: `AmazonS3FullAccess` (or custom policy)
3. Create access key:
   - Go to user > Security credentials
   - Click "Create access key"
   - Copy Access Key ID and Secret Access Key
4. Create S3 bucket:
   - Go to S3 > Create bucket
   - Note the bucket name and region

**Required env vars:**
```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
```

**Documentation:** https://docs.aws.amazon.com/AmazonS3/latest/userguide/

---

## 🗄️ Database Setup

### PostgreSQL (Required)

**Local setup:**
```bash
# macOS (Homebrew)
brew install postgresql@14
brew services start postgresql@14
createdb mesh_development

# Ubuntu/Debian
sudo apt install postgresql-14
sudo systemctl start postgresql
sudo -u postgres createdb mesh_development

# Docker
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=mesh_development \
  -p 5432:5432 \
  postgres:14
```

**Required env vars:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/mesh_development
```

---

### Redis (Required)

**Local setup:**
```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# Docker
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:6
```

**Required env vars:**
```bash
REDIS_URL=redis://localhost:6379
```

---

## 📝 Setup Checklist

### Minimum Setup (Local Development)
- [ ] PostgreSQL installed and running
- [ ] Redis installed and running
- [ ] Ollama installed with models downloaded
- [ ] `.env` file created from `.env.example`
- [ ] Generated security keys

### Optional Integrations
- [ ] Gmail OAuth credentials (if using Gmail)
- [ ] Slack app credentials (if using Slack)
- [ ] Discord bot token (if using Discord)
- [ ] Telegram bot token (if using Telegram)
- [ ] Twitter API keys (if using Twitter/X)
- [ ] OpenAI API key (if using cloud AI)
- [ ] AWS credentials (if using S3 storage)

---

## 🚀 Quick Start Commands

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your credentials
nano .env  # or use your preferred editor

# 3. Generate security keys
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env

# 4. Install dependencies
pip install -r requirements.txt

# 5. Download spaCy model
python -m spacy download en_core_web_sm

# 6. Run database migrations
alembic upgrade head

# 7. Start the application
python main.py
```

---

## 🔍 Testing Your Setup

```bash
# Test database connection
python -c "from db.session import get_db; print('Database: OK')"

# Test Redis connection
python -c "from db.redis_client import get_redis_client; print('Redis: OK')"

# Test Ollama
curl http://localhost:11434/api/tags

# Test API
curl http://localhost:8000/health
```

---

## 🆘 Troubleshooting

### "Connection refused" errors
- Make sure PostgreSQL and Redis are running
- Check that ports 5432 (PostgreSQL) and 6379 (Redis) are not blocked

### "Model not found" errors (Ollama)
- Run `ollama pull llama3.2:3b`
- Run `ollama pull nomic-embed-text:latest`

### "Invalid credentials" errors
- Double-check your API keys in `.env`
- Make sure there are no extra spaces or quotes
- Verify keys haven't expired

### spaCy model errors
- Run `python -m spacy download en_core_web_sm`
- Or use a different model: `python -m spacy download en_core_web_md`

---

## 📚 Additional Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Slack API Documentation](https://api.slack.com/)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- [Ollama Documentation](https://ollama.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/docs/)

---

## 🔒 Security Best Practices

1. **Never commit `.env` file** - It's in `.gitignore` for a reason
2. **Rotate keys regularly** - Especially for production
3. **Use different keys** - Don't reuse keys across environments
4. **Limit API permissions** - Only grant necessary scopes
5. **Monitor usage** - Watch for unusual API activity
6. **Use environment-specific keys** - Different keys for dev/staging/prod
7. **Store production keys securely** - Use secret management services (AWS Secrets Manager, HashiCorp Vault, etc.)

---

Need help with a specific integration? Check the platform's documentation or open an issue!
