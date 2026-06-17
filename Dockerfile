# syntax=docker/dockerfile:1.7
# ---- Build stage: render the Docusaurus site to static HTML ----
FROM node:20-alpine AS build

WORKDIR /app

# Install deps separately to leverage layer caching
COPY package.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --no-audit --no-fund --omit=dev=false

# Copy source and build
COPY docusaurus.config.js sidebars.js ./
COPY src/ ./src/
COPY static/ ./static/
COPY docs/ ./docs/

RUN npx docusaurus build

# ---- Runtime stage: serve the static bundle with nginx ----
FROM nginx:1.27-alpine

COPY --from=build /app/build /usr/share/nginx/html

# Compact nginx config: gzip on, cache static assets, fall back to /index.html
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/plain text/css text/javascript application/javascript application/json image/svg+xml;
    gzip_min_length 1024;

    location / {
        try_files $uri $uri/ $uri.html /index.html;
    }

    # Long cache for fingerprinted static assets
    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable, max-age=2592000";
    }
    location ~* \.(?:css|js|woff2?|svg|png|jpg|jpeg|gif|ico)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}
EOF

EXPOSE 80
