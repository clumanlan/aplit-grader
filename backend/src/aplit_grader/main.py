from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from aplit_grader.api.routes import router

app = FastAPI(title="AP Lit Essay Grader")

# Local dev only, pinned to match frontend/vite.config.ts's fixed dev port
# (not Vite's 5173 default — that port is taken by another project on this
# machine). The production shape (frontend/dist served as static assets from
# this same FastAPI app) removes the need for CORS entirely.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180"],
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router)

# API routes above take priority (registered first); this mount only serves
# frontend/dist, built and copied in by the Dockerfile. Absent in local dev
# unless `npm run build` was run, so it's guarded rather than assumed present.
_frontend_dist = Path(__file__).resolve().parent / "static"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
