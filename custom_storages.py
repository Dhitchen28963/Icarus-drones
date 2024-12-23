from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import boto3


class StaticStorage(S3Boto3Storage):
    location = settings.STATICFILES_LOCATION
    default_acl = 'public-read'
    file_overwrite = False


class MediaStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION
    default_acl = 'public-read'
    file_overwrite = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Test S3 connection
        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        s3.list_buckets()

    def _normalize_name(self, name):
        """Ensure consistent naming for media files."""
        if name.startswith(f"{settings.MEDIAFILES_LOCATION}/"):
            normalized_name = name
        else:
            normalized_name = (
                f"{settings.MEDIAFILES_LOCATION}/"
                f"{name.lstrip('/')}"
            )
        return normalized_name

    def _save(self, name, content):
        """Ensure file is saved to S3 with proper error handling"""
        # Normalize path
        name = self._normalize_name(name)

        # Ensure content is at start of file
        content.seek(0)

        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        # Upload directly to S3
        s3_client.upload_fileobj(
            content,
            settings.AWS_STORAGE_BUCKET_NAME,
            name,
            ExtraArgs={'ACL': 'public-read'}
        )

        # Verify the file exists
        s3_client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=name
        )

        return name
