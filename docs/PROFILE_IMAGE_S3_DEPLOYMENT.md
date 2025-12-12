# Profile Image Storage - Production Deployment Guide

This document provides step-by-step instructions for configuring profile image storage with AWS S3 in production.

## Overview

The application supports two storage modes for profile images:

| Environment | Storage Location | URL Format |
|-------------|------------------|------------|
| Development | Local `uploads/profile/` folder | `/uploads/profile/{filename}` |
| Production | AWS S3 bucket | `https://{bucket}.s3.{region}.amazonaws.com/profile-images/{filename}` |

The storage mode is determined by the `ENVIRONMENT` variable (or `DEBUG` flag).

---

## Prerequisites

1. **AWS Account** with S3 access
2. **IAM User** with programmatic access and S3 permissions
3. **S3 Bucket** created in your preferred region

---

## Step 1: Create S3 Bucket

1. Go to AWS Console → S3 → Create bucket
2. Configure bucket settings:
   - **Bucket name**: `pixelperfectui-profile-images` (or your preferred name)
   - **Region**: `ap-southeast-1` (or your preferred region)
   - **Object Ownership**: ACLs enabled (for public-read access)
   - **Block Public Access**: Uncheck "Block all public access" (required for public profile images)

3. After creation, go to **Permissions** tab and add this bucket policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::pixelperfectui-profile-images/profile-images/*"
        }
    ]
}
```

> **Note**: Replace `pixelperfectui-profile-images` with your actual bucket name.

---

## Step 2: Create IAM User for S3 Access

1. Go to AWS Console → IAM → Users → Create user
2. User name: `pixelperfectui-s3-user`
3. Attach policy directly with this custom policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::pixelperfectui-profile-images/profile-images/*"
        }
    ]
}
```

4. Create the user and generate **Access Keys**:
   - Go to Security credentials → Create access key
   - Choose "Application running outside AWS"
   - Save the **Access Key ID** and **Secret Access Key**

---

## Step 3: Configure Environment Variables

Add the following variables to your production `.env` file:

```env
# Environment (REQUIRED for S3)
ENVIRONMENT=production

# AWS S3 Configuration (REQUIRED)
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=pixelperfectui-profile-images

# Optional: CloudFront or custom domain
# AWS_S3_CUSTOM_DOMAIN=cdn.yourdomain.com
```

### Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `ENVIRONMENT` | Yes | Set to `production` to enable S3 storage |
| `AWS_ACCESS_KEY_ID` | Yes | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | IAM user secret key |
| `AWS_REGION` | Yes | S3 bucket region (e.g., `ap-southeast-1`) |
| `AWS_S3_BUCKET` | Yes | S3 bucket name |
| `AWS_S3_CUSTOM_DOMAIN` | No | Custom domain for serving images (CloudFront) |

---

## Step 4: Docker Compose Configuration

The `docker-compose.yml` is already configured to pass S3 variables to the backend container:

```yaml
environment:
  - ENVIRONMENT=${ENVIRONMENT:-development}
  - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
  - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
  - AWS_REGION=${AWS_REGION:-ap-southeast-1}
  - AWS_S3_BUCKET=${AWS_S3_BUCKET:-}
  - AWS_S3_CUSTOM_DOMAIN=${AWS_S3_CUSTOM_DOMAIN:-}
```

---

## Step 5: Install Dependencies

Ensure `boto3` is installed in the backend container. It's already added to `requirements.txt`:

```
boto3==1.35.0
```

If deploying without Docker, install manually:

```bash
pip install boto3==1.35.0
```

---

## Step 6: Deploy and Verify

1. **Restart containers** with updated environment:

```bash
docker-compose down
docker-compose up -d --build
```

2. **Verify S3 connection** by uploading a profile image:
   - Log in to the application
   - Go to Profile Settings
   - Upload a new profile image
   - Check the browser's Network tab - the image URL should be an S3 URL

3. **Check S3 bucket** for uploaded files:
   - Go to AWS Console → S3 → Your bucket → `profile-images/` folder

---

## Optional: CloudFront CDN Setup

For better performance, set up CloudFront:

1. Create CloudFront distribution with S3 bucket as origin
2. Configure custom domain (optional)
3. Set `AWS_S3_CUSTOM_DOMAIN` to your CloudFront domain:

```env
AWS_S3_CUSTOM_DOMAIN=d1234567890.cloudfront.net
```

---

## Troubleshooting

### Image upload fails with "Failed to save profile image"

1. Check backend logs: `docker-compose logs backend`
2. Verify AWS credentials are correct
3. Verify S3 bucket exists and is accessible
4. Check IAM user has required permissions

### Images not displaying (403 Forbidden)

1. Verify bucket policy allows public read access
2. Check that ACLs are enabled on the bucket
3. Verify the `public-read` ACL is being set on uploaded objects

### boto3 import error

1. Ensure `boto3` is in `requirements.txt`
2. Rebuild the container: `docker-compose up -d --build`

---

## Security Best Practices

1. **Never commit credentials** - Keep `.env` in `.gitignore`
2. **Use IAM roles** in production (EC2/ECS) instead of access keys when possible
3. **Restrict bucket policy** to only the `profile-images/` prefix
4. **Enable S3 versioning** for backup/recovery
5. **Enable CloudTrail** for audit logging
6. **Rotate access keys** periodically

---

## File Structure

```
backend/
├── app/
│   ├── config.py              # S3 configuration settings
│   ├── services/
│   │   └── storage_service.py # Storage abstraction (local/S3)
│   └── api/
│       └── auth_endpoints.py  # Profile update endpoint
├── uploads/
│   └── profile/               # Local storage (development only)
└── requirements.txt           # boto3 dependency
```

---

## Related Files

- `backend/app/services/storage_service.py` - Storage service implementation
- `backend/app/config.py` - Configuration with S3 settings
- `docker-compose.yml` - Docker environment configuration
- `.env` - Environment variables (not in git)
