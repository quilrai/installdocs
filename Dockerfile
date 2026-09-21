# syntax=docker/dockerfile:1.7
# SOP-only image: the site now serves just the static SOP under /sop/ and
# redirects the root there. The Docusaurus source stays in the repo but is no
# longer built or served.
FROM nginx:1.27-alpine

COPY static/sop /usr/share/nginx/html/sop

# Compact nginx config: root redirects to /sop/, gzip on, cache static assets
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Behind the Caddy TLS proxy nginx only sees http — emit relative
    # Location headers so redirects stay on the client's original scheme
    absolute_redirect off;

    gzip on;
    gzip_types text/plain text/css text/javascript application/javascript application/json image/svg+xml;
    gzip_min_length 1024;

    # Everything lives under /sop/ now — send the root there
    location = / {
        return 302 /sop/;
    }

    location /sop/ {
        try_files $uri $uri/ =404;
    }

    # Legacy Docusaurus paths no longer exist — send them to the SOP landing page
    location / {
        return 302 /sop/;
    }

    location ~* \.(?:css|js|woff2?|svg|png|jpg|jpeg|gif|ico)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}
EOF

EXPOSE 80
