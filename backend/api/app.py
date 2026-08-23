"""FastAPI backend API — serves ML endpoints for the webapp."""

from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def create_app():
    from fastapi import FastAPI

    from backend.api.chat import router as chat_router
    from backend.api.performance import router as perf_router

    app = FastAPI(title="Master Prediction API", version="1.0")
    app.include_router(chat_router)
    app.include_router(perf_router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.api.app:app", host="0.0.0.0", port=8081, reload=True)
