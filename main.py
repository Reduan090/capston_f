from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager  
from routers import upload
from routers import query

from routers.auth import router as auth_router, init_user_table
from db.schema import init_chat_history_table
from routers import literature_review
from routers import topic_finder
from routers import ai_writter
from routers import plagiarism



# Lifespan function (startup + shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code ekhane
    init_user_table()
    init_chat_history_table()
    yield  # after yield shutdown code (now empty)

app = FastAPI(title="Research Bot API", lifespan=lifespan)  
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(literature_review.router)
app.include_router(topic_finder.router)
app.include_router(ai_writter.router)
app.include_router(plagiarism.router)

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "Research Bot FastAPI backend is running! 🚀"}