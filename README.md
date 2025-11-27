# CodeSense

**Automated AI-Powered Code Review System**

DTSC-5253 Data Scale Computing - Final Project

---

## 👥 Team Members

- Atharva Patil
- Mihir Chauhan

---

## 📋 Project Overview

CodeSense is a serverless, event-driven code review platform that automatically analyzes GitHub pull requests using OpenAI's GPT-4. When developers push code to GitHub, webhooks trigger our AWS Lambda-based system to queue review jobs, analyze code changes, and provide intelligent feedback on code quality, security issues, and best practices.

### Key Features

- **Automated Code Reviews**: AI-powered analysis using OpenAI GPT-4o-mini
- **GitHub Integration**: Real-time webhook-based event processing
- **Serverless Architecture**: AWS Lambda for scalable, cost-effective compute
- **Event-Driven Processing**: SQS queue for reliable asynchronous job processing
- **Web Dashboard**: React-based frontend for viewing reviews and findings
- **User Authentication**: JWT-based secure authentication system

---

## 🏗️ Architecture

![Architecture Diagram](architecture-diagram.png)

### System Components

```
GitHub → API Gateway → Lambda (API) → RDS PostgreSQL
                           ↓
                       SQS Queue
                           ↓
                  Lambda (Worker) → OpenAI API
                           ↓
                    Store Findings
```

**AWS Services Used:**

- **AWS Lambda**: Serverless compute (API handler + Worker processor)
- **API Gateway**: HTTP API v2 for webhook and REST endpoints
- **RDS PostgreSQL**: Relational database for events, reviews, and findings
- **SQS**: Message queue for decoupled asynchronous processing
- **S3**: Static website hosting for React frontend
- **VPC**: Private networking for secure database access
- **CloudWatch**: Logging and monitoring

**External APIs:**

- **GitHub API**: Webhook delivery, repository access, code comparison
- **OpenAI API**: GPT-4o-mini for intelligent code analysis

---

## 📊 Database Schema

**Tables:**

- `users` - User accounts with hashed passwords
- `repositories` - Connected GitHub repositories with webhook secrets
- `events` - GitHub push events (commits, branches, timestamps)
- `reviews` - Review jobs with status tracking
- `findings` - Individual code issues identified by AI
- `deliveries` - Webhook delivery tracking

---

## 🚀 Deployment Instructions

### Prerequisites

- AWS Account with appropriate permissions
- GitHub account with repository access
- OpenAI API key
- Docker installed (for Lambda deployment)
- AWS CLI configured
- Python 3.11+
- Node.js 18+ (for frontend)

### Environment Variables

**Backend (Lambda):**

```bash
DATABASE_URL=postgresql://username:password@host:5432/dbname
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
SECRET_KEY=your-jwt-secret-key
REVIEW_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/.../cloudsense-review-queue
GITHUB_TOKEN=ghp_...
```

**Frontend:**

```bash
VITE_API_URL=https://your-api-gateway-id.execute-api.us-east-1.amazonaws.com/production
```

### Step 1: Deploy Database

```bash
# Create RDS PostgreSQL instance (db.t3.micro recommended)
aws rds create-db-instance \
  --db-instance-identifier cloudsense-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password YOUR_PASSWORD \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-XXXXXXXX

# Run database migrations
python app/database.py
```

### Step 2: Create SQS Queue

```bash
aws sqs create-queue \
  --queue-name cloudsense-review-queue \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=345600
```

### Step 3: Deploy Lambda Functions

**Build Lambda package (using Docker for Linux compatibility):**

```bash
# Build dependencies
docker run --rm --entrypoint pip \
  -v "${PWD}/build/api-lambda:/var/task" \
  -v "${PWD}/requirements-lambda.txt:/tmp/requirements.txt" \
  public.ecr.aws/lambda/python:3.11 \
  install -r /tmp/requirements.txt -t /var/task

# Copy application code
cp -r app build/api-lambda/
```

**Deploy API Lambda:**

```bash
aws lambda create-function \
  --function-name cloudsense-api \
  --runtime python3.11 \
  --handler app.lambda_handler.lambda_handler \
  --role arn:aws:iam::ACCOUNT:role/cloudsense-lambda-exec \
  --memory-size 512 \
  --timeout 60 \
  --zip-file fileb://lambda-package.zip \
  --environment Variables="{DATABASE_URL=...,SECRET_KEY=...,GITHUB_TOKEN=...}"
```

**Deploy Worker Lambda:**

