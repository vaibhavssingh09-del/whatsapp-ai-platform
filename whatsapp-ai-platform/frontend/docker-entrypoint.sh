#!/bin/sh
# Substitutes the BACKEND_ORIGIN environment variable into nginx.conf at
# container startup (not at build time), so the same built image works
# against different backend URLs in different environments without a
# rebuild — set BACKEND_ORIGIN as a plain env var on the Render service
# (or leave the docker-compose default) rather than baking it into the image.
set -e

: "${BACKEND_ORIGIN:=http://backend:8000}"

sed -i "s#BACKEND_ORIGIN#${BACKEND_ORIGIN}#g" /etc/nginx/conf.d/default.conf

exec "$@"
