# Frontend image: React/Vite static site served on :8080.
# Build from web/:  docker build --build-arg VITE_API_BASE=https://backend.url web
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
# `npm install` (not `npm ci`): npm omits Vite 8 / rolldown's platform+libc-gated
# native binding (@rolldown/binding-linux-x64-gnu) from a `ci` install in slim
# images, which breaks `vite build`. install re-resolves it for this platform.
RUN npm install --no-audit --no-fund

# Vite inlines these at build time — they cannot be changed at runtime.
ARG VITE_API_BASE
ARG VITE_DOCSERVER_TOKEN
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_DOCSERVER_TOKEN=$VITE_DOCSERVER_TOKEN

COPY . .
RUN npm run build

FROM node:20-slim
RUN npm install -g serve
WORKDIR /app
COPY --from=builder /app/dist /app/dist
EXPOSE 8080
# tcp://0.0.0.0:PORT form — the bare "-l 8080" is ignored by newer serve.
CMD ["serve", "-s", "dist", "-l", "tcp://0.0.0.0:8080"]
