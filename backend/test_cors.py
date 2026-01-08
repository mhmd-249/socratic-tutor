"""Test CORS configuration."""

from app.core.config import settings

print("CORS Configuration Test")
print("=" * 50)
print(f"CORS_ORIGINS type: {type(settings.CORS_ORIGINS)}")
print(f"CORS_ORIGINS value: {settings.CORS_ORIGINS}")
print("=" * 50)

if isinstance(settings.CORS_ORIGINS, list):
    print("✓ CORS_ORIGINS is a list")
    for origin in settings.CORS_ORIGINS:
        print(f"  - {origin}")
else:
    print("✗ CORS_ORIGINS is not a list!")
