import os
import sys

# Add the mcp_server path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env variables from parent directory `.env`
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            # Rewrite container names to localhost for host execution
            if val.startswith('http://prowlarr:'):
                val = val.replace('http://prowlarr:', 'http://localhost:')
            elif val.startswith('http://qbittorrent:'):
                val = val.replace('http://qbittorrent:', 'http://localhost:')
            os.environ[key] = val

import server

print("--- INDEXERS IN PROWLARR ---")
print(server.listar_indexers())
print("\n--- ACTIVE DOWNLOADS IN QBITTORRENT ---")
print(server.listar_downloads())
