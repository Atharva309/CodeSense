# User Authentication & Repository Management Plan

## Overview
Transform CloudSense from a single-instance service to a multi-tenant SaaS platform where users can:
- Sign up and log in
- Connect their GitHub repositories
- Get unique webhook URLs for each repo
- View reviews only for their connected repositories

## Architecture Design

### 1. Database Schema Changes

#### New Tables

**users**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    is_active BOOLEAN DEFAULT 1
)
```

**repositories**
```sql
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    repo_full_name TEXT NOT NULL,  -- e.g., "username/repo-name"
    webhook_secret TEXT NOT NULL,   -- Unique secret per repo
    webhook_url TEXT,                -- Generated webhook URL
    github_token TEXT,               -- Optional: user's GitHub token for private repos
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id),
    UNIQUE(user_id, repo_full_name)
)
```

**Modified Tables**

**events** - Add `user_id` and `repository_id`
```sql
ALTER TABLE events ADD COLUMN user_id INTEGER;
ALTER TABLE events ADD COLUMN repository_id INTEGER;
ALTER TABLE events ADD FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE events ADD FOREIGN KEY (repository_id) REFERENCES repositories(id);
```

### 2. Authentication System

#### Technology Choice
- **JWT (JSON Web Tokens)** for stateless authentication
- **bcrypt** for password hashing
- **python-jose** for JWT encoding/decoding

#### Flow
1. User signs up → Password hashed with bcrypt → User created
2. User logs in → Password verified → JWT token issued
3. Frontend stores JWT in localStorage/sessionStorage
4. All API requests include JWT in Authorization header
5. Backend validates JWT and extracts user_id

### 3. Webhook Management

#### Current: Single webhook endpoint
```
POST /webhook
```

#### New: Per-repository webhook URLs
```
POST /webhook/{webhook_secret}
```

**Benefits:**
- Each repository gets unique webhook URL
- Webhook secret identifies which repo/user
- More secure (can't guess other users' webhooks)
- Easy to revoke (just deactivate repository)

**Webhook URL Format:**
```
https://yourdomain.com/webhook/{webhook_secret}
```

Where `webhook_secret` is a UUID or random string stored in `repositories` table.

### 4. Authorization & Data Isolation

#### API Changes
- All event/review queries filtered by `user_id`
- Users can only see their own repositories
- Webhook handler looks up repository by `webhook_secret`

#### Example Query Changes
```python
# Before
SELECT * FROM events ORDER BY id DESC

