# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Sub-path mount point (e.g. /emr/). Set via docker-compose build args or --build-arg.
# Defaults to / so local dev and plain docker run work without any extra config.
ARG BASE_PATH=/
ENV VITE_BASE_PATH=${BASE_PATH}

# Install deps first (layer-cached unless package files change)
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# Drop to non-root for nginx worker processes
# (master must stay root to bind port 80; workers drop to nginx user by default)

# Re-declare so the value is available in this stage
ARG BASE_PATH=/

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Process the nginx config template at build time — BASE_PATH is known here,
# so no runtime envsubst needed and no risk of substituting nginx's own $variables.
COPY nginx.conf.template /tmp/nginx.conf.template
RUN APP_BASE_PATH=${BASE_PATH} envsubst '${APP_BASE_PATH}' \
        < /tmp/nginx.conf.template \
        > /etc/nginx/conf.d/app.conf \
    && rm /tmp/nginx.conf.template

# Copy built assets into the sub-path directory matching BASE_PATH.
# e.g. BASE_PATH=/emr/ → files land at html/emr/, so /emr/assets/... resolves correctly.
COPY --from=builder /app/dist /usr/share/nginx/html${BASE_PATH}

# Ensure nginx can write its temp files
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1${BASE_PATH}index.html || exit 1

CMD ["nginx", "-g", "daemon off;"]