```bash
aws lambda create-function \
  --function-name cloudsense-worker \
  --runtime python3.11 \
  --handler app.lambda_worker.lambda_handler \
  --role arn:aws:iam::ACCOUNT:role/cloudsense-lambda-exec \
  --memory-size 1024 \
  --timeout 300 \
  --zip-file fileb://lambda-package.zip \
  --environment Variables="{DATABASE_URL=...,OPENAI_API_KEY=...,OPENAI_MODEL=gpt-4o-mini}"

# Create SQS event source mapping
aws lambda create-event-source-mapping \
  --function-name cloudsense-worker \
  --event-source-arn arn:aws:sqs:us-east-1:ACCOUNT:cloudsense-review-queue \
  --batch-size 1
```

### Step 4: Configure API Gateway

```bash
# Create HTTP API
aws apigatewayv2 create-api \
  --name cloudsense-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:ACCOUNT:function:cloudsense-api

# Add routes
aws apigatewayv2 create-route \
  --api-id API_ID \
  --route-key 'POST /webhook/{secret}'

aws apigatewayv2 create-route \
  --api-id API_ID \
  --route-key 'ANY /api/{proxy+}'
```

### Step 5: Deploy Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set production API URL
echo "VITE_API_URL=https://API_ID.execute-api.us-east-1.amazonaws.com/production" > .env.production

# Build
npm run build

# Deploy to S3
aws s3 sync dist/ s3://cloudsense-frontend/

# Configure S3 for SPA routing
aws s3api put-bucket-website \
  --bucket cloudsense-frontend \
  --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"index.html"}}'
```

### Step 6: Configure GitHub Webhooks

1. Go to your GitHub repository → Settings → Webhooks
2. Add webhook:
   - **Payload URL**: `https://API_ID.execute-api.us-east-1.amazonaws.com/production/webhook/YOUR_UNIQUE_SECRET`
   - **Content type**: `application/json`
   - **Events**: Push events
   - **Active**: ✓

---

## 💻 Local Development

### Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your values

# Run local server
python -m uvicorn app.web:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set development API URL
echo "VITE_API_URL=http://localhost:8000" > .env.development

# Run dev server
npm run dev
```

### Using Docker Compose

```bash
# Start all services (API + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 🧪 Testing

### Manual Testing

```bash
# Test webhook endpoint
.\test-review-flow.ps1

# Check reviews in database
.\check-reviews.ps1
```

### End-to-End Testing

1. Make a commit to connected GitHub repository
2. Verify webhook delivery in GitHub (green checkmark)
3. Check CloudWatch logs: `aws logs tail /aws/lambda/cloudsense-api --follow`
4. Verify event created in database
5. Check SQS queue for message
6. Monitor worker Lambda processing
7. View findings in web dashboard

---

## 📈 Monitoring

**CloudWatch Logs:**

```bash
# API Lambda logs
aws logs tail /aws/lambda/cloudsense-api --follow

# Worker Lambda logs
aws logs tail /aws/lambda/cloudsense-worker --follow
```

**SQS Queue Monitoring:**

```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT/cloudsense-review-queue \
  --attribute-names All
```

**Lambda Metrics:**

- Invocations, duration, errors, throttles available in CloudWatch

---

## 💰 Cost Estimate

Monthly cost for moderate usage (~1000 reviews/month):

- **Lambda**: ~$2-3 (512MB API + 1024MB Worker)
- **API Gateway**: ~$1-2 (HTTP API requests)
- **RDS**: ~$10-12 (db.t3.micro with 20GB storage)
- **SQS**: ~$0.50 (1M requests free tier)
- **S3**: ~$0.50 (frontend hosting)
- **CloudWatch**: ~$0.50 (logs)

**Total: ~$15-18/month**

---

## 🔐 Security Considerations

- JWT-based authentication for API endpoints
- GitHub webhook signature validation
- Unique webhook secrets per repository
- Database credentials in environment variables (never committed)
- VPC isolation for RDS database
- IAM least-privilege permissions for Lambda

---

## 🐛 Known Limitations

- Large commits (>50 files) may timeout due to Lambda 300s limit
- OpenAI API rate limits may cause delays during high traffic
- Database transactions require explicit commits in Lambda environment
- Cross-platform Python dependency builds need Docker

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- Course: DTSC-5253 Data Scale Computing, University of Colorado Boulder
- Instructor: Dr. Michael Elgood
- Technologies: AWS, OpenAI, GitHub, FastAPI, React, PostgreSQL
