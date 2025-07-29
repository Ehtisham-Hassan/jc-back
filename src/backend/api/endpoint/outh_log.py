from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, List
from datetime import datetime

from backend.core.database import get_db
from backend.core.config import settings
# from backend.dependencies.auth import get_current_active_user, get_current_active_superuser
from backend.models.user import User
from backend.schemas.user import User as UserSchema, UserCreate, UserUpdate
from backend.schemas.token import Token
from backend.utils.security import create_access_token, get_password_hash, verify_password

router = APIRouter()

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/auth/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    
    access_token_expires = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/users", response_model=UserSchema)
def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    # current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Create new user.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_superuser=user_in.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=List[UserSchema])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    # current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Retrieve users.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/me", response_model=UserSchema)
def read_user_me(
    user_id: int = Query(1, description="User ID to get"),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Get user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/me", response_model=UserSchema)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    user_id: int = Form(...),
    password: str = None,
    full_name: str = None,
    email: str = None,
) -> Any:
    """
    Update user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_user_data = UserUpdate(**user.__dict__)
    if password is not None:
        current_user_data.password = password
    if full_name is not None:
        current_user_data.full_name = full_name
    if email is not None:
        current_user_data.email = email
    user = update_user(db=db, db_obj=user, obj_in=current_user_data)
    return user


@router.get("/users/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ============================================================================
# AUDIT ENDPOINTS
# ============================================================================

@router.get("/audit/{client_number}")
def get_audit_trail(
    client_number: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Retrieve audit trail for mapping activities.
    """
    # TODO: Implement audit trail logic
    # This is a placeholder implementation
    
    mock_audit_logs = [
        {
            "action": "file_upload",
            "timestamp": datetime.now().isoformat(),
            "user_id": 1, #current_user.id
            "details": f"Uploaded file for client {client_number}"
        },
        {
            "action": "mapping_saved",
            "timestamp": datetime.now().isoformat(),
            "user_id": 1, #current_user.id
            "details": f"Saved mappings for client {client_number}"
        }
    ]
    
    return {
        "client_number": client_number,
        "audit_logs": mock_audit_logs[offset:offset+limit],
        "total": len(mock_audit_logs)
    }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def update_user(
    *,
    db: Session,
    db_obj: User,
    obj_in: UserUpdate,
) -> User:
    """
    Update user.
    """
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.dict(exclude_unset=True)
    if update_data.get("password"):
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
