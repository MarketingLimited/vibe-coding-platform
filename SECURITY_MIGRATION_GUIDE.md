# Security Migration Guide - Vibe Coding Platform

## Version 2.1 Security Updates

This document describes critical security improvements made to the Vibe Coding Platform and provides migration instructions.

## Overview of Changes

### 1. Password Hashing Algorithm Change (CRITICAL)

**Previous:** SHA-256 without salt
**New:** bcrypt with 12 rounds

#### Why This Change?
- SHA-256 is a fast hashing algorithm designed for data integrity, not password storage
- Without salt, passwords are vulnerable to rainbow table attacks
- bcrypt is specifically designed for password hashing with built-in salting and adjustable cost factor

#### Impact
⚠️ **IMPORTANT:** Existing project passwords stored with SHA-256 will no longer work after this update.

#### Migration Options

**Option 1: Password Rotation (Recommended)**
1. Deploy the updated code
2. Notify all users to rotate their project passwords using the `/projects/rotate-password` endpoint
3. New passwords will be hashed with bcrypt automatically

**Option 2: Database Migration Script**
Unfortunately, since password hashes are one-way, we cannot automatically convert SHA-256 hashes to bcrypt.
Users MUST reset their passwords after the update.

**Option 3: Temporary Compatibility Mode (Not Recommended)**
If you need time for migration, you can temporarily support both hashing methods by modifying the `verify_password` function:

```python
def verify_password_legacy(password: str, hashed: str) -> bool:
    """Temporary compatibility with SHA-256 hashes."""
    # Try bcrypt first
    try:
        if bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8')):
            return True
    except (ValueError, AttributeError):
        pass

    # Fallback to SHA-256 (INSECURE - remove after migration)
    import hashlib
    sha256_hash = hashlib.sha256(password.encode()).hexdigest()
    if secrets.compare_digest(sha256_hash, hashed):
        # TODO: Rehash with bcrypt and update database
        logger.warning("User authenticated with legacy SHA-256 hash", extra={"hash_prefix": hashed[:8]})
        return True

    return False
```

**IMPORTANT:** Remove this compatibility mode after all passwords have been migrated.

---

### 2. CORS Security Configuration

**Previous:** Allow all origins (`allow_origins=["*"]`)
**New:** Configurable allowed origins via `ALLOWED_ORIGINS` environment variable

#### Migration Steps
1. Add `ALLOWED_ORIGINS` to your `.env` file
2. List all legitimate origins that should access your API:
   ```bash
   ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
   ```
3. If you don't need CORS (API-only access), leave it empty:
   ```bash
   ALLOWED_ORIGINS=
   ```

---

### 3. Timing Attack Prevention

**Previous:** String comparison for API keys and passwords
**New:** Constant-time comparison using `secrets.compare_digest()`

#### Impact
No migration needed - this is a drop-in security improvement.

---

### 4. Command Injection Prevention

**Previous:** Shell string interpolation in `exec` commands
**New:** Command array format without shell interpolation

#### Impact
No migration needed - command execution behavior remains the same, but is now more secure.

---

### 5. Rate Limiter Fail Mode

**Previous:** Fail open (allow requests when Redis unavailable)
**New:** Configurable via `STRICT_RATE_LIMITING` (default: fail closed)

#### Migration Steps
1. Add to `.env`:
   ```bash
   STRICT_RATE_LIMITING=true  # Recommended for production
   ```
2. For development environments with unreliable Redis:
   ```bash
   STRICT_RATE_LIMITING=false
   ```

---

### 6. Input Validation Improvements

**New Validations:**
- Path traversal prevention in `cwd` parameter
- Command pattern validation (blocks extremely dangerous operations)
- GitHub token format validation
- Additional secrets format validation

#### Impact
Some previously accepted inputs may now be rejected if they violate security constraints.

**Examples of now-blocked operations:**
- Working directory with `..` (path traversal)
- Commands like `rm -rf /`
- Invalid secret key formats (must be uppercase with underscores)

---

## Deployment Checklist

### Pre-Deployment
- [ ] Review all configuration changes
- [ ] Update `.env` file with new variables:
  - `ALLOWED_ORIGINS`
  - `STRICT_RATE_LIMITING`
- [ ] Plan password rotation strategy
- [ ] Notify users about upcoming password reset requirement

### Deployment
- [ ] Stop the application
- [ ] Update code to latest version
- [ ] Install new dependencies (bcrypt):
  ```bash
  cd api
  pip install -r requirements.txt
  ```
- [ ] Update configuration files
- [ ] Start the application
- [ ] Verify health endpoint: `/health`

### Post-Deployment
- [ ] Test authentication with new passwords
- [ ] Monitor logs for authentication failures
- [ ] Track password rotation progress
- [ ] Verify CORS configuration is working
- [ ] Test rate limiting behavior

---

## Rollback Plan

If you need to rollback:

1. **Revert Code**
   ```bash
   git checkout <previous-commit>
   ```

2. **Restore Previous Dependencies**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

3. **Revert Configuration**
   - Remove `ALLOWED_ORIGINS` from `.env`
   - Remove `STRICT_RATE_LIMITING` from `.env`

4. **Note:** Any passwords changed after deployment will need to be reset again

---

## Security Best Practices Going Forward

1. **API Keys**
   - Rotate `API_KEY` and `MASTER_API_KEY` regularly
   - Use strong, randomly generated keys (32+ characters)

2. **CORS**
   - Only add trusted origins to `ALLOWED_ORIGINS`
   - Never use `*` in production

3. **Rate Limiting**
   - Keep `STRICT_RATE_LIMITING=true` in production
   - Monitor Redis health to prevent service disruptions

4. **Secrets Management**
   - Keep `GITHUB_SECRETS_KEY` secure and backed up
   - Use environment-specific secrets keys

5. **Monitoring**
   - Watch for failed authentication attempts in logs
   - Set up alerts for rate limit violations
   - Monitor Redis availability

---

## Support

For questions or issues during migration:
- Check logs in `/logs/audit.log` and `/logs/app.log`
- Review the application health: `GET /health/services`
- Refer to the main README for general setup instructions

---

## Changelog

### Version 2.1 (2025-11-18)
- Replaced SHA-256 password hashing with bcrypt
- Added CORS origin configuration
- Implemented timing attack prevention
- Added command injection safeguards
- Improved rate limiter error handling
- Enhanced input validation across all endpoints
- Added HTTP request timeouts

---

**Last Updated:** 2025-11-18
**Migration Priority:** HIGH - Deploy as soon as possible for security improvements
