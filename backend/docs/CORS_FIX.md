# CORS Configuration Fix

## Problem

Frontend on localhost:3000 was getting CORS errors when trying to reach backend on localhost:8000:

```
Access to fetch at 'http://localhost:8000/api/v1/auth/callback' from origin
'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin'
header is present on the requested resource.
```

Additionally, the `/api/v1/auth/callback` endpoint was returning 500 Internal Server Error.

## Solution

### 1. Updated CORS Configuration (`app/core/config.py`)

**Before:**
```python
CORS_ORIGINS: list[str] | str = ["http://localhost:3000"]
```

**After:**
```python
CORS_ORIGINS: list[str] | str = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
```

Also improved the validator to handle comma-separated strings:
```python
@field_validator("CORS_ORIGINS", mode="before")
@classmethod
def parse_cors_origins(cls, v: Any) -> list[str]:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
    return v
```

### 2. Enhanced CORS Middleware (`app/main.py`)

**Changes:**
- Made explicit which headers are allowed and exposed
- Added `max_age` for preflight request caching
- Kept middleware registration **before** routes (critical!)

```python
application.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "User-Agent",
        "DNT",
        "Cache-Control",
        "X-Requested-With",
    ],
    expose_headers=[
        "Content-Length",
        "Content-Type",
        "Cache-Control",
        "X-Accel-Buffering",
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)
```

### 3. Updated Environment Configuration (`.env`)

**Before:**
```
CORS_ORIGINS=["http://localhost:3000"]
```

**After:**
```
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","http://127.0.0.1:3000","http://127.0.0.1:3001"]
```

### 4. Fixed Auth Callback Error Handling (`app/api/v1/endpoints/auth.py`)

Added comprehensive error handling and logging:

```python
try:
    logger.info(f"Auth callback for supabase_id: {request.supabase_id}")

    # ... existing logic ...

    await db.commit()  # Explicit commit for updates too
    logger.info(f"Successfully created user and profile: {new_user.id}")

    return new_user

except Exception as e:
    logger.error(f"Error in auth callback: {e}", exc_info=True)
    await db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "message": "Failed to process authentication callback",
            "code": "AUTH_CALLBACK_ERROR",
            "error": str(e),
        },
    )
```

**Key improvements:**
- Added logging at each step
- Explicit `commit()` for both new and existing users
- Proper exception handling with rollback
- Detailed error responses

## Testing

### Test CORS Configuration

Run the included test script:

```bash
cd backend
python3 test_cors.py
```

Expected output:
```
============================================================
CORS Configuration Test
============================================================

Configured CORS Origins:
  ✓ http://localhost:3000
  ✓ http://localhost:3001
  ✓ http://127.0.0.1:3000
  ✓ http://127.0.0.1:3001

Checking FastAPI middleware...
  ✓ CORS middleware found

...
```

### Manual Testing

1. **Start the backend:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

2. **Test health endpoint with curl:**
   ```bash
   curl -i http://localhost:8000/health
   ```

   Should return:
   ```
   HTTP/1.1 200 OK
   content-type: application/json
   ...
   {"status":"healthy"}
   ```

3. **Test CORS from browser console (frontend on localhost:3000):**
   ```javascript
   fetch('http://localhost:8000/health')
     .then(r => r.json())
     .then(console.log)
   ```

   Should work without CORS errors and log: `{status: 'healthy'}`

4. **Test auth callback:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/callback \
     -H "Content-Type: application/json" \
     -d '{
       "supabase_id": "test-123",
       "email": "test@example.com",
       "name": "Test User"
     }'
   ```

   Should return user data (200 OK) or detailed error with stack trace in logs.

### Check Response Headers

With curl:
```bash
curl -i -H "Origin: http://localhost:3000" http://localhost:8000/health
```

Should include:
```
access-control-allow-origin: http://localhost:3000
access-control-allow-credentials: true
```

## Files Modified

1. ✅ `app/core/config.py` - Updated CORS_ORIGINS default
2. ✅ `app/main.py` - Enhanced CORS middleware configuration
3. ✅ `app/api/v1/endpoints/auth.py` - Added error handling and logging
4. ✅ `.env` - Updated CORS_ORIGINS to include all ports
5. ✅ `.env.example` - Updated documentation

## Files Created

1. ✅ `test_cors.py` - CORS configuration test script
2. ✅ `docs/CORS_FIX.md` - This documentation

## Verification Steps

After restarting the backend:

1. **Check logs on startup:**
   ```
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   ```

2. **Try frontend request** - Should work without CORS errors

3. **Check browser DevTools:**
   - Network tab → Response headers should show `access-control-allow-origin`
   - Console should have NO CORS errors

4. **Test preflight (OPTIONS) request:**
   ```bash
   curl -X OPTIONS http://localhost:8000/api/v1/auth/callback \
     -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -i
   ```

   Should return 200 OK with CORS headers.

## Common Issues

### CORS Still Not Working?

1. **Clear browser cache** - Browsers cache preflight responses
2. **Check .env is loaded** - Verify with `python3 test_cors.py`
3. **Restart backend** - CORS config is loaded on startup
4. **Check browser console** - Look for actual error message
5. **Verify URL** - Make sure frontend is calling correct port (8000)

### 500 Error on Auth Callback?

Check backend logs for the actual error:
```bash
# In terminal running uvicorn
# Look for: "ERROR:     Error in auth callback: ..."
```

Common causes:
- Database connection issue
- Missing tables (run migrations: `alembic upgrade head`)
- Invalid supabase_id format
- Unique constraint violation (user already exists)

## Environment Variables

You can set CORS_ORIGINS in multiple formats:

**JSON array (recommended):**
```
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
```

**Comma-separated (alternative):**
```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Single origin:**
```
CORS_ORIGINS=http://localhost:3000
```

## Security Notes

- ✅ CORS is properly restrictive (specific origins, not `*`)
- ✅ Credentials are allowed (required for cookies/auth)
- ✅ Only necessary headers are exposed
- ⚠️  In production, use actual domain names (not localhost)
- ⚠️  Consider using environment-specific settings

## Production Considerations

For production deployment, update `.env`:

```
CORS_ORIGINS=["https://your-frontend.com","https://www.your-frontend.com"]
```

Or use comma-separated:
```
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
```

## Next Steps

1. ✅ CORS is fixed for local development
2. Test authentication flow end-to-end
3. Monitor backend logs for any remaining issues
4. Add production CORS origins when deploying

---

**Status**: ✅ Fixed
**Tested**: Local development (localhost:3000, localhost:3001)
**Ready for**: Frontend integration testing
