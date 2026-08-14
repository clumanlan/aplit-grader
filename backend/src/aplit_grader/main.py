from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aplit_grader.api.routes import router

app = FastAPI(title="AP Lit Essay Grader")

# Local dev only, pinned to match frontend/vite.config.ts's fixed dev port
# (not Vite's 5173 default — that port is taken by another project on this
# machine). The production shape (frontend/dist served as static assets from
# this same FastAPI app) removes the need for CORS entirely and can land later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)
