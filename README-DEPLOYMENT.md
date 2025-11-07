# CloudSense Deployment Guide

This guide covers deploying CloudSense to AWS.

## Architecture

- **Frontend**: React app deployed to S3 + CloudFront
- **Backend**: FastAPI app deployed to ECS Fargate
- **Database**: SQLite (local) or RDS PostgreSQL (production)
- **Cache**: Redis via ElastiCache (production)

## Prerequisites

1. AWS CLI configured
2. Terraform installed (for infrastructure)
3. Docker installed (for building images)
4. Node.js and npm (for frontend build)

## Deployment Steps

### 1. Infrastructure Setup (Terraform)

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### 2. Build and Push Backend Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t cloudsense-backend .
docker tag cloudsense-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudsense-backend:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/cloudsense-backend:latest
```

### 3. Build and Deploy Frontend

```bash
cd frontend
npm install
npm run build

# Deploy to S3
aws s3 sync dist/ s3://cloudsense-production-frontend --delete

# Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

### 4. Environment Variables

Set the following environment variables in your ECS task definition:

- `GITHUB_TOKEN`: GitHub API token
- `OPENAI_API_KEY`: OpenAI API key
- `GH_WEBHOOK_SECRET`: GitHub webhook secret
- `REDIS_HOST`: Redis host (ElastiCache endpoint)
- `REDIS_PORT`: Redis port (default 6379)
- `DB_PATH`: Database path (for SQLite) or use RDS connection string

## CI/CD

GitHub Actions workflow is configured in `.github/workflows/deploy.yml`.

Required secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `CLOUDFRONT_DISTRIBUTION_ID`
- `VITE_API_URL`

## Local Development

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run with uvicorn
uvicorn app.web:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will proxy API requests to `http://localhost:8000/api`.

## Production Considerations

1. **Database**: Migrate from SQLite to RDS PostgreSQL for production
2. **Redis**: Use ElastiCache instead of local Redis
3. **CORS**: Update CORS origins in `app/web.py` to only allow your frontend domain
4. **Secrets**: Use AWS Secrets Manager or Parameter Store
5. **Monitoring**: Set up CloudWatch alarms and logging
6. **SSL**: Configure custom domain with ACM certificate for CloudFront

