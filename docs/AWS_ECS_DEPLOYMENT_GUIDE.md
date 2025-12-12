# AWS ECS Deployment Guide - Pixel Perfect UI

Complete step-by-step guide to deploy the full Pixel Perfect UI system on AWS using:
- **Amazon ECS** (Elastic Container Service) for containerized backend & frontend
- **Amazon RDS** (PostgreSQL) for database
- **Amazon S3** for profile image storage
- **Amazon ECR** (Elastic Container Registry) for Docker images
- **Application Load Balancer** for traffic routing
- **Amazon CloudWatch** for logging

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Step 1: Create S3 Bucket](#step-1-create-s3-bucket)
4. [Step 2: Create RDS PostgreSQL Database](#step-2-create-rds-postgresql-database)
5. [Step 3: Create ECR Repositories](#step-3-create-ecr-repositories)
6. [Step 4: Build and Push Docker Images](#step-4-build-and-push-docker-images)
7. [Step 5: Create ECS Cluster](#step-5-create-ecs-cluster)
8. [Step 6: Create Task Definitions](#step-6-create-task-definitions)
9. [Step 7: Create Application Load Balancer](#step-7-create-application-load-balancer)
10. [Step 8: Create ECS Services](#step-8-create-ecs-services)
11. [Step 9: Configure Environment Variables](#step-9-configure-environment-variables)
12. [Step 10: DNS and SSL Setup](#step-10-dns-and-ssl-setup)
13. [Monitoring and Logging](#monitoring-and-logging)
14. [Troubleshooting](#troubleshooting)
15. [Cost Optimization](#cost-optimization)

---

## Prerequisites

Before starting, ensure you have:

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Docker installed locally
- [ ] Domain name (optional, for custom domain)
- [ ] Git repository access

### Install AWS CLI

```bash
# Windows (PowerShell)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Configure AWS CLI

```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: ap-southeast-1 (or your preferred region)
# - Default output format: json
```

---

## Architecture Overview

```
                                    ┌─────────────────────────────────────────────────────────┐
                                    │                        AWS Cloud                         │
                                    │                                                          │
    Users ──────────────────────────┼──► Application Load Balancer                             │
                                    │           │                                              │
                                    │     ┌─────┴─────┐                                        │
                                    │     │           │                                        │
                                    │     ▼           ▼                                        │
                                    │  ┌──────┐   ┌──────────┐                                 │
                                    │  │ ECS  │   │   ECS    │                                 │
                                    │  │Front │   │ Backend  │──────► Amazon RDS (PostgreSQL) │
                                    │  │ end  │   │          │                                 │
                                    │  └──────┘   └────┬─────┘                                 │
                                    │                  │                                       │
                                    │                  ▼                                       │
                                    │            Amazon S3 (Profile Images)                    │
                                    │                                                          │
                                    │  ┌──────────────────────────────────┐                    │
                                    │  │ Amazon ECR (Docker Images)       │                    │
                                    │  │ - pixelperfect-frontend          │                    │
                                    │  │ - pixelperfect-backend           │                    │
                                    │  └──────────────────────────────────┘                    │
                                    └─────────────────────────────────────────────────────────┘
```

---

## Step 1: Create S3 Bucket

### 1.1 Create Bucket for Profile Images

```bash
# Create S3 bucket (bucket names must be globally unique)
aws s3 mb s3://pixelperfectui-profile-images-prod --region ap-southeast-1

# Enable public access for profile images
aws s3api put-public-access-block \
    --bucket pixelperfectui-profile-images-prod \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"
```

### 1.2 Add Bucket Policy

Create `bucket-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::pixelperfectui-profile-images-prod/profile-images/*"
        }
    ]
}
```

Apply the policy:

```bash
aws s3api put-bucket-policy \
    --bucket pixelperfectui-profile-images-prod \
    --policy file://bucket-policy.json
```

### 1.3 Enable CORS (for frontend uploads)

Create `cors-config.json`:

```json
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST"],
            "AllowedOrigins": ["*"],
            "ExposeHeaders": ["ETag"]
        }
    ]
}
```

Apply CORS:

```bash
aws s3api put-bucket-cors \
    --bucket pixelperfectui-profile-images-prod \
    --cors-configuration file://cors-config.json
```

---

## Step 2: Create RDS PostgreSQL Database

### 2.1 Create DB Subnet Group

First, identify your VPC and subnets:

```bash
# Get default VPC ID
aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text

# Get subnet IDs (need at least 2 in different AZs)
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<VPC_ID>" --query "Subnets[*].[SubnetId,AvailabilityZone]" --output table
```

Create subnet group:

```bash
aws rds create-db-subnet-group \
    --db-subnet-group-name pixelperfect-db-subnet \
    --db-subnet-group-description "Subnet group for Pixel Perfect UI database" \
    --subnet-ids subnet-xxxxx subnet-yyyyy
```

### 2.2 Create Security Group for RDS

```bash
# Create security group
aws ec2 create-security-group \
    --group-name pixelperfect-rds-sg \
    --description "Security group for Pixel Perfect RDS" \
    --vpc-id <VPC_ID>

# Note the SecurityGroupId returned, then allow PostgreSQL access
aws ec2 authorize-security-group-ingress \
    --group-id <RDS_SECURITY_GROUP_ID> \
    --protocol tcp \
    --port 5432 \
    --cidr 10.0.0.0/8
```

### 2.3 Create RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
    --db-instance-identifier pixelperfect-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 16.1 \
    --master-username postgres \
    --master-user-password "YourSecurePassword123!" \
    --allocated-storage 20 \
    --storage-type gp3 \
    --db-subnet-group-name pixelperfect-db-subnet \
    --vpc-security-group-ids <RDS_SECURITY_GROUP_ID> \
    --db-name pixel_perfect_ui \
    --backup-retention-period 7 \
    --no-publicly-accessible \
    --storage-encrypted
```

### 2.4 Wait for RDS to be Available

```bash
# Check status (wait until "available")
aws rds describe-db-instances \
    --db-instance-identifier pixelperfect-db \
    --query "DBInstances[0].DBInstanceStatus"

# Get the endpoint (save this for later)
aws rds describe-db-instances \
    --db-instance-identifier pixelperfect-db \
    --query "DBInstances[0].Endpoint.Address" \
    --output text
```

**Save the RDS endpoint** - you'll need it for the backend configuration.

---

## Step 3: Create ECR Repositories

### 3.1 Create Repositories for Frontend and Backend

```bash
# Create backend repository
aws ecr create-repository \
    --repository-name pixelperfect-backend \
    --image-scanning-configuration scanOnPush=true

# Create frontend repository
aws ecr create-repository \
    --repository-name pixelperfect-frontend \
    --image-scanning-configuration scanOnPush=true
```

### 3.2 Get ECR Login

```bash
# Login to ECR
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com
```

Replace `<ACCOUNT_ID>` with your AWS account ID:

```bash
aws sts get-caller-identity --query "Account" --output text
```

---

## Step 4: Build and Push Docker Images

### 4.1 Create Production Dockerfile for Frontend

Create `frontend/Dockerfile.prod`:

```dockerfile
# Build stage
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 4.2 Create Nginx Config for Frontend

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Handle React Router
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Proxy uploads requests to backend
    location /uploads {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Proxy static requests to backend
    location /static {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

### 4.3 Create Production Dockerfile for Backend

Create `backend/Dockerfile.prod`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Create directories
RUN mkdir -p uploads outputs static

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.4 Build and Push Images

```bash
# Set variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export AWS_REGION=ap-southeast-1
export ECR_URL=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

# Build and push backend
cd backend
docker build -f Dockerfile.prod -t pixelperfect-backend:latest .
docker tag pixelperfect-backend:latest $ECR_URL/pixelperfect-backend:latest
docker push $ECR_URL/pixelperfect-backend:latest

# Build and push frontend
cd ../frontend
docker build -f Dockerfile.prod -t pixelperfect-frontend:latest .
docker tag pixelperfect-frontend:latest $ECR_URL/pixelperfect-frontend:latest
docker push $ECR_URL/pixelperfect-frontend:latest
```

---

## Step 5: Create ECS Cluster

### 5.1 Create ECS Cluster

```bash
aws ecs create-cluster \
    --cluster-name pixelperfect-cluster \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1,base=1 \
        capacityProvider=FARGATE_SPOT,weight=4
```

### 5.2 Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/pixelperfect-backend
aws logs create-log-group --log-group-name /ecs/pixelperfect-frontend
```

---

## Step 6: Create Task Definitions

### 6.1 Create IAM Role for ECS Tasks

Create `ecs-task-trust-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

Create the role:

```bash
# Create task execution role
aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file://ecs-task-trust-policy.json

# Attach managed policy
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create task role (for S3 access)
aws iam create-role \
    --role-name pixelperfectTaskRole \
    --assume-role-policy-document file://ecs-task-trust-policy.json
```

Create S3 access policy `s3-access-policy.json`:

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
            "Resource": "arn:aws:s3:::pixelperfectui-profile-images-prod/*"
        }
    ]
}
```

Attach S3 policy:

```bash
aws iam put-role-policy \
    --role-name pixelperfectTaskRole \
    --policy-name S3AccessPolicy \
    --policy-document file://s3-access-policy.json
```

### 6.2 Create Backend Task Definition

Create `backend-task-definition.json`:

```json
{
    "family": "pixelperfect-backend",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "512",
    "memory": "1024",
    "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
    "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/pixelperfectTaskRole",
    "containerDefinitions": [
        {
            "name": "backend",
            "image": "<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/pixelperfect-backend:latest",
            "essential": true,
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {"name": "DEBUG", "value": "False"},
                {"name": "ENVIRONMENT", "value": "production"},
                {"name": "API_V1_PREFIX", "value": "/api/v1"},
                {"name": "AWS_REGION", "value": "ap-southeast-1"},
                {"name": "AWS_S3_BUCKET", "value": "pixelperfectui-profile-images-prod"}
            ],
            "secrets": [
                {
                    "name": "DATABASE_URL",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/database-url"
                },
                {
                    "name": "SMTP_HOST",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/smtp-host"
                },
                {
                    "name": "SMTP_PORT",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/smtp-port"
                },
                {
                    "name": "SMTP_USER",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/smtp-user"
                },
                {
                    "name": "SMTP_PASSWORD",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/smtp-password"
                },
                {
                    "name": "SENDER_EMAIL",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/sender-email"
                },
                {
                    "name": "FIGMA_CLIENT_ID",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/figma-client-id"
                },
                {
                    "name": "FIGMA_CLIENT_SECRET",
                    "valueFrom": "arn:aws:ssm:ap-southeast-1:<ACCOUNT_ID>:parameter/pixelperfect/figma-client-secret"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/pixelperfect-backend",
                    "awslogs-region": "ap-southeast-1",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 60
            }
        }
    ]
}
```

### 6.3 Create Frontend Task Definition

Create `frontend-task-definition.json`:

```json
{
    "family": "pixelperfect-frontend",
    "networkMode": "awsvpc",
    "requiresCompatibilities": ["FARGATE"],
    "cpu": "256",
    "memory": "512",
    "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
    "containerDefinitions": [
        {
            "name": "frontend",
            "image": "<ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/pixelperfect-frontend:latest",
            "essential": true,
            "portMappings": [
                {
                    "containerPort": 80,
                    "protocol": "tcp"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/pixelperfect-frontend",
                    "awslogs-region": "ap-southeast-1",
                    "awslogs-stream-prefix": "ecs"
                }
            },
            "healthCheck": {
                "command": ["CMD-SHELL", "curl -f http://localhost/health || exit 1"],
                "interval": 30,
                "timeout": 5,
                "retries": 3,
                "startPeriod": 10
            }
        }
    ]
}
```

### 6.4 Register Task Definitions

```bash
# Replace <ACCOUNT_ID> in the JSON files first, then:
aws ecs register-task-definition --cli-input-json file://backend-task-definition.json
aws ecs register-task-definition --cli-input-json file://frontend-task-definition.json
```

---

## Step 7: Create Application Load Balancer

### 7.1 Create Security Groups

```bash
# ALB Security Group (allow HTTP/HTTPS from internet)
aws ec2 create-security-group \
    --group-name pixelperfect-alb-sg \
    --description "Security group for Pixel Perfect ALB" \
    --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress \
    --group-id <ALB_SG_ID> \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id <ALB_SG_ID> \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# ECS Tasks Security Group (allow traffic from ALB)
aws ec2 create-security-group \
    --group-name pixelperfect-ecs-sg \
    --description "Security group for Pixel Perfect ECS tasks" \
    --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress \
    --group-id <ECS_SG_ID> \
    --protocol tcp \
    --port 8000 \
    --source-group <ALB_SG_ID>

aws ec2 authorize-security-group-ingress \
    --group-id <ECS_SG_ID> \
    --protocol tcp \
    --port 80 \
    --source-group <ALB_SG_ID>

# Allow ECS to access RDS
aws ec2 authorize-security-group-ingress \
    --group-id <RDS_SG_ID> \
    --protocol tcp \
    --port 5432 \
    --source-group <ECS_SG_ID>
```

### 7.2 Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
    --name pixelperfect-alb \
    --subnets subnet-xxxxx subnet-yyyyy \
    --security-groups <ALB_SG_ID> \
    --scheme internet-facing \
    --type application

# Note the ALB ARN and DNS name returned
```

### 7.3 Create Target Groups

```bash
# Backend target group
aws elbv2 create-target-group \
    --name pixelperfect-backend-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id <VPC_ID> \
    --target-type ip \
    --health-check-path /api/v1/health \
    --health-check-interval-seconds 30

# Frontend target group
aws elbv2 create-target-group \
    --name pixelperfect-frontend-tg \
    --protocol HTTP \
    --port 80 \
    --vpc-id <VPC_ID> \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30
```

### 7.4 Create Listeners and Rules

```bash
# Create HTTP listener (redirects to HTTPS in production)
aws elbv2 create-listener \
    --load-balancer-arn <ALB_ARN> \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=<FRONTEND_TG_ARN>

# Add rule for /api/* to route to backend
aws elbv2 create-rule \
    --listener-arn <LISTENER_ARN> \
    --priority 10 \
    --conditions Field=path-pattern,Values='/api/*' \
    --actions Type=forward,TargetGroupArn=<BACKEND_TG_ARN>

# Add rule for /uploads/* to route to backend
aws elbv2 create-rule \
    --listener-arn <LISTENER_ARN> \
    --priority 20 \
    --conditions Field=path-pattern,Values='/uploads/*' \
    --actions Type=forward,TargetGroupArn=<BACKEND_TG_ARN>

# Add rule for /static/* to route to backend
aws elbv2 create-rule \
    --listener-arn <LISTENER_ARN> \
    --priority 30 \
    --conditions Field=path-pattern,Values='/static/*' \
    --actions Type=forward,TargetGroupArn=<BACKEND_TG_ARN>
```

---

## Step 8: Create ECS Services

### 8.1 Create Backend Service

```bash
aws ecs create-service \
    --cluster pixelperfect-cluster \
    --service-name pixelperfect-backend \
    --task-definition pixelperfect-backend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx,subnet-yyyyy],securityGroups=[<ECS_SG_ID>],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=<BACKEND_TG_ARN>,containerName=backend,containerPort=8000" \
    --health-check-grace-period-seconds 120
```

### 8.2 Create Frontend Service

```bash
aws ecs create-service \
    --cluster pixelperfect-cluster \
    --service-name pixelperfect-frontend \
    --task-definition pixelperfect-frontend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx,subnet-yyyyy],securityGroups=[<ECS_SG_ID>],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=<FRONTEND_TG_ARN>,containerName=frontend,containerPort=80" \
    --health-check-grace-period-seconds 60
```

---

## Step 9: Configure Environment Variables

### 9.1 Store Secrets in AWS Systems Manager Parameter Store

```bash
# Database URL
aws ssm put-parameter \
    --name "/pixelperfect/database-url" \
    --value "postgresql://postgres:YourSecurePassword123!@<RDS_ENDPOINT>:5432/pixel_perfect_ui" \
    --type SecureString

# SMTP Configuration
aws ssm put-parameter --name "/pixelperfect/smtp-host" --value "email-smtp.ap-southeast-1.amazonaws.com" --type SecureString
aws ssm put-parameter --name "/pixelperfect/smtp-port" --value "587" --type String
aws ssm put-parameter --name "/pixelperfect/smtp-user" --value "YOUR_SMTP_USER" --type SecureString
aws ssm put-parameter --name "/pixelperfect/smtp-password" --value "YOUR_SMTP_PASSWORD" --type SecureString
aws ssm put-parameter --name "/pixelperfect/sender-email" --value "no-reply@yourdomain.com" --type String

# Figma OAuth
aws ssm put-parameter --name "/pixelperfect/figma-client-id" --value "YOUR_FIGMA_CLIENT_ID" --type SecureString
aws ssm put-parameter --name "/pixelperfect/figma-client-secret" --value "YOUR_FIGMA_CLIENT_SECRET" --type SecureString
```

### 9.2 Grant ECS Task Execution Role Access to SSM

```bash
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

---

## Step 10: DNS and SSL Setup

### 10.1 Request SSL Certificate (AWS Certificate Manager)

```bash
aws acm request-certificate \
    --domain-name pixelperfectui.yourdomain.com \
    --validation-method DNS \
    --region ap-southeast-1
```

Validate the certificate by adding the DNS records shown in ACM console.

### 10.2 Add HTTPS Listener

```bash
aws elbv2 create-listener \
    --load-balancer-arn <ALB_ARN> \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=<ACM_CERTIFICATE_ARN> \
    --default-actions Type=forward,TargetGroupArn=<FRONTEND_TG_ARN>

# Add same routing rules as HTTP listener
```

### 10.3 Redirect HTTP to HTTPS

```bash
# Modify HTTP listener to redirect
aws elbv2 modify-listener \
    --listener-arn <HTTP_LISTENER_ARN> \
    --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"
```

### 10.4 Configure DNS (Route 53 or your DNS provider)

Create an A record (alias) pointing to the ALB DNS name:
- **Name**: pixelperfectui.yourdomain.com
- **Type**: A (Alias)
- **Value**: <ALB_DNS_NAME>

---

## Monitoring and Logging

### CloudWatch Dashboards

```bash
# View backend logs
aws logs tail /ecs/pixelperfect-backend --follow

# View frontend logs
aws logs tail /ecs/pixelperfect-frontend --follow
```

### Set Up Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
    --alarm-name pixelperfect-backend-cpu-high \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ClusterName,Value=pixelperfect-cluster Name=ServiceName,Value=pixelperfect-backend \
    --evaluation-periods 2 \
    --alarm-actions <SNS_TOPIC_ARN>
```

---

## Troubleshooting

### Common Issues

#### 1. Tasks failing to start
```bash
# Check task stopped reason
aws ecs describe-tasks \
    --cluster pixelperfect-cluster \
    --tasks <TASK_ARN> \
    --query "tasks[0].stoppedReason"

# Check CloudWatch logs
aws logs tail /ecs/pixelperfect-backend --since 1h
```

#### 2. Database connection issues
- Verify RDS security group allows traffic from ECS security group
- Check DATABASE_URL parameter is correct
- Ensure RDS is in the same VPC as ECS tasks

#### 3. Health check failures
- Verify health check endpoints are correct
- Check container logs for startup errors
- Increase health check grace period

#### 4. S3 upload failures
- Verify task role has S3 permissions
- Check bucket policy allows PutObject
- Verify ENVIRONMENT=production is set

### Useful Commands

```bash
# List running tasks
aws ecs list-tasks --cluster pixelperfect-cluster --service-name pixelperfect-backend

# Force new deployment
aws ecs update-service --cluster pixelperfect-cluster --service pixelperfect-backend --force-new-deployment

# Scale service
aws ecs update-service --cluster pixelperfect-cluster --service pixelperfect-backend --desired-count 3

# View service events
aws ecs describe-services --cluster pixelperfect-cluster --services pixelperfect-backend --query "services[0].events[:10]"
```

---

## Cost Optimization

### Estimated Monthly Costs (ap-southeast-1)

| Service | Configuration | Est. Cost/Month |
|---------|--------------|-----------------|
| ECS Fargate (Backend) | 2 tasks × 0.5 vCPU × 1GB | ~$30 |
| ECS Fargate (Frontend) | 2 tasks × 0.25 vCPU × 0.5GB | ~$15 |
| RDS PostgreSQL | db.t3.micro, 20GB | ~$15 |
| ALB | 1 ALB + data transfer | ~$20 |
| S3 | Storage + requests | ~$5 |
| CloudWatch | Logs + metrics | ~$5 |
| **Total** | | **~$90/month** |

### Cost Saving Tips

1. **Use Fargate Spot** for non-critical workloads (up to 70% savings)
2. **Reserved Instances** for RDS (up to 40% savings)
3. **Right-size** containers based on actual usage
4. **Set up auto-scaling** to scale down during low traffic
5. **Use S3 Intelligent-Tiering** for infrequently accessed files

---

## CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS ECS

on:
  push:
    branches: [main]

env:
  AWS_REGION: ap-southeast-1
  ECR_REPOSITORY_BACKEND: pixelperfect-backend
  ECR_REPOSITORY_FRONTEND: pixelperfect-frontend
  ECS_CLUSTER: pixelperfect-cluster

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push backend
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          cd backend
          docker build -f Dockerfile.prod -t $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:${{ github.sha }} .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:${{ github.sha }}
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:${{ github.sha }} $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND:latest
      
      - name: Build and push frontend
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          cd frontend
          docker build -f Dockerfile.prod -t $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:${{ github.sha }} .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:${{ github.sha }}
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:${{ github.sha }} $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND:latest
      
      - name: Deploy backend to ECS
        run: |
          aws ecs update-service --cluster $ECS_CLUSTER --service pixelperfect-backend --force-new-deployment
      
      - name: Deploy frontend to ECS
        run: |
          aws ecs update-service --cluster $ECS_CLUSTER --service pixelperfect-frontend --force-new-deployment
```

---

## Quick Reference - All Resources Created

| Resource | Name/ID | Purpose |
|----------|---------|---------|
| S3 Bucket | pixelperfectui-profile-images-prod | Profile image storage |
| RDS Instance | pixelperfect-db | PostgreSQL database |
| ECR Repository | pixelperfect-backend | Backend Docker images |
| ECR Repository | pixelperfect-frontend | Frontend Docker images |
| ECS Cluster | pixelperfect-cluster | Container orchestration |
| ECS Service | pixelperfect-backend | Backend containers |
| ECS Service | pixelperfect-frontend | Frontend containers |
| ALB | pixelperfect-alb | Load balancing |
| Target Group | pixelperfect-backend-tg | Backend routing |
| Target Group | pixelperfect-frontend-tg | Frontend routing |

---

## Support

For issues or questions:
1. Check CloudWatch logs first
2. Review ECS service events
3. Verify security group rules
4. Check RDS connectivity

**Document Version**: 1.0  
**Last Updated**: December 2024
