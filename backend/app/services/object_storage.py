"""对象存储服务 - 支持MinIO/S3/OSS"""
from typing import Optional, BinaryIO, List, Dict, Any
import os
import uuid
from pathlib import Path
from datetime import timedelta
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()

# 根据配置选择对象存储客户端
_object_storage_client = None


def get_object_storage_client():
    """获取对象存储客户端（懒加载）"""
    global _object_storage_client
    
    if _object_storage_client is not None:
        return _object_storage_client
    
    storage_type = settings.OBJECT_STORAGE_TYPE.lower()
    
    try:
        if storage_type == "minio":
            from minio import Minio
            from minio.error import S3Error
            
            _object_storage_client = MinioStorage(
                endpoint=settings.OBJECT_STORAGE_ENDPOINT,
                access_key=settings.OBJECT_STORAGE_ACCESS_KEY,
                secret_key=settings.OBJECT_STORAGE_SECRET_KEY,
                secure=settings.OBJECT_STORAGE_USE_SSL,
                bucket=settings.OBJECT_STORAGE_BUCKET
            )
            app_logger.info("MinIO对象存储客户端初始化成功")
            
        elif storage_type == "s3":
            import boto3
            from botocore.exceptions import ClientError
            
            _object_storage_client = S3Storage(
                endpoint=settings.OBJECT_STORAGE_ENDPOINT,
                access_key=settings.OBJECT_STORAGE_ACCESS_KEY,
                secret_key=settings.OBJECT_STORAGE_SECRET_KEY,
                region=settings.OBJECT_STORAGE_REGION,
                bucket=settings.OBJECT_STORAGE_BUCKET
            )
            app_logger.info("AWS S3对象存储客户端初始化成功")
            
        elif storage_type == "oss":
            import oss2
            
            _object_storage_client = OSSStorage(
                endpoint=settings.OBJECT_STORAGE_ENDPOINT,
                access_key=settings.OBJECT_STORAGE_ACCESS_KEY,
                secret_key=settings.OBJECT_STORAGE_SECRET_KEY,
                bucket=settings.OBJECT_STORAGE_BUCKET
            )
            app_logger.info("阿里云OSS对象存储客户端初始化成功")
            
        else:
            app_logger.warning(f"不支持的对象存储类型: {storage_type}，使用本地存储")
            _object_storage_client = LocalStorage(
                base_path=settings.UPLOAD_DIR
            )
            
    except Exception as e:
        app_logger.error(f"对象存储客户端初始化失败: {e}，使用本地存储")
        _object_storage_client = LocalStorage(
            base_path=settings.UPLOAD_DIR
        )
    
    return _object_storage_client


