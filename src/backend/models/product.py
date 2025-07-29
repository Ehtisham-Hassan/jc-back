from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import uuid
from backend.core.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.file_id"), nullable=False)
    client_number = Column(String(50), nullable=False, index=True)
    parent_sku = Column(String(100), nullable=False)
    child_skus = Column(Text, nullable=True)  # JSON string of child SKUs
    configuration_fields = Column(Text, nullable=True)  # JSON string of config fields
    is_configurable = Column(Boolean, default=True)
    variant_count = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    file = relationship("File", back_populates="products") 