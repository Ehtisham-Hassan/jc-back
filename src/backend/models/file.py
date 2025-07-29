from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from backend.core.database import Base


class File(Base):
    __tablename__ = "files"

    file_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_number = Column(String(50), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)  # Path to stored file
    file_size = Column(String(20), nullable=True)  # File size in bytes
    file_type = Column(String(10), nullable=False)  # CSV, XLS, JSON, TSV, TXT
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="uploaded")  # uploaded, processing, completed, failed
