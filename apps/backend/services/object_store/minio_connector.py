"""
MinIO connector for object storage operations.

This module provides CRUD operations for files stored in MinIO,
integrated with the user_upload database table.
"""

import io
import os
import uuid
from functools import lru_cache
from typing import Optional, BinaryIO, Dict, List
from datetime import datetime, timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error

# Try to import settings, with fallback for when running as script
try:
    from backend.config import settings
except ImportError:
    # If running as script, add parent directory to path
    import sys
    from pathlib import Path
    # File is at: apps/backend/services/document_parser/financial_text_extractor.py
    # Need to add apps/ to path so backend can be imported
    apps_dir = Path(__file__).parent.parent.parent.parent  # Go up to apps/
    if str(apps_dir) not in sys.path:
        sys.path.insert(0, str(apps_dir))
    from backend.config import settings


class MinIOConnector:
    """MinIO connector for file storage operations."""

    def __init__(self):
        """Initialize MinIO client with settings."""
        # Convert MINIO_SECURE from int to bool (0/1 -> False/True)
        secure = bool(settings.MINIO_SECURE) if isinstance(settings.MINIO_SECURE, int) else settings.MINIO_SECURE
            
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=secure
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._bucket_checked = False

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't.
        
        This is called lazily when needed, not during initialization,
        to allow time for the createbuckets service to finish setting up credentials.
        """
        if self._bucket_checked:
            return
            
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
            self._bucket_checked = True
        except S3Error as e:
            # If it's an authentication error, the access keys might not be ready yet
            # This can happen during startup when createbuckets service is still running
            if e.code in ["InvalidAccessKeyId", "SignatureDoesNotMatch"]:
                raise Exception(
                    f"MinIO authentication failed. This may happen during startup. "
                    f"Please ensure the createbuckets service has finished running. Error: {e}"
                )
            raise Exception(f"Failed to ensure bucket exists: {e}")

    def _get_object_path(self, user_id: int, document_id: str) -> str:
        """
        Generate object path in MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            
        Returns:
            Object path string
        """
        return f"users/{user_id}/{document_id}"

    def upload_file(
        self,
        user_id: int,
        document_id: str,
        file_data: BinaryIO,
        file_name: str,
        content_type: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Upload a file to MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            file_data: File-like object (BinaryIO) containing file data
            file_name: Original file name
            content_type: MIME type of the file (optional)
            file_size: Size of the file in bytes (optional, will be determined if not provided)
            
        Returns:
            Dictionary with file_url and metadata
            
        Raises:
            S3Error: If upload fails
        """
        self._ensure_bucket_exists()
        object_path = self._get_object_path(user_id, document_id)
        
        # Determine file size if not provided
        if file_size is None:
            file_data.seek(0, os.SEEK_END)
            file_size = file_data.tell()
            file_data.seek(0)
        
        # Default content type
        if content_type is None:
            content_type = "application/octet-stream"
        
        try:
            # Upload file to MinIO
            self.client.put_object(
                self.bucket_name,
                object_path,
                file_data,
                length=file_size,
                content_type=content_type,
                metadata={
                    "user_id": str(user_id),
                    "document_id": document_id,
                    "file_name": file_name,
                    "uploaded_at": datetime.utcnow().isoformat()
                }
            )
            
            # Generate S3-style URL (standard format for object storage references)
            file_url = f"s3://{self.bucket_name}/{object_path}"
            
            return {
                "file_url": file_url,
                "object_path": object_path,
                "bucket": self.bucket_name,
                "file_size": file_size,
                "content_type": content_type
            }
        except S3Error as e:
            raise Exception(f"Failed to upload file to MinIO: {e}")

    def download_file(
        self,
        user_id: int,
        document_id: str
    ) -> BytesIO:
        """
        Download a file from MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            
        Returns:
            BytesIO object containing file data
            
        Raises:
            S3Error: If download fails
            FileNotFoundError: If file doesn't exist
        """
        self._ensure_bucket_exists()
        object_path = self._get_object_path(user_id, document_id)
        
        try:
            response = self.client.get_object(self.bucket_name, object_path)
            file_data = BytesIO(response.read())
            response.close()
            response.release_conn()
            return file_data
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {object_path}")
            raise Exception(f"Failed to download file from MinIO: {e}")

    def get_file_info(
        self,
        user_id: int,
        document_id: str
    ) -> Dict:
        """
        Get file metadata from MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            
        Returns:
            Dictionary with file metadata
            
        Raises:
            S3Error: If operation fails
            FileNotFoundError: If file doesn't exist
        """
        self._ensure_bucket_exists()
        object_path = self._get_object_path(user_id, document_id)
        
        try:
            stat = self.client.stat_object(self.bucket_name, object_path)
            
            return {
                "document_id": document_id,
                "user_id": user_id,
                "object_path": object_path,
                "file_size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "metadata": stat.metadata or {},
                "etag": stat.etag
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {object_path}")
            raise Exception(f"Failed to get file info from MinIO: {e}")

    def get_presigned_url(
        self,
        user_id: int,
        document_id: str,
        expires_seconds: int = 3600
    ) -> str:
        """
        Get a presigned URL for temporary file access.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            expires_seconds: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string
            
        Raises:
            S3Error: If operation fails
            FileNotFoundError: If file doesn't exist
        """
        object_path = self._get_object_path(user_id, document_id)
        
        try:
            # Check if file exists
            self.client.stat_object(self.bucket_name, object_path)
            
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_path,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {object_path}")
            raise Exception(f"Failed to generate presigned URL: {e}")

    def update_file(
        self,
        user_id: int,
        document_id: str,
        file_data: BinaryIO,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Update/replace a file in MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            file_data: File-like object (BinaryIO) containing new file data
            file_name: New file name (optional, preserves old if not provided)
            content_type: MIME type of the file (optional)
            file_size: Size of the file in bytes (optional)
            
        Returns:
            Dictionary with updated file_url and metadata
            
        Raises:
            S3Error: If update fails
            FileNotFoundError: If file doesn't exist
        """
        object_path = self._get_object_path(user_id, document_id)
        
        # Check if file exists
        try:
            old_stat = self.client.stat_object(self.bucket_name, object_path)
            old_metadata = old_stat.metadata or {}
            old_file_name = file_name or old_metadata.get("file_name", "unknown")
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {object_path}")
            raise Exception(f"Failed to check existing file: {e}")
        
        # Determine file size if not provided
        if file_size is None:
            file_data.seek(0, os.SEEK_END)
            file_size = file_data.tell()
            file_data.seek(0)
        
        # Use existing content type if not provided
        if content_type is None:
            content_type = old_stat.content_type or "application/octet-stream"
        
        try:
            # Upload new version
            self.client.put_object(
                self.bucket_name,
                object_path,
                file_data,
                length=file_size,
                content_type=content_type,
                metadata={
                    "user_id": str(user_id),
                    "document_id": document_id,
                    "file_name": old_file_name,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Generate S3-style URL (standard format for object storage references)
            file_url = f"s3://{self.bucket_name}/{object_path}"
            
            return {
                "file_url": file_url,
                "object_path": object_path,
                "bucket": self.bucket_name,
                "file_size": file_size,
                "content_type": content_type
            }
        except S3Error as e:
            raise Exception(f"Failed to update file in MinIO: {e}")

    def delete_file(
        self,
        user_id: int,
        document_id: str
    ) -> None:
        """
        Delete a file from MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            
        Raises:
            S3Error: If deletion fails
            FileNotFoundError: If file doesn't exist
        """
        self._ensure_bucket_exists()
        object_path = self._get_object_path(user_id, document_id)
        
        try:
            # Check if file exists first
            self.client.stat_object(self.bucket_name, object_path)
            
            # Delete the file
            self.client.remove_object(self.bucket_name, object_path)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {object_path}")
            raise Exception(f"Failed to delete file from MinIO: {e}")

    def list_user_files(
        self,
        user_id: int,
        prefix: Optional[str] = None
    ) -> List[Dict]:
        """
        List all files for a specific user.
        
        Args:
            user_id: User ID
            prefix: Optional prefix filter for object names
            
        Returns:
            List of dictionaries with file information
        """
        user_prefix = f"users/{user_id}/"
        if prefix:
            user_prefix = f"{user_prefix}{prefix}"
        
        files = []
        try:
            objects = self.client.list_objects(
                self.bucket_name,
                prefix=user_prefix,
                recursive=True
            )
            
            for obj in objects:
                # Extract document_id from object path
                document_id = obj.object_name.split("/")[-1]
                
                files.append({
                    "document_id": document_id,
                    "user_id": user_id,
                    "object_path": obj.object_name,
                    "file_size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                })
        except S3Error as e:
            raise Exception(f"Failed to list user files: {e}")
        
        return files

    def file_exists(
        self,
        user_id: int,
        document_id: str
    ) -> bool:
        """
        Check if a file exists in MinIO.
        
        Args:
            user_id: User ID
            document_id: Document/file ID from database
            
        Returns:
            True if file exists, False otherwise
        """
        object_path = self._get_object_path(user_id, document_id)
        
        try:
            self.client.stat_object(self.bucket_name, object_path)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise Exception(f"Failed to check file existence: {e}")

    def health_check(self) -> bool:
        """
        Check the health of the MinIO connector.
        
        Returns:
            True if the connector can list buckets, False otherwise
        """
        try:
            self.client.list_buckets()
            return True
        except Exception as e:
            raise Exception(f"Failed to check MinIO health: {e}")


# Singleton instance
_minio_connector: Optional[MinIOConnector] = None

@lru_cache(maxsize=1)
def get_minio_connector() -> MinIOConnector:
    """
    Get or create MinIO connector instance (singleton pattern).
    
    Returns:
        MinIOConnector instance
    """
    global _minio_connector
    if _minio_connector is None:
        _minio_connector = MinIOConnector()
    return _minio_connector


if __name__ == "__main__":
    minio_connector = get_minio_connector()
    minio_connector.upload_file(
        user_id=1,
        document_id="1234567890",
        file_data=io.BytesIO(b"Hello, world!"),
        file_name="test.txt"
    )

    print(minio_connector.list_user_files(
        user_id=1
    ))