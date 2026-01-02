# 1. Clone/create project
mkdir axon && cd axon

# 2. Install
pip install pywrangler uv

# 3. Setup database
wrangler d1 create axon-db
# Copy database_id to wrangler.toml

# 4. Initialize schema
wrangler d1 execute axon-db --file=schema.sql

# 5. Deploy
uv run pywrangler deploy

# 6. Visit dashboard
open https://axon.your-subdomain.workers.dev/dashboard
