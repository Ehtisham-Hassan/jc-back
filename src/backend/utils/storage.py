# In src/backend/utils/storage.py
import os
import tempfile
from typing import Optional

class FileStorage:
    def __init__(self, storage_path: str = "uploads"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def save_file(self, file_content: bytes, filename: str) -> str:
        file_path = os.path.join(self.storage_path, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        return file_path
    
    def get_file_path(self, filename: str) -> Optional[str]:
        file_path = os.path.join(self.storage_path, filename)
        return file_path if os.path.exists(file_path) else None