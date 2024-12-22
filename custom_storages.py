from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import logging
import boto3
import os

logger = logging.getLogger(__name__)


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
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
            s3.list_buckets()
            logger.info("Successfully connected to S3")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {str(e)}")

    def _normalize_name(self, name):
        """Ensure consistent naming for media files."""
        logger.debug(f"Incoming file name: {name}")
        if name.startswith(f"{settings.MEDIAFILES_LOCATION}/"):
            normalized_name = name
        else:
            normalized_name = (
                    f"{settings.MEDIAFILES_LOCATION}/"
                    f"{name.lstrip('/')}"
                )
        logger.debug(f"Normalized file name: {normalized_name}")
        return normalized_name

    def _save(self, name, content):
        """Ensure file is saved to S3 with proper error handling"""
        logger.info(f"Starting S3 upload for {name}")

        # Normalize path
        name = self._normalize_name(name)
        logger.info(f"Full path for save: {name}")

        # Ensure content is at start of file
        content.seek(0)
        logger.info(f"File size: {content.size} bytes")

        try:
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
            logger.info(f"Successfully uploaded {name} to S3")

            # Verify the file exists
            try:
                s3_client.head_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                    Key=name
                )
                logger.info("File exists in S3 after save")
            except Exception as e:
                logger.error(f"File verification failed: {str(e)}")
                raise

            return name

        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise
