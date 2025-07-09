from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import uuid
import bcrypt
import jwt
import json
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="ImpNet - Децентрализованный интернет")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
SECRET_KEY = "impnet_secret_key_2025"
ALGORITHM = "HS256"

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if websocket in self.user_connections[user_id]:
            self.user_connections[user_id].remove(websocket)

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str
    full_name: str
    role: str = "user"  # user, admin, central_bank
    balance: float = 0.0
    salary: float = 0.0  # Зарплата назначаемая центробанком
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    balance: float
    salary: float
    created_at: datetime
    is_active: bool

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_user_id: str
    to_user_id: str
    amount: float
    currency: str = "Ǐ"
    transaction_type: str  # transfer, salary, system
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "completed"

class TransactionCreate(BaseModel):
    to_user_id: str
    amount: float
    description: str

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    username: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = "text"  # text, system, file

class ChatMessageCreate(BaseModel):
    message: str
    message_type: str = "text"

class FileShare(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    file_data: str  # base64 encoded
    file_type: str
    file_size: int
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = True

class FileShareCreate(BaseModel):
    filename: str
    file_data: str
    file_type: str
    file_size: int
    description: str = ""
    is_public: bool = True

class SearchQuery(BaseModel):
    query: str
    search_type: str = "all"  # all, messages, files, users

class Email(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_user_id: str
    to_user_id: str
    subject: str
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False
    is_deleted: bool = False

class EmailCreate(BaseModel):
    to_user_id: str
    subject: str
    body: str

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Auth endpoints
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        balance=100.0  # Стартовый баланс
    )
    
    await db.users.insert_one(user.dict())
    return UserResponse(**user.dict())

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"username": user_data.username})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return {"access_token": access_token, "token_type": "bearer", "user": UserResponse(**user)}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(**current_user.dict())

# Banking system endpoints
@api_router.post("/banking/transfer")
async def transfer_money(transaction_data: TransactionCreate, current_user: User = Depends(get_current_user)):
    # Check if sender has enough balance
    if current_user.balance < transaction_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Check if recipient exists
    recipient = await db.users.find_one({"id": transaction_data.to_user_id})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Create transaction
    transaction = Transaction(
        from_user_id=current_user.id,
        to_user_id=transaction_data.to_user_id,
        amount=transaction_data.amount,
        transaction_type="transfer",
        description=transaction_data.description
    )
    
    # Update balances
    await db.users.update_one(
        {"id": current_user.id},
        {"$inc": {"balance": -transaction_data.amount}}
    )
    await db.users.update_one(
        {"id": transaction_data.to_user_id},
        {"$inc": {"balance": transaction_data.amount}}
    )
    
    # Save transaction
    await db.transactions.insert_one(transaction.dict())
    
    return {"message": "Transfer successful", "transaction": transaction}

@api_router.get("/banking/balance")
async def get_balance(current_user: User = Depends(get_current_user)):
    user = await db.users.find_one({"id": current_user.id})
    return {"balance": user["balance"], "currency": "Ǐ"}

@api_router.get("/banking/transactions")
async def get_transactions(current_user: User = Depends(get_current_user)):
    transactions = await db.transactions.find({
        "$or": [{"from_user_id": current_user.id}, {"to_user_id": current_user.id}]
    }).sort("created_at", -1).to_list(100)
    return transactions

@api_router.get("/banking/users")
async def get_users_for_transfer(current_user: User = Depends(get_current_user)):
    users = await db.users.find({"id": {"$ne": current_user.id}}).to_list(100)
    return [{"id": user["id"], "username": user["username"], "full_name": user["full_name"]} for user in users]

# Chat endpoints
@api_router.post("/chat/message")
async def send_message(message_data: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    message = ChatMessage(
        user_id=current_user.id,
        username=current_user.username,
        message=message_data.message,
        message_type=message_data.message_type
    )
    
    await db.chat_messages.insert_one(message.dict())
    
    # Broadcast to all connected users
    await manager.broadcast(json.dumps({
        "type": "new_message",
        "message": message.dict(),
        "timestamp": message.created_at.isoformat()
    }))
    
    return message

@api_router.get("/chat/messages")
async def get_chat_messages(current_user: User = Depends(get_current_user)):
    messages = await db.chat_messages.find().sort("created_at", -1).limit(100).to_list(100)
    return messages

# File sharing endpoints
@api_router.post("/files/upload")
async def upload_file(file_data: FileShareCreate, current_user: User = Depends(get_current_user)):
    file_share = FileShare(
        user_id=current_user.id,
        filename=file_data.filename,
        file_data=file_data.file_data,
        file_type=file_data.file_type,
        file_size=file_data.file_size,
        description=file_data.description,
        is_public=file_data.is_public
    )
    
    await db.file_shares.insert_one(file_share.dict())
    return {"message": "File uploaded successfully", "file_id": file_share.id}

@api_router.get("/files/list")
async def get_files(current_user: User = Depends(get_current_user)):
    files = await db.file_shares.find({"is_public": True}).sort("created_at", -1).to_list(100)
    return files

@api_router.get("/files/{file_id}")
async def get_file(file_id: str, current_user: User = Depends(get_current_user)):
    file = await db.file_shares.find_one({"id": file_id})
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return file

# Email endpoints
@api_router.post("/email/send")
async def send_email(email_data: EmailCreate, current_user: User = Depends(get_current_user)):
    email = Email(
        from_user_id=current_user.id,
        to_user_id=email_data.to_user_id,
        subject=email_data.subject,
        body=email_data.body
    )
    
    await db.emails.insert_one(email.dict())
    return {"message": "Email sent successfully", "email_id": email.id}

@api_router.get("/email/inbox")
async def get_inbox(current_user: User = Depends(get_current_user)):
    emails = await db.emails.find({
        "to_user_id": current_user.id,
        "is_deleted": False
    }).sort("created_at", -1).to_list(100)
    return emails

@api_router.get("/email/sent")
async def get_sent_emails(current_user: User = Depends(get_current_user)):
    emails = await db.emails.find({
        "from_user_id": current_user.id,
        "is_deleted": False
    }).sort("created_at", -1).to_list(100)
    return emails

@api_router.put("/email/{email_id}/read")
async def mark_email_as_read(email_id: str, current_user: User = Depends(get_current_user)):
    await db.emails.update_one(
        {"id": email_id, "to_user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    return {"message": "Email marked as read"}

# Search endpoints
@api_router.post("/search")
async def search(query: SearchQuery, current_user: User = Depends(get_current_user)):
    results = {"messages": [], "files": [], "users": []}
    
    if query.search_type in ["all", "messages"]:
        messages = await db.chat_messages.find({
            "message": {"$regex": query.query, "$options": "i"}
        }).limit(20).to_list(20)
        results["messages"] = messages
    
    if query.search_type in ["all", "files"]:
        files = await db.file_shares.find({
            "$or": [
                {"filename": {"$regex": query.query, "$options": "i"}},
                {"description": {"$regex": query.query, "$options": "i"}}
            ],
            "is_public": True
        }).limit(20).to_list(20)
        results["files"] = files
    
    if query.search_type in ["all", "users"]:
        users = await db.users.find({
            "$or": [
                {"username": {"$regex": query.query, "$options": "i"}},
                {"full_name": {"$regex": query.query, "$options": "i"}}
            ]
        }).limit(20).to_list(20)
        results["users"] = [{"id": u["id"], "username": u["username"], "full_name": u["full_name"]} for u in users]
    
    return results

# WebSocket endpoint for real-time chat
@api_router.websocket("/ws/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"User {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

# Admin endpoints (Central Bank)
@api_router.post("/admin/set-salary")
async def set_user_salary(user_id: str, salary: float, current_user: User = Depends(get_current_user)):
    if current_user.role != "central_bank":
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"salary": salary}}
    )
    return {"message": "Salary set successfully"}

@api_router.post("/admin/pay-salaries")
async def pay_salaries(current_user: User = Depends(get_current_user)):
    if current_user.role != "central_bank":
        raise HTTPException(status_code=403, detail="Access denied")
    
    users = await db.users.find({"salary": {"$gt": 0}}).to_list(1000)
    
    for user in users:
        # Pay salary
        await db.users.update_one(
            {"id": user["id"]},
            {"$inc": {"balance": user["salary"]}}
        )
        
        # Create transaction record
        transaction = Transaction(
            from_user_id=current_user.id,
            to_user_id=user["id"],
            amount=user["salary"],
            transaction_type="salary",
            description=f"Salary payment for {user['username']}"
        )
        await db.transactions.insert_one(transaction.dict())
    
    return {"message": f"Salaries paid to {len(users)} users"}

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
    # Create admin user if not exists
    admin_user = await db.users.find_one({"role": "central_bank"})
    if not admin_user:
        admin = User(
            username="central_bank",
            email="admin@impnet.local",
            password_hash=hash_password("admin123"),
            full_name="Central Bank ImpNet",
            role="central_bank",
            balance=35000000000.0  # 35 миллиардов Империума
        )
        await db.users.insert_one(admin.dict())
        logger.info("Central Bank user created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()