Generate an executable startup script for the sims/apip_sim FastAPI backend (research artifact).

Write the file `run_apip.sh` in research/ with this exact content:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "Installing dependencies..."
uv sync

echo "Starting APIP simulation server..."
uv run uvicorn research.apip_sim.backend.main:app --reload --host 0.0.0.0 --port 8100
```

After writing the file, make it executable with: `chmod +x run_apip.sh`

Then confirm to the user that `run_apip.sh` was created and is ready to run with `./run_apip.sh`. The server will be available at http://localhost:8100 and the WebSocket stream at ws://localhost:8100/ws/metrics.
