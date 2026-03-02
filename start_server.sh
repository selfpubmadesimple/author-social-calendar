#!/bin/bash
# Custom startup script with extended timeout for image generation
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload --timeout 120 --graceful-timeout 120 main:app
