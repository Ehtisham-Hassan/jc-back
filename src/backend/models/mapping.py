from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import uuid
from backend.core.database import Base


class Mapping(Base):
    __tablename__ = "mappings"

    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.file_id"), nullable=False)
    client_number = Column(String(50), nullable=False, index=True)
    vendor_field = Column(String(100), nullable=False)
    jc_field = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=True)  # AI confidence score
    mapping_type = Column(String(20), default="ai")  # ai, manual
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    file = relationship("File", back_populates="mappings")
