#!/bin/sh
set -e

# Replace $PORT with actual PORT environment variable
# Use sed instead of envsubst to avoid issues with nginx variables
sed "s/\${PORT:-80}/${PORT:-80}/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Execute the CMD
exec "$@"