import os
import psycopg2
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.hash import bcrypt
from jose import JWTError, jwt
from typing import List, Optional
from datetime import datetime, timedelta

SECRET_KEY = "supersecretjwt"  # Pro demo, změň v produkci!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pro demo, v produkci omez!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nové proměnné prostředí
PG_HOST = os.environ.get('PG_HOST', 'localhost')
PG_DB = os.environ.get('PG_DB', 'yourdb')
PG_USER = os.environ.get('PG_USER', 'youruser')
PG_PASS = os.environ.get('PG_PASS', 'yourpassword')

print("DEBUG PG_HOST:", PG_HOST)
print("DEBUG PG_DB:", PG_DB)
print("DEBUG PG_USER:", PG_USER)
print("DEBUG PG_PASS:", PG_PASS)

def get_db():
    return psycopg2.connect(
        host=PG_HOST,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS
    )

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: int
    username: str
    is_admin: bool

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        username = payload.get("username")
        is_admin = payload.get("is_admin")
        if user_id is None or username is None:
            raise credentials_exception
        return User(id=user_id, username=username, is_admin=is_admin)
    except JWTError:
        raise credentials_exception

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = %s", (form_data.username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user and bcrypt.verify(form_data.password, user[2]):
        token = create_access_token({"id": user[0], "username": user[1], "is_admin": user[3]})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Incorrect username or password")

@app.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# Endpoint: seznam allowed_devices (pro parser, admin)
@app.get("/allowed_devices", response_model=List[str])
def get_allowed_devices(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT dev_eui FROM allowed_devices")
    devices = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return devices

# Endpoint: přidání allowed_device (admin only)
class DeviceIn(BaseModel):
    dev_eui: str
    name: Optional[str] = None

@app.post("/allowed_devices")
def add_allowed_device(device: DeviceIn, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO allowed_devices (dev_eui, name, added_by) VALUES (%s, %s, %s) ON CONFLICT (dev_eui) DO NOTHING",
        (device.dev_eui, device.name, current_user.id),
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"result": "ok"}

# Endpoint: měření (user, admin)
@app.get("/measurements")
def get_measurements(
    device_eui: str,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT measured_at, measurement_id, value FROM measurements WHERE device_eui = %s"
    params = [device_eui]
    if from_ts:
        query += " AND measured_at >= %s"
        params.append(from_ts)
    if to_ts:
        query += " AND measured_at <= %s"
        params.append(to_ts)
    query += " ORDER BY measured_at ASC"
    cur.execute(query, tuple(params))
    data = [{"measured_at": row[0], "measurement_id": row[1], "value": row[2]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    return data