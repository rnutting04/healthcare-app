#!/bin/bash

echo "Waiting for other services to be ready..."
sleep 10

echo "Starting Admin Service..."
exec "$@"