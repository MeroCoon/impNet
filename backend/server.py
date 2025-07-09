from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta, date
from passlib.context import CryptContext
from jose import JWTError, jwt
import json
from PIL import Image
import io
import base64
import aiofiles
import secrets
import string

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create uploads directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security setup
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(title="impNet API", version="1.0.0")

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class Role(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str

class RoleCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[str] = []

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    username: str
    full_name: str
    role_id: str
    hashed_password: str
    is_active: bool = True
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    profile_data: Dict[str, Any] = {}

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role_id: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    profile_data: Dict[str, Any] = {}

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str  # "passport", "photo", "certificate", etc.
    filename: str
    original_name: str
    file_path: str
    file_size: int
    mime_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    type: str
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    created_at: datetime
    description: Optional[str] = None
    url: str

class Passport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    series: str
    number: str
    issue_date: date
    issue_place: str
    photo_document_id: Optional[str] = None
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: date
    birth_place: str
    gender: str  # "М" or "Ж"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PassportCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: date
    birth_place: str
    gender: str
    issue_place: str

class PassportResponse(BaseModel):
    id: str
    series: str
    number: str
    issue_date: date
    issue_place: str
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: date
    birth_place: str
    gender: str
    created_at: datetime
    updated_at: datetime
    photo_url: Optional[str] = None

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_passport_number():
    """Generate passport series and number"""
    series = ''.join(secrets.choice(string.digits) for _ in range(4))
    number = ''.join(secrets.choice(string.digits) for _ in range(6))
    return series, number

async def save_uploaded_file(file: UploadFile, user_id: str) -> str:
    """Save uploaded file and return file path"""
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
    unique_filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
    
    # Create user directory
    user_dir = UPLOAD_DIR / user_id
    user_dir.mkdir(exist_ok=True)
    
    file_path = user_dir / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    return str(file_path.relative_to(ROOT_DIR))

def is_image_file(filename: str) -> bool:
    """Check if file is an image"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    return any(filename.lower().endswith(ext) for ext in image_extensions)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    return User(**user)

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    role = await db.roles.find_one({"id": current_user.role_id})
    if not role or "admin" not in role.get("permissions", []):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# Initialize default roles
async def init_default_roles():
    # Check if roles exist
    roles_count = await db.roles.count_documents({})
    if roles_count == 0:
        default_roles = [
            {
                "id": str(uuid.uuid4()),
                "name": "super_admin",
                "display_name": "Супер Администратор",
                "description": "Полный доступ к системе",
                "permissions": ["admin", "create_roles", "manage_users", "manage_services"],
                "created_at": datetime.utcnow(),
                "created_by": "system"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "citizen",
                "display_name": "Гражданин",
                "description": "Базовый пользователь системы",
                "permissions": ["user", "view_services", "create_applications"],
                "created_at": datetime.utcnow(),
                "created_by": "system"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "bank_employee",
                "display_name": "Сотрудник ЦБ",
                "description": "Сотрудник Центрального Банка",
                "permissions": ["user", "bank_operations", "view_applications"],
                "created_at": datetime.utcnow(),
                "created_by": "system"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "mfc_employee",
                "display_name": "Сотрудник МФЦ",
                "description": "Сотрудник Многофункционального Центра",
                "permissions": ["user", "mfc_operations", "process_applications"],
                "created_at": datetime.utcnow(),
                "created_by": "system"
            }
        ]
        await db.roles.insert_many(default_roles)
        
        # Create default admin user
        admin_role = await db.roles.find_one({"name": "super_admin"})
        if admin_role:
            admin_user = {
                "id": str(uuid.uuid4()),
                "email": "admin@impnet.ru",
                "username": "admin",
                "full_name": "Администратор Системы",
                "role_id": admin_role["id"],
                "hashed_password": get_password_hash("admin123"),
                "is_active": True,
                "created_at": datetime.utcnow(),
                "profile_data": {}
            }
            await db.users.insert_one(admin_user)

# Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Get default citizen role if no role specified
    if not user_data.role_id:
        citizen_role = await db.roles.find_one({"name": "citizen"})
        if not citizen_role:
            raise HTTPException(status_code=500, detail="Default role not found")
        user_data.role_id = citizen_role["id"]
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        role_id=user_data.role_id,
        hashed_password=get_password_hash(user_data.password)
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**user.dict())
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(**user)
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return UserResponse(**current_user.dict())

@api_router.get("/roles", response_model=List[Role])
async def get_roles(current_user: User = Depends(get_current_active_user)):
    roles = await db.roles.find().to_list(1000)
    return [Role(**role) for role in roles]

@api_router.post("/roles", response_model=Role)
async def create_role(role_data: RoleCreate, current_user: User = Depends(get_admin_user)):
    # Check if role name already exists
    existing_role = await db.roles.find_one({"name": role_data.name})
    if existing_role:
        raise HTTPException(status_code=400, detail="Role name already exists")
    
    role = Role(
        name=role_data.name,
        display_name=role_data.display_name,
        description=role_data.description,
        permissions=role_data.permissions,
        created_by=current_user.id
    )
    
    await db.roles.insert_one(role.dict())
    return role

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [UserResponse(**user) for user in users]

@api_router.get("/")
async def root():
    return {"message": "impNet API v1.0.0"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.post("/reset-database")
async def reset_database():
    """Reset database - only for development"""
    await db.users.drop()
    await db.roles.drop()
    await init_default_roles()
    return {"message": "Database reset successfully"}

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_default_roles()
    logger.info("Default roles initialized")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()