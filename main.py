from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager  

from routers.auth import router as auth_router, init_user_table

# Lifespan function (startup + shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code ekhane
    init_user_table()
    yield  # after yield shutdown code (now empty)

app = FastAPI(title="Research Bot API", lifespan=lifespan)  

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