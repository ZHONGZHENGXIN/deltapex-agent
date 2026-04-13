# Build AI Template Deploy

## Get Started

```bash
# Clone repository
git clone https://github.com/open-v2ai/build-ai-template.git
cd build-ai-template/deploy

# Copy .env.example to .env
cp .env.example .env

# Edit .env file
vim .env

# Build images
make build-all

# Run services
make start

# View logs
docker compose logs -f
```
