# AWS-Ready Implementation Considerations

## Design Principles for AWS Migration

### 1. Database Compatibility
- ✅ Use standard SQL (no SQLite-specific features)
- ✅ Parameterized queries (already doing this)
- ✅ Avoid SQLite-specific functions
- ✅ Use migrations that work with PostgreSQL
- ✅ Design for connection pooling (RDS)

### 2. Stateless Architecture
- ✅ JWT tokens (no server-side sessions)
- ✅ No file-based storage (use S3 for future)
- ✅ Environment variables for config (AWS Secrets Manager compatible)

### 3. Scalability
- ✅ Stateless API (can scale horizontally)
- ✅ No shared state between instances
- ✅ Redis for job queue (already using, works with ElastiCache)

### 4. Security
- ✅ Secrets in environment variables (not hardcoded)
- ✅ JWT secrets configurable via env vars
- ✅ Password hashing (bcrypt) - works anywhere

### 5. Future AWS Services
- **RDS PostgreSQL** - Replace SQLite (same SQL, just change connection)
- **ElastiCache Redis** - Already using Redis
- **S3** - For file storage (if needed later)
- **Secrets Manager** - For API keys, JWT secrets
- **Cognito** - Optional: Could replace custom auth later
- **API Gateway + Lambda** - Optional: Could migrate to serverless

## Implementation Strategy

### Phase 1: Current (SQLite)
- Use standard SQL only
- Environment variables for all secrets
- JWT tokens (stateless)
- Ready for PostgreSQL migration

### Phase 2: AWS Migration
- Change database connection string
- Update Redis connection (ElastiCache)
- Deploy to ECS/App Runner
- Use Secrets Manager for env vars

### No Breaking Changes
- Same API structure
- Same authentication flow
- Same data models
- Just change connection strings

## Code Structure

```python
# Database connection - abstracted
DB_PATH = os.getenv("DB_PATH")  # SQLite for now
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL later

# JWT secret - from env
JWT_SECRET = os.getenv("JWT_SECRET")  # AWS Secrets Manager later

# Redis - already using env vars
REDIS_HOST = os.getenv("REDIS_HOST")  # ElastiCache later
```

## Migration Path

1. **Now**: SQLite + local Redis
2. **AWS Dev**: RDS PostgreSQL + ElastiCache
3. **AWS Prod**: Same, with Secrets Manager

No code changes needed, just environment variables!

