# Gunicorn configuration file
# Increase worker timeout to handle long-running image generation requests

# Worker timeout in seconds (10 minutes for bulk image generation)
timeout = 600

# Bind to port 5000
bind = "0.0.0.0:5000"

# Enable auto-reload for development
reload = True

# Reuse port to prevent "address already in use" errors  
reuse_port = True
