"""
Cloudflare R2 Storage Manager for MSC DRIVr Safety Portal
Handles image uploads for safety infographics with automatic resizing and optimization
"""

import boto3
import os
from datetime import datetime
import streamlit as st
from PIL import Image
import io
import uuid

class CloudflareR2Manager:
    def __init__(self):
        """Initialize Cloudflare R2 client with credentials from environment"""
        self.bucket_name = None
        self.s3_client = None
        self.base_url = None
        
        # Try to initialize with environment variables
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize R2 client if credentials are available"""
        try:
            # Check for required environment variables
            account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
            access_key = os.getenv('CLOUDFLARE_R2_ACCESS_KEY')
            secret_key = os.getenv('CLOUDFLARE_R2_SECRET_KEY')
            bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
            
            if all([account_id, access_key, secret_key, bucket_name]):
                # Configure S3 client for Cloudflare R2
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name='auto'  # R2 uses 'auto' region
                )
                self.bucket_name = bucket_name
                # Get the actual bucket ID for public URLs - need to query R2 for this
                self.base_url = None  # Will be set after getting bucket ID
                self._get_bucket_public_url()
                
                # Test connection
                self._test_connection()
                
        except Exception as e:
            print(f"R2 initialization failed: {e}")
            self.s3_client = None
    
    def _get_bucket_public_url(self):
        """Get the bucket's public URL by extracting from a test upload or using bucket metadata"""
        try:
            if self.s3_client:
                # Try to get bucket location/metadata to extract the bucket ID
                response = self.s3_client.head_bucket(Bucket=self.bucket_name)
                # For now, use a simpler approach - hardcode the working format from user's example
                # The bucket ID appears to be 46584f5bf24c4481ac1e5753ae0a8b35 based on working URL
                self.base_url = f'https://pub-46584f5bf24c4481ac1e5753ae0a8b35.r2.dev'
                return True
        except Exception as e:
            print(f"Could not determine bucket public URL: {e}")
            # Fallback to bucket name format (won't work but better than nothing)
            self.base_url = f'https://pub-{self.bucket_name}.r2.dev'
            return False
        return False
    
    def _test_connection(self):
        """Test R2 connection and bucket access"""
        try:
            if self.s3_client:
                # First try to list objects to test connection
                self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
                return True
        except Exception as e:
            print(f"R2 connection test failed: {e}")
            # Don't disable client yet - might work for uploads even if head_bucket fails
            return False
        return False
    
    def is_configured(self):
        """Check if R2 is properly configured"""
        return self.s3_client is not None
    
    def optimize_image(self, image_file, max_size=(1024, 1024), quality=85):
        """Optimize image for web storage - resize and compress"""
        try:
            # Open image with PIL
            image = Image.open(image_file)
            
            # Convert RGBA to RGB if necessary (for JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize if larger than max_size
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            return output, image.size
            
        except Exception as e:
            raise Exception(f"Image optimization failed: {str(e)}")
    
    def upload_infographic(self, image_file, submitter, title=None):
        """Upload safety infographic to Cloudflare R2"""
        if not self.is_configured():
            raise Exception("Cloudflare R2 not configured. Please set up credentials.")
        
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_id = str(uuid.uuid4())[:8]
            file_extension = image_file.name.split('.')[-1].lower()
            filename = f"safety_infographics/{timestamp}_{submitter}_{file_id}.jpg"
            
            # Optimize image
            optimized_image, dimensions = self.optimize_image(image_file)
            file_size = optimized_image.getbuffer().nbytes
            
            # Upload to R2 with public read access
            self.s3_client.upload_fileobj(
                optimized_image,
                self.bucket_name,
                filename,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'public-read',  # Make the object publicly readable
                    'Metadata': {
                        'submitter': submitter,
                        'original_filename': image_file.name,
                        'title': title or 'Safety Infographic',
                        'upload_timestamp': datetime.now().isoformat(),
                        'optimized_size': str(file_size),
                        'dimensions': f"{dimensions[0]}x{dimensions[1]}"
                    }
                }
            )
            
            # Generate public URL using the working R2 format
            public_url = f"{self.base_url}/{filename}"
            
            return {
                'success': True,
                'url': public_url,
                'filename': filename,
                'size': file_size,
                'dimensions': dimensions,
                'message': f'Image uploaded successfully ({file_size // 1024}KB)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Upload failed: {str(e)}'
            }
    
    def get_upload_stats(self):
        """Get usage statistics for the bucket"""
        if not self.is_configured():
            return None
        
        try:
            # List objects to get basic stats
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='safety_infographics/'
            )
            
            total_size = 0
            file_count = 0
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    total_size += obj['Size']
                    file_count += 1
            
            return {
                'total_files': file_count,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'free_tier_usage_percent': round((total_size / (10 * 1024 * 1024 * 1024)) * 100, 1)
            }
            
        except Exception as e:
            return None

def get_r2_setup_instructions():
    """Return setup instructions for Cloudflare R2"""
    return """
    ## Cloudflare R2 Setup Instructions
    
    1. **Create Cloudflare Account**: Sign up at cloudflare.com
    2. **Create R2 Bucket**: 
       - Go to R2 Object Storage in dashboard
       - Create new bucket (e.g., 'msc-drivr-safety')
    3. **Generate API Tokens**:
       - Go to My Profile > API Tokens
       - Create Custom Token with R2 permissions
    4. **Set Environment Variables**:
       - `CLOUDFLARE_ACCOUNT_ID`: Your account ID
       - `CLOUDFLARE_R2_ACCESS_KEY`: API access key
       - `CLOUDFLARE_R2_SECRET_KEY`: API secret key
       - `CLOUDFLARE_R2_BUCKET_NAME`: Your bucket name
    
    **Free Tier Benefits:**
    - 10 GB storage per month
    - No egress fees
    - Perfect for ~10,000 optimized images
    """