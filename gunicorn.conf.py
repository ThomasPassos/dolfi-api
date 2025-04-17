import os

port = os.environ.get("PORT", "8080")
bind = [f"0.0.0.0:{port}", f"[::]:{port}"]
workers = 8
preload_app = True
