# API Authentication Guide

**Version:** 2.1  
**Last Updated:** January 1, 2024

---

## Overview

YourSaaS Product API uses multiple authentication mechanisms. This guide covers all supported methods, when to use each, and common configuration issues.

---

## 1. Authentication Methods

### 1.1 API Key (Recommended for Server-to-Server)

The simplest and most common authentication method for backend integrations.

**Request format:**
```
GET /v1/resource HTTP/1.1
Host: api.yoursaasproduct.com
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Creating API keys:**
1. Settings → Developer → API Keys → Create New Key
2. Choose a name and optional expiry date
3. Copy the key immediately – it is shown only once
4. Keys begin with prefix: `ysp_live_` (production) or `ysp_test_` (sandbox)

**Key scopes available:**
- `read:all` – Read access to all resources
- `write:all` – Read and write access to all resources
- `read:users` – Read user data only
- `write:reports` – Create and modify reports only
- `admin` – Full administrative access (use with extreme caution)

---

### 1.2 OAuth 2.0 (Recommended for User-Facing Applications)

Use OAuth 2.0 when your application acts on behalf of a user.

**Supported flows:**
- Authorization Code + PKCE (recommended for SPAs and mobile apps)
- Client Credentials (server-to-server, non-user-context)
- Refresh Token (for maintaining long-lived access)

**OAuth 2.0 endpoints:**
```
Authorization URL: https://auth.yoursaasproduct.com/oauth/authorize
Token URL:         https://auth.yoursaasproduct.com/oauth/token
Revocation URL:    https://auth.yoursaasproduct.com/oauth/revoke
JWKS URL:          https://auth.yoursaasproduct.com/.well-known/jwks.json
```

**Authorization Code + PKCE flow:**

Step 1 – Generate code verifier and challenge:
```python
import hashlib, base64, os

code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode()
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).rstrip(b'=').decode()
```

Step 2 – Redirect user to authorization URL:
```
https://auth.yoursaasproduct.com/oauth/authorize
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=https://yourapp.com/callback
  &scope=read:all
  &state=RANDOM_STATE_VALUE
  &code_challenge=CODE_CHALLENGE
  &code_challenge_method=S256
```

Step 3 – Exchange code for token:
```bash
curl -X POST https://auth.yoursaasproduct.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=https://yourapp.com/callback" \
  -d "code_verifier=CODE_VERIFIER"
```

Step 4 – Token response:
```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "ysp_refresh_...",
  "scope": "read:all"
}
```

---

### 1.3 SAML 2.0 (Enterprise SSO)

For enterprise customers using SAML-based Single Sign-On.

**Metadata URL:** `https://auth.yoursaasproduct.com/saml/metadata`

**Required IdP configuration:**
- ACS URL: `https://auth.yoursaasproduct.com/saml/acs`
- Entity ID: `https://auth.yoursaasproduct.com/saml/entity`
- Name ID format: `urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress`
- Required attributes: `email`, `given_name`, `family_name`
- Optional: `groups`, `role`

SAML configuration is managed by your workspace Owner at: Settings → Security → SSO/SAML

---

## 2. Token Management

### Access Token Lifetime
- API Keys: No expiry by default (optional: set expiry in key settings)
- OAuth Access Tokens: 1 hour
- OAuth Refresh Tokens: 30 days (rotated on each use)
- SAML Sessions: Controlled by IdP session settings

### Refreshing OAuth Tokens
```bash
curl -X POST https://auth.yoursaasproduct.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "refresh_token=YOUR_REFRESH_TOKEN"
```

### Revoking Tokens
```bash
curl -X POST https://auth.yoursaasproduct.com/oauth/revoke \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=TOKEN_TO_REVOKE"
```

---

## 3. Common Authentication Errors

| HTTP Status | Error Code | Cause | Resolution |
|---|---|---|---|
| 401 | `invalid_token` | Token expired or malformed | Refresh or regenerate token |
| 401 | `token_not_found` | Token revoked or never existed | Generate a new token |
| 401 | `missing_authorization` | Authorization header absent | Add `Authorization: Bearer TOKEN` header |
| 403 | `insufficient_scope` | Token lacks required scope | Regenerate with correct scope |
| 403 | `ip_not_allowlisted` | IP address not in allowlist | Add IP in Settings → Security |
| 429 | `rate_limit_exceeded` | Too many auth requests | Implement exponential backoff |
| 400 | `invalid_client` | Wrong client_id in OAuth flow | Verify client credentials |
| 400 | `invalid_grant` | Auth code expired/used | Restart the OAuth flow |

---

## 4. Security Best Practices

- **Never expose API keys in client-side code** (JavaScript, mobile apps)
- **Use environment variables** for secrets: `os.environ.get('API_KEY')`
- **Use scoped keys:** Create separate keys per integration with minimum necessary scope
- **Rotate keys every 90 days** or immediately on suspected compromise
- **Validate JWT signatures** using the JWKS endpoint for OAuth tokens
- **Verify the `iss` claim** in JWTs: must be `https://auth.yoursaasproduct.com`
- **Verify the `aud` claim** in JWTs: must match your `client_id`

---

## 5. SDK Quick Start

### Python
```python
from yoursaas import Client

client = Client(api_key="ysp_live_YOUR_KEY")
users = client.users.list()
```

### JavaScript / TypeScript
```typescript
import { YourSaasClient } from '@yoursaas/sdk';

const client = new YourSaasClient({ apiKey: process.env.API_KEY });
const users = await client.users.list();
```

### Go
```go
client := yoursaas.NewClient(os.Getenv("API_KEY"))
users, err := client.Users.List(ctx)
```

---

## 6. Testing Authentication

Use the sandbox environment to test without affecting production data:

- Sandbox API base URL: `https://api-sandbox.yoursaasproduct.com/v1`
- Test API keys begin with: `ysp_test_`
- Test keys are created at: Settings → Developer → API Keys → Environment: Sandbox

The `/v1/auth/verify` endpoint confirms token validity:
```bash
curl https://api.yoursaasproduct.com/v1/auth/verify \
  -H "Authorization: Bearer YOUR_TOKEN"

# 200 OK: {"valid": true, "scope": "read:all", "expires_at": "..."}
# 401:     {"error": "invalid_token", "message": "Token has expired"}
```

---

## 7. Support

- API documentation: https://docs.yoursaasproduct.com/api
- OAuth App registration: Settings → Developer → OAuth Applications
- Developer support: developers@yoursaasproduct.com
- Status and incidents: https://status.yoursaasproduct.com
