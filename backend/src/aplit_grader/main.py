from fastapi import FastAPI

from aplit_grader.api.routes import router

app = FastAPI(title="AP Lit Essay Grader")
app.include_router(router)
