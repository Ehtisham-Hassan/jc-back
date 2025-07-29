from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Any, List, Optional , Literal
import uuid
import os
from datetime import datetime
from pydantic import BaseModel


import json


from backend.core.database import get_db
from backend.core.config import settings
# from backend.dependencies.auth import get_current_active_user, get_current_active_superuser

# from agents import Agent
import pandas as pd

# Import upload router
from backend.api.endpoint.upload import router as upload_router

# Import auth router
from backend.api.endpoint.outh_log import router as auth_router

# Import mapping router
from backend.api.endpoint.mapping import router as mapping_router

router = APIRouter()

# Include upload router
router.include_router(upload_router, tags=["upload"])

# Include auth router
router.include_router(auth_router, tags=["auth"])

# Include mapping router
router.include_router(mapping_router, tags=["mapping"])

# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@router.get("/export/final.csv")
async def export_final_csv(
    file_id: str = Query(...),
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Preview and download JC-compliant output files.
    """

    file_to_return = os.path.join("uploads", file_id)

    return FileResponse(
        path=file_to_return,
        media_type='application/octet-stream',
        filename=f"export_{file_id}"
    )

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# import pandas as pd


@router.get("/file/headers")
def get_xls_headers(filename: str):
    """
    Read an .xls file from the uploads folder and return all headers.
    """
    file_path = os.path.join("uploads", filename)
    try:
        df = pd.read_excel(file_path)
        headers = list(df.columns)
        return {"headers": headers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    