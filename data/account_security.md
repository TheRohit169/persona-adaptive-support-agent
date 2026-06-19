# Account Security Guide

**Last Updated:** January 1, 2024

---

## Overview

Account security is a shared responsibility. This guide covers the security features available in YourSaaS Product and best practices for keeping your account safe.

---

## 1. Password Requirements

All account passwords must meet the following criteria:

- Minimum **12 characters** in length
- At least one **uppercase letter** (A–Z)
- At least one **lowercase letter** (a–z)
- At least one **number** (0–9)
- At least one **special character** (`!@#$%^&*()_+-=[]{}|;':,./<>?`)
- Cannot contain your email address or common dictionary words
- Cannot be the same as your last 10 passwords

**Recommended approach:** Use a password manager to generate and store a unique, high-entropy password for each service.

---

## 2. Multi-Factor Authentication (MFA)

Enabling MFA is the single most effective step you can take to protect your account.

### Supported methods:
| Method | Security Level | Availability |
|---|---|---|
| Authenticator App (TOTP) | High | All plans |
| Hardware Security Key (FIDO2) | Very High | Enterprise only |
| SMS OTP | Medium | All plans |
| Email OTP | Low | All plans (fallback) |

See the **Multi-Factor Authentication Guide** for setup instructions and troubleshooting.

---

## 3. Active Sessions Management

View and manage all active login sessions:

1. **Settings → Security → Active Sessions**
2. See: device type, browser, IP address, country, last active time
3. Click **"Revoke"** next to any session you don't recognize
4. Click **"Revoke All Other Sessions"** to log out from all devices except the current one

**Recommendation:** Review active sessions monthly and revoke any unrecognized or inactive sessions.

---

## 4. Login Notifications

Security notifications are sent for:
- Login from a new device or unrecognized IP address
- Login from a new geographic location
- Multiple failed login attempts
- Password change
- MFA enabled or disabled
- API key created or deleted
- Billing information changed

To configure notifications: **Settings → Security → Security Alerts**

---

## 5. API Key Security

API keys provide programmatic access to your account. Treat them like passwords.

**Best practices:**
- Never commit API keys to version control (GitHub, GitLab, Bitbucket)
- Use environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault)
- Use the minimum scope required (create read-only keys for read-only operations)
- Set key expiry where possible (Settings → Developer → API Keys → Expiry)
- Rotate keys periodically (recommended: every 90 days)
- Immediately revoke keys if you suspect compromise

**If your API key is compromised:**
1. Revoke it immediately: **Settings → Developer → API Keys → Revoke**
2. Generate a new key
3. Update your integration with the new key
4. Review API logs for unauthorized usage: **Settings → Developer → API Logs**

---

## 6. Audit Logs

Audit logs record all significant account actions for compliance and security investigation.

**What is logged:**
- All login attempts (success and failure)
- Permission changes
- Data exports
- API key creation/deletion
- Team member invitations/removals
- Subscription and billing changes
- Configuration changes

**Accessing audit logs:**
- **Settings → Security → Audit Logs**
- Available on Professional (30-day retention) and Enterprise (365-day retention) plans
- Export as CSV for external SIEM integration

---

## 7. IP Allowlisting (Enterprise)

Enterprise customers can restrict account access to specific IP ranges:

1. **Settings → Security → IP Allowlist**
2. Add CIDR ranges (e.g., `203.0.113.0/24`)
3. All logins and API calls from outside the allowlist will be blocked
4. Ensure you include your own IP before saving (to avoid locking yourself out)

---

## 8. Single Sign-On (SSO) and Security

For organizations using SSO:
- Password and MFA management is handled by your Identity Provider (IdP)
- Platform-level security settings still apply for API keys and sessions
- Your IdP admin can configure conditional access policies, device compliance, and risk-based MFA
- Supported IdPs: Okta, Azure AD, Google Workspace, Ping Identity, and any SAML 2.0-compatible IdP

---

## 9. Suspicious Activity

If you notice suspicious activity on your account:

1. **Immediately change your password**
2. **Revoke all active sessions** (Settings → Security → Active Sessions → Revoke All)
3. **Review and revoke API keys** (Settings → Developer → API Keys)
4. **Enable MFA** if not already enabled
5. **Contact security team:** security@yoursaasproduct.com
6. **Include in your report:** account email, nature of suspicious activity, approximate time, affected data

Our security team responds to breach reports within **4 hours**.

---

## 10. Data Encryption

- **In transit:** All data encrypted with TLS 1.3
- **At rest:** AES-256 encryption for all stored data
- **Database:** Encrypted at the block-storage level
- **API keys:** Stored as bcrypt hashes; cannot be recovered (only revoked and recreated)
- **Passwords:** Stored as Argon2id hashes; never stored or transmitted in plaintext

---

## 11. Security Compliance

YourSaaS Product maintains the following compliance certifications:

- SOC 2 Type II (annual renewal)
- ISO 27001
- GDPR compliant (Data Processing Agreement available)
- CCPA compliant
- HIPAA-eligible configuration available (Enterprise plan with BAA)

Compliance documentation available at: **https://yoursaasproduct.com/security**