# After
SELECT * FROM events WHERE user_id = ? ORDER BY id DESC
```

### 5. New API Endpoints

#### Authentication
- `POST /api/auth/signup` - Create new user
- `POST /api/auth/login` - Login and get JWT
- `POST /api/auth/logout` - Logout (client-side, but can invalidate token)
- `GET /api/auth/me` - Get current user info

#### Repository Management
- `GET /api/repositories` - List user's repositories
- `POST /api/repositories` - Connect new repository
- `GET /api/repositories/{id}` - Get repository details
- `DELETE /api/repositories/{id}` - Disconnect repository
- `POST /api/repositories/{id}/regenerate-secret` - Generate new webhook secret

### 6. Frontend Changes

#### New Pages
1. **Signup Page** (`/signup`)
   - Email, password, name fields
   - Form validation
   - Redirect to login on success

2. **Login Page** (`/login`)
   - Email, password fields
   - "Remember me" option
   - Redirect to dashboard on success

3. **Repository Management Page** (`/repositories`)
   - List of connected repositories
   - "Connect Repository" button
   - Show webhook URL for each repo
   - Copy webhook URL button
   - Disconnect button

4. **Connect Repository Modal/Page**
   - Repository name input (e.g., "username/repo-name")
   - Optional: GitHub token for private repos
   - Generate webhook URL
   - Show instructions for GitHub webhook setup

#### Updated Pages
- **Dashboard**: Filter to show only user's repos
- **Events**: Only show events from user's repos
- **All pages**: Add authentication check, redirect to login if not authenticated

#### New Components
- `AuthProvider` - Context for user state
- `ProtectedRoute` - Wrapper for authenticated routes
- `Navbar` - Show user name, logout button

### 7. Security Considerations

1. **Password Security**
   - Hash with bcrypt (salt rounds: 12)
   - Never store plain passwords
   - Enforce password strength (min 8 chars, complexity)

2. **JWT Security**
   - Short expiration (e.g., 24 hours)
   - Refresh token mechanism (optional, for MVP can skip)
   - Store in httpOnly cookies (better) or localStorage (simpler for MVP)

3. **Webhook Security**
   - Each repo has unique secret
   - Verify HMAC signature from GitHub
   - Rate limiting on webhook endpoint

4. **Authorization**
   - Always verify user owns resource before access
   - SQL injection protection (already using parameterized queries)
   - CORS properly configured

### 8. Migration Strategy

#### Phase 1: Add Auth (Backward Compatible)
1. Add user/repository tables
2. Create default "anonymous" user for existing data
3. Migrate existing events to anonymous user
4. Add auth endpoints (signup/login)

#### Phase 2: Add Repository Management
1. Add repository management endpoints
2. Update webhook handler to support per-repo secrets
3. Add repository management UI

#### Phase 3: Enforce Authorization
1. Add JWT middleware to all API routes
2. Filter queries by user_id
3. Update frontend to require authentication

#### Phase 4: Cleanup
1. Remove anonymous user support
2. Add proper error handling
3. Add email verification (optional)

### 9. User Flow

#### New User Journey
1. Visit CloudSense → See landing page
2. Click "Sign Up" → Fill form → Account created
3. Redirected to dashboard (empty state)
4. Click "Connect Repository" → Enter repo name
5. Get webhook URL → Copy to clipboard
6. Go to GitHub → Settings → Webhooks → Add webhook
7. Paste URL, select events (push, pull_request)
8. Push code → Webhook triggered → Review appears in dashboard

#### Existing User Journey
1. Login → Dashboard shows connected repos
2. View events/reviews for their repos
3. Can add more repos or disconnect existing ones

### 10. Implementation Priority

**MVP (Minimum Viable Product)**
1. ✅ User signup/login
2. ✅ JWT authentication
3. ✅ Repository connection (manual repo name entry)
4. ✅ Per-repo webhook URLs
5. ✅ Filter events/reviews by user
6. ✅ Basic repository management UI

**Nice to Have (Future)**
- GitHub OAuth (auto-discover repos)
- Email verification
- Password reset
- Team/organization support
- Repository statistics
- Webhook delivery status/history

## Technology Stack

### Backend
- `python-jose[cryptography]` - JWT handling
- `passlib[bcrypt]` - Password hashing
- `python-multipart` - Form data parsing (for login)

### Frontend
- React Context for auth state
- Axios interceptors for JWT injection
- Protected route components

## Database Migration

Since we're using SQLite, we'll need migration scripts to:
1. Add new tables
2. Add columns to existing tables
3. Migrate existing data to anonymous user

## Questions to Consider

1. **Email Verification**: Required for MVP? (Recommend: No, add later)
2. **GitHub OAuth**: Auto-connect repos? (Recommend: Manual entry for MVP, OAuth later)
3. **Team Support**: Multiple users per repo? (Recommend: Single user for MVP)
4. **Free vs Paid**: Usage limits? (Recommend: Unlimited for MVP)

## Estimated Implementation Time

- Backend Auth: 2-3 hours
- Database Migration: 1 hour
- Repository Management: 2-3 hours
- Frontend Auth: 2-3 hours
- Repository UI: 2-3 hours
- Testing & Polish: 2-3 hours

**Total: ~12-18 hours**

## Alternative Approaches Considered

### Option 1: GitHub OAuth Only (No Email/Password)
- **Pros**: Simpler, no password management
- **Cons**: Requires GitHub account, less flexible

### Option 2: API Keys Instead of JWT
- **Pros**: Simpler, no expiration
- **Cons**: Less secure, harder to revoke

### Option 3: Session-Based Auth
- **Pros**: Easier to invalidate
- **Cons**: Requires server-side session storage, not stateless

**Recommendation**: JWT-based auth is best for scalability and statelessness.

