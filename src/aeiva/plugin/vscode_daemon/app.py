from fastapi import FastAPI
from .router import router

app = FastAPI(title="Aeiva VSCode Daemon")
app.include_router(router)

# Run with:
# uvicorn aeiva.plugin.vscode_daemon.app:app --port 8787 --reload