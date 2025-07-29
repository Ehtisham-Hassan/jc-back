from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Any
import uuid
import os
import json

from backend.core.database import get_db
from backend.models.file import File as FileModel

router = APIRouter()

# Counter file to track the next ID
COUNTER_FILE = "file_counter.json"

def get_next_file_id() -> str:
    """
    Get the next sequential file ID in format jc_XX
    """
    try:
        # Try to read existing counter
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, 'r') as f:
                counter_data = json.load(f)
                current_count = counter_data.get('count', 0)
        else:
            current_count = 0
        
        # Increment counter
        next_count = current_count + 1
        
        # Save updated counter
        with open(COUNTER_FILE, 'w') as f:
            json.dump({'count': next_count}, f)
        
        # Format as jc_XX (with leading zeros)
        return f"jc_{next_count:02d}"
        
    except Exception as e:
        print(f"Error managing file counter: {e}")
        # Fallback to timestamp-based ID if counter fails
        import time
        timestamp = int(time.time())
        return f"jc_{timestamp}"

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    client_number: str = Form(...),
    # current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    Upload vendor files (CSV, XLS, JSON, TSV, TXT) with client number.
    """
    print("\nfile_id1: ------------------------------\n")
    # Validate file type
    allowed_extensions = {'.csv', '.xls', '.xlsx', '.json', '.tsv', '.txt'}
    file_extension = os.path.splitext(file.filename)[1].lower()
    print("\nfile_id:2 ------------------------------\n")
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not supported. Allowed: {allowed_extensions}"
        )
    print("\nfile_id3: ------------------------------\n")
    # Validate file size (50MB limit)
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 50MB limit"
        )

    # Create upload directory if it doesn't exist
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    print("\nfile_id4: ------------------------------\n")
    
    # Generate sequential file ID
    file_id = get_next_file_id()
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(upload_dir, safe_filename)
    file_id_with_extension = f"{file_id}{file_extension}"
    print("\nfile_id15: ------------------------------\n")
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    print("\nfile_id6: ------------------------------\n")

    # Create file record in database
    # file_record = FileModel(
    #     file_id=file_id,  # Use the new sequential ID
    #     client_number=client_number,
    #     filename=file.filename,
    #     file_path=file_path,
    #     file_size=str(file.size) if file.size else None,
    #     file_type=file_extension[1:].upper(),
    #     status="uploaded"
    # )

    # db.add(file_record)
    # db.commit()
    # db.refresh(file_record)

    print("file_id7: ", file_id)
    return {
        "file_id": file_id_with_extension,
        "filename": file.filename,
        "client_number": client_number,
        "status": "uploaded",
        "message": "File uploaded successfully"
    }
