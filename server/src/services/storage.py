# src/services/storage.py
import os
import uuid
from pathlib import Path
from aiofiles import open as aio_open

UPLOAD_DIR = Path("uploads")

class LocalFileStorage:
    def __init__(self, base_dir: Path = UPLOAD_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, extension: str = ".jpg") -> str:
        filename = f"{uuid.uuid4().hex}{extension}"
        dir_path = self.base_dir / "ads"
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename
        
        async with aio_open(file_path, "wb") as f:
            await f.write(file_bytes)
        return str(file_path.relative_to(self.base_dir))  # относительный путь

    def get_url(self, storage_path: str) -> str:
        return f"static/uploads/{storage_path}"  # отдавай через nginx/fastapi stati