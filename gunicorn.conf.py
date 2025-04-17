import os

port = os.environ.get("PORT", "8080")
bind = "[::]:8080"
workers = 8
preload_app = True
timeout = 1200
