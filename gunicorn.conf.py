import os

workers     = 1          # single worker — keeps APScheduler from running multiple times
threads     = 4
timeout     = 120        # SSE streams need longer timeout
bind        = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
accesslog   = "-"
errorlog    = "-"
loglevel    = "info"
preload_app = False
