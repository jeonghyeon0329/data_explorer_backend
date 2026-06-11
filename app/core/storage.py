from io import BytesIO
from typing import Optional, Any

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    Minio = None
    S3Error = Exception


class MinioStorage:
    """MinIO 연결과 객체 입출력을 관리하는 스토리지 래퍼."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = True,
    ):
        if Minio is None:
            raise ImportError(
                "MinIO client package is not installed. Install it with 'pip install minio'."
            )
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def ensure_bucket(self, bucket_name: str) -> bool:
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
            return True
        return False

    def upload_object(
        self,
        bucket_name: str,
        object_name: str,
        data: Any,
        content_type: Optional[str] = None,
    ) -> None:
        if isinstance(data, (bytes, bytearray)):
            buffer = BytesIO(data)
            length = len(data)
            self.client.put_object(
                bucket_name,
                object_name,
                buffer,
                length=length,
                content_type=content_type,
            )
        else:
            self.client.put_object(
                bucket_name,
                object_name,
                data,
                length=-1,
                content_type=content_type,
            )

    def download_object(self, bucket_name: str, object_name: str) -> bytes:
        with self.client.get_object(bucket_name, object_name) as stream:
            return stream.read()

    def remove_object(self, bucket_name: str, object_name: str) -> None:
        self.client.remove_object(bucket_name, object_name)

    def get_client(self) -> Any:
        return self.client
