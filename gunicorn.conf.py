# Gunicorn configuration file
# This sets a 10-minute timeout to handle long-running AI image generation

bind = "0.0.0.0:5000"
timeout = 600  # 10 minutes (600 seconds) - enough time for OpenAI to generate 30 images
workers = 1
reload = True
reuse_port = True
