# ---- Stage 1: build -----------------------------------------------------
FROM hugomods/hugo:exts AS build
WORKDIR /src
COPY . .
RUN hugo --minify --gc

# ---- Stage 2: serve -------------------------------------------------------
FROM caddy:2-alpine AS serve

# Dedicated non-root user — the server process never runs as root.
RUN addgroup -S site && adduser -S site -G site

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/public /srv/www
RUN chown -R site:site /srv/www /etc/caddy

USER site
EXPOSE 8080
