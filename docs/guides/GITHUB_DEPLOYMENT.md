# GitHub Deployment — research_papers

Full-stack app with a non-standard layout:
- Python backend packaged via **`pyproject.toml`** (entry `src/docserver/main.py`,
  plus a sub-app under `sims/apip_sim/backend/`)
- TypeScript/Vite frontend in **`web/`** (build: `tsc -b && vite build` → `web/dist/`)
- A `web/Dockerfile` and a `docker/` directory already exist.

This repo also has `DEPLOY-AWS.md`. This file covers the **GitHub-native** path.

---

## 1. Prerequisites
- Own GitHub repo: `gh repo create research_papers --source=. --private --push`
- **Settings → Pages → Source: GitHub Actions**

## 2. Frontend (`web/`) → GitHub Pages
Set `base: '/research_papers/'` in `web/vite.config.ts`, and configure the API base URL
for production (e.g. `web/.env.production` → `VITE_API_BASE=...`).

`.github/workflows/deploy-frontend.yml`:
```yaml
name: Deploy web to Pages
on: { push: { branches: [main] } }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  build:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: web } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm', cache-dependency-path: web/package-lock.json }
      - run: npm ci
      - run: npm run build        # tsc -b && vite build
      - uses: actions/upload-pages-artifact@v3
        with: { path: web/dist }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: '${{ steps.deployment.outputs.page_url }}' }
    steps: [ { id: deployment, uses: actions/deploy-pages@v4 } ]
```

## 3. Backend → GHCR

The backend is a Python package. Build a container from the repo root (so `pyproject.toml`
and `src/` are in context). Add `Dockerfile` at the root:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .
EXPOSE 8000
CMD ["uvicorn", "docserver.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
> Adjust the module path if your ASGI app is exposed elsewhere (check `src/docserver/main.py`).

`.github/workflows/backend-image.yml`:
```yaml
name: Build backend image
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write }
jobs:
  image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: '${{ github.actor }}', password: '${{ secrets.GITHUB_TOKEN }}' }
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/research_papers-api:latest
```

## 4. Notes
- LaTeX/PDF generation may need system packages (e.g. `texlive`) — add them to the
  backend Dockerfile if the API renders documents server-side.
- Keep model/API keys on the backend host, never in the Pages bundle.
