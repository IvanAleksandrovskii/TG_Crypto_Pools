import os
from typing import Optional, List

from fastapi import UploadFile
from fastapi_storages import FileSystemStorage

from core import settings, logger


class CustomFileSystemStorage(FileSystemStorage):
    def __init__(self, root_path: str, allowed_extensions: Optional[List[str]] = None):
        self.root_path = root_path
        self.allowed_extensions = allowed_extensions or []
        super().__init__(self.root_path)

    async def put(self, file: UploadFile) -> str:
        if not self._check_extension(file.filename):
            raise ValueError(f"File extension not allowed. Allowed extensions: {', '.join(self.allowed_extensions)}")

        os.makedirs(self.root_path, exist_ok=True)
        full_path = os.path.join(self.root_path, file.filename)

        content = await file.read()
        with open(full_path, "wb") as f:
            f.write(content)

        return file.filename

    def delete(self, name: str) -> None:
        full_path = os.path.join(self.root_path, name)
        if os.path.exists(full_path):
            os.remove(full_path)

    def _check_extension(self, filename: str) -> bool:
        if not self.allowed_extensions:
            return True
        return any(filename.lower().endswith(ext.lower()) for ext in self.allowed_extensions)


# Define allowed extensions for each type of file
ALLOWED_IMAGE_EXTENSIONS = settings.media.allowed_image_extensions

coin_storage = CustomFileSystemStorage(settings.media.coins_path, ALLOWED_IMAGE_EXTENSIONS)
pool_storage = CustomFileSystemStorage(settings.media.pools_path, ALLOWED_IMAGE_EXTENSIONS)
chain_storage = CustomFileSystemStorage(settings.media.chains_path, ALLOWED_IMAGE_EXTENSIONS)

logger.info("Initialized all storage instances")
