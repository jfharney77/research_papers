# Backend image: FastAPI doc server + LaTeX build toolchain.
# Build from the REPO ROOT (the src/ layout needs latex/, script/, etc.):
#   docker build -f docker/backend.Dockerfile -t research-papers-backend .
FROM python:3.12-slim

# TeX Live for the four conference templates (matches script/latex/*/build.sh),
# plus curl/unzip for NeurIPS/AAAI style-file fetching. Debian base avoids the
# Alpine musl pyexpat bug.
RUN apt-get update && apt-get install -y --no-install-recommends \
        texlive-latex-base \
        texlive-latex-recommended \
        texlive-publishers \
        texlive-latex-extra \
        texlive-fonts-recommended \
        texlive-science \
        texlive-bibtex-extra \
        curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies only (the project uses a src layout with no build backend).
# `--extra llm` pulls in the anthropic SDK so the Claude Critic provider works.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra llm

# Application code (web/, research/, tests/ are excluded via .dockerignore).
COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    LATEX_SANDBOX=local \
    DOCSERVER_HOST=0.0.0.0 \
    DOCSERVER_PORT=8080

# Supplied at runtime via the ECS service environment:
#   DOCSERVER_API_KEY, DOCSERVER_CORS_ORIGINS  (auth + CORS)
#   CRITIC_PROVIDER=claude, ANTHROPIC_API_KEY  (enable the Claude Critic provider)
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "docserver.main:app", "--host", "0.0.0.0", "--port", "8080"]