class ObjectStorageBase:
    """对象存储基类"""
    
    def __init__(self, bucket: str):
        self.bucket = bucket
    
    def upload_file(self, file_data: bytes, object_key: str, 
                   content_type: Optional[str] = None) -> str:
        """上传文件"""
        raise NotImplementedError
    
    def download_file(self, object_key: str) -> bytes:
        """下载文件"""
        raise NotImplementedError
    
    def delete_file(self, object_key: str) -> bool:
        """删除文件"""
        raise NotImplementedError
    
    def file_exists(self, object_key: str) -> bool:
        """检查文件是否存在"""
        raise NotImplementedError
    
    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """生成预签名URL"""
        raise NotImplementedError
    
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出文件"""
        raise NotImplementedError
    
    def get_file_size(self, object_key: str) -> int:
        """获取文件大小"""
        raise NotImplementedError


class MinIOStorage(ObjectStorageBase):
    """MinIO对象存储实现"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 secure: bool = False, bucket: str = "documents"):
        super().__init__(bucket)
        from minio import Minio
        from minio.error import S3Error
        
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.S3Error = S3Error
        
        # 确保bucket存在
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """确保bucket存在"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                app_logger.info(f"创建bucket: {self.bucket}")
        except Exception as e:
            app_logger.error(f"检查/创建bucket失败: {e}")
            raise
    
    def upload_file(self, file_data: bytes, object_key: str,
                   content_type: Optional[str] = None) -> str:
        """上传文件到MinIO"""
        try:
            from io import BytesIO
            
            if content_type is None:
                content_type = "application/octet-stream"
            
            self.client.put_object(
                self.bucket,
                object_key,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            
            app_logger.info(f"文件上传成功: {object_key}")
            return object_key
            
        except self.S3Error as e:
            app_logger.error(f"MinIO上传失败: {e}")
            raise
    
    def download_file(self, object_key: str) -> bytes:
        """从MinIO下载文件"""
        try:
            response = self.client.get_object(self.bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except self.S3Error as e:
            app_logger.error(f"MinIO下载失败: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """从MinIO删除文件"""
        try:
            self.client.remove_object(self.bucket, object_key)
            app_logger.info(f"文件删除成功: {object_key}")
            return True
        except self.S3Error as e:
            app_logger.error(f"MinIO删除失败: {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.stat_object(self.bucket, object_key)
            return True
        except self.S3Error:
            return False
    
    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """生成预签名URL"""
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket,
                object_key,
                expires=timedelta(seconds=expires)
            )
            return url
        except self.S3Error as e:
            app_logger.error(f"生成预签名URL失败: {e}")
            raise
    
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            files = []
            for obj in objects:
                files.append({
                    "key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                })
            return files
        except self.S3Error as e:
            app_logger.error(f"列出文件失败: {e}")
            return []
    
    def get_file_size(self, object_key: str) -> int:
        """获取文件大小"""
        try:
            stat = self.client.stat_object(self.bucket, object_key)
            return stat.size
        except self.S3Error as e:
            app_logger.error(f"获取文件大小失败: {e}")
            return 0


class S3Storage(ObjectStorageBase):
    """AWS S3对象存储实现"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 region: str = "us-east-1", bucket: str = "documents"):
        super().__init__(bucket)
        import boto3
        from botocore.exceptions import ClientError
        
        self.client = boto3.client(
            's3',
            endpoint_url=endpoint if endpoint else None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.ClientError = ClientError
        
        # 确保bucket存在
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """确保bucket存在"""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket不存在，创建它
                self.client.create_bucket(Bucket=self.bucket)
                app_logger.info(f"创建bucket: {self.bucket}")
            else:
                app_logger.error(f"检查bucket失败: {e}")
                raise
    
    def upload_file(self, file_data: bytes, object_key: str,
                   content_type: Optional[str] = None) -> str:
        """上传文件到S3"""
        try:
            if content_type is None:
                content_type = "application/octet-stream"
            
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_data,
                ContentType=content_type
            )
            
            app_logger.info(f"文件上传成功: {object_key}")
            return object_key
            
        except self.ClientError as e:
            app_logger.error(f"S3上传失败: {e}")
            raise
    
    def download_file(self, object_key: str) -> bytes:
        """从S3下载文件"""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return response['Body'].read()
        except self.ClientError as e:
            app_logger.error(f"S3下载失败: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """从S3删除文件"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            app_logger.info(f"文件删除成功: {object_key}")
            return True
        except self.ClientError as e:
            app_logger.error(f"S3删除失败: {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except self.ClientError:
            return False
    
    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """生成预签名URL"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_key},
                ExpiresIn=expires
            )
            return url
        except self.ClientError as e:
            app_logger.error(f"生成预签名URL失败: {e}")
            raise
    
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified']
                })
            return files
        except self.ClientError as e:
            app_logger.error(f"列出文件失败: {e}")
            return []
    
    def get_file_size(self, object_key: str) -> int:
        """获取文件大小"""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
            return response['ContentLength']
        except self.ClientError as e:
            app_logger.error(f"获取文件大小失败: {e}")
            return 0


class OSSStorage(ObjectStorageBase):
    """阿里云OSS对象存储实现"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 bucket: str = "documents"):
        super().__init__(bucket)
        import oss2
        
        auth = oss2.Auth(access_key, secret_key)
        self.client = oss2.Bucket(auth, endpoint, bucket)
    
    def upload_file(self, file_data: bytes, object_key: str,
                   content_type: Optional[str] = None) -> str:
        """上传文件到OSS"""
        try:
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type
            
            self.client.put_object(object_key, file_data, headers=headers)
            app_logger.info(f"文件上传成功: {object_key}")
            return object_key
        except Exception as e:
            app_logger.error(f"OSS上传失败: {e}")
            raise
    
    def download_file(self, object_key: str) -> bytes:
        """从OSS下载文件"""
        try:
            result = self.client.get_object(object_key)
            return result.read()
        except Exception as e:
            app_logger.error(f"OSS下载失败: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """从OSS删除文件"""
        try:
            self.client.delete_object(object_key)
            app_logger.info(f"文件删除成功: {object_key}")
            return True
        except Exception as e:
            app_logger.error(f"OSS删除失败: {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """检查文件是否存在"""
        try:
            return self.client.object_exists(object_key)
        except Exception as e:
            app_logger.error(f"检查文件存在性失败: {e}")
            return False
    
    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """生成预签名URL"""
        try:
            url = self.client.sign_url('GET', object_key, expires)
            return url
        except Exception as e:
            app_logger.error(f"生成预签名URL失败: {e}")
            raise
    
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            import oss2
            files = []
            for obj in oss2.ObjectIterator(self.client, prefix=prefix):
                files.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified
                })
            return files
        except Exception as e:
            app_logger.error(f"列出文件失败: {e}")
            return []
    
    def get_file_size(self, object_key: str) -> int:
        """获取文件大小"""
        try:
            meta = self.client.head_object(object_key)
            return meta.content_length
        except Exception as e:
            app_logger.error(f"获取文件大小失败: {e}")
            return 0


class LocalStorage(ObjectStorageBase):
    """本地文件存储（用于开发环境）"""
    
    def __init__(self, base_path: str = "./data/documents"):
        super().__init__("local")
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def upload_file(self, file_data: bytes, object_key: str,
                   content_type: Optional[str] = None) -> str:
        """上传文件到本地"""
        try:
            file_path = self.base_path / object_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(file_data)
            
            app_logger.info(f"文件上传成功（本地）: {object_key}")
            return object_key
        except Exception as e:
            app_logger.error(f"本地文件上传失败: {e}")
            raise
    
    def download_file(self, object_key: str) -> bytes:
        """从本地下载文件"""
        try:
            file_path = self.base_path / object_key
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            app_logger.error(f"本地文件下载失败: {e}")
            raise
    
    def delete_file(self, object_key: str) -> bool:
        """从本地删除文件"""
        try:
            file_path = self.base_path / object_key
            if file_path.exists():
                file_path.unlink()
                app_logger.info(f"文件删除成功（本地）: {object_key}")
                return True
            return False
        except Exception as e:
            app_logger.error(f"本地文件删除失败: {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """检查文件是否存在"""
        file_path = self.base_path / object_key
        return file_path.exists()
    
    def get_presigned_url(self, object_key: str, expires: int = 3600) -> str:
        """生成预签名URL（本地存储返回相对路径）"""
        # 本地存储不支持预签名URL，返回相对路径
        return f"/files/{object_key}"
    
    def list_files(self, prefix: str = "") -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            files = []
            search_path = self.base_path / prefix if prefix else self.base_path
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.base_path)
                    files.append({
                        "key": str(rel_path),
                        "size": file_path.stat().st_size,
                        "last_modified": file_path.stat().st_mtime
                    })
            return files
        except Exception as e:
            app_logger.error(f"列出文件失败: {e}")
            return []
    
    def get_file_size(self, object_key: str) -> int:
        """获取文件大小"""
        try:
            file_path = self.base_path / object_key
            if file_path.exists():
                return file_path.stat().st_size
            return 0
        except Exception as e:
            app_logger.error(f"获取文件大小失败: {e}")
            return 0


class ObjectStorageService:
    """对象存储服务封装"""
    
    def __init__(self):
        self.client = get_object_storage_client()
        self.storage_type = settings.OBJECT_STORAGE_TYPE.lower()
    
    def generate_object_key(self, filename: str, prefix: str = "documents") -> str:
        """生成对象存储键"""
        # 使用UUID确保唯一性
        file_ext = Path(filename).suffix
        unique_id = str(uuid.uuid4())
        return f"{prefix}/{unique_id}{file_ext}"
    
    def upload_document(self, file_data: bytes, filename: str,
                       content_type: Optional[str] = None) -> Dict[str, Any]:
        """上传文档"""
        object_key = self.generate_object_key(filename)
        
        try:
            self.client.upload_file(file_data, object_key, content_type)
            file_size = len(file_data)
            
            return {
                "object_key": object_key,
                "storage_type": self.storage_type,
                "bucket": self.client.bucket,
                "file_size": file_size,
                "filename": filename
            }
        except Exception as e:
            app_logger.error(f"上传文档失败: {e}")
            raise
    
    def download_document(self, object_key: str) -> bytes:
        """下载文档"""
        return self.client.download_file(object_key)
    
    def delete_document(self, object_key: str) -> bool:
        """删除文档"""
        return self.client.delete_file(object_key)
    
    def get_download_url(self, object_key: str, expires: int = 3600) -> str:
        """获取下载URL（预签名URL）"""
        return self.client.get_presigned_url(object_key, expires)
    
    def document_exists(self, object_key: str) -> bool:
        """检查文档是否存在"""
        return self.client.file_exists(object_key)
    
    def get_document_size(self, object_key: str) -> int:
        """获取文档大小"""
        return self.client.get_file_size(object_key)


# 全局对象存储服务实例
object_storage_service = ObjectStorageService()

