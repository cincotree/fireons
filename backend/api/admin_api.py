from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import Token, create_access_token, decode_admin_token, verify_password
from database.models import Admin
from database.repository import AdminRepository
from database.session import get_session

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()

UNUSED_PASSWORD_HASH = "$2b$12$BA/OavSGyA19lDzZ6Am.4OT4bKazcuzlLCUrey4mXOkfIg0jBbceS"


class AdminLogin(BaseModel):
    username: str
    password: str


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Admin:
    admin_id = decode_admin_token(credentials.credentials)
    admin = await AdminRepository(session).get_by_id(admin_id) if admin_id else None
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin


@router.post("/login", response_model=Token)
async def login(credentials: AdminLogin, session: AsyncSession = Depends(get_session)):
    admin = await AdminRepository(session).get_by_username(credentials.username)
    password_ok = verify_password(credentials.password, admin.hashed_password if admin else UNUSED_PASSWORD_HASH)
    if admin is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token({"sub": admin.id, "username": admin.username, "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}
