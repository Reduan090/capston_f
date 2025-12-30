from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from utils.jwt_handler import create_access_token, get_current_user

# Dummy in-memory "database" for demonstration
fake_users_db = {}

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pydantic models
class UserSignup(BaseModel):
    username: str
    password: str  # In real apps, hash this!

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Initialize user table (for demo, could be DB setup)
def init_user_table():
    fake_users_db.clear()

# Signup route
@router.post("/signup", response_model=Token)
async def signup(user: UserSignup):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    fake_users_db[user.username] = {"password": user.password, "user_id": len(fake_users_db)+1}
    access_token = create_access_token(data={"sub": user.username, "user_id": fake_users_db[user.username]["user_id"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Login route
@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    db_user = fake_users_db.get(user.username)
    if not db_user or db_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token(data={"sub": user.username, "user_id": db_user["user_id"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Protected route
@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
