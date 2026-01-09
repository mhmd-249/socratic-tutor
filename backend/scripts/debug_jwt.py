#!/usr/bin/env python3
"""Debug script to inspect JWT token structure."""

import base64
import json
import sys


def decode_jwt_parts(token: str) -> dict:
    """Decode JWT without verification to inspect its structure."""
    parts = token.split(".")
    if len(parts) != 3:
        print(f"ERROR: Invalid JWT format. Expected 3 parts, got {len(parts)}")
        return {}

    # Decode header (first part)
    header_b64 = parts[0]
    # Add padding if needed
    header_b64 += "=" * (4 - len(header_b64) % 4)
    try:
        header = json.loads(base64.urlsafe_b64decode(header_b64))
    except Exception as e:
        print(f"ERROR decoding header: {e}")
        header = {}

    # Decode payload (second part)
    payload_b64 = parts[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        print(f"ERROR decoding payload: {e}")
        payload = {}

    return {
        "header": header,
        "payload": payload,
    }


def main():
    print("=" * 60)
    print("JWT Token Debugger")
    print("=" * 60)

    # Get token from argument or prompt
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        print("\nPaste your Supabase access token (from localStorage):")
        token = input().strip()

    if not token:
        print("No token provided!")
        return

    print(f"\nToken length: {len(token)} characters")
    print(f"Token preview: {token[:50]}...")

    # Decode and display
    decoded = decode_jwt_parts(token)

    if decoded.get("header"):
        print("\n" + "=" * 60)
        print("JWT HEADER:")
        print("=" * 60)
        print(json.dumps(decoded["header"], indent=2))

        alg = decoded["header"].get("alg")
        print(f"\n>>> Algorithm (alg): {alg}")
        if alg != "HS256":
            print(f"    WARNING: Expected HS256, got {alg}")
            print(f"    You may need to update SUPABASE_JWT_ALGORITHMS in security.py")

        typ = decoded["header"].get("typ")
        print(f">>> Type (typ): {typ}")

    if decoded.get("payload"):
        print("\n" + "=" * 60)
        print("JWT PAYLOAD:")
        print("=" * 60)
        print(json.dumps(decoded["payload"], indent=2))

        # Key fields
        print("\n>>> Key Claims:")
        print(f"    sub (user ID): {decoded['payload'].get('sub')}")
        print(f"    aud (audience): {decoded['payload'].get('aud')}")
        print(f"    role: {decoded['payload'].get('role')}")
        print(f"    iss (issuer): {decoded['payload'].get('iss')}")

        # Check audience
        aud = decoded["payload"].get("aud")
        if aud != "authenticated":
            print(f"\n    WARNING: Expected aud='authenticated', got '{aud}'")

    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)

    if decoded.get("header"):
        alg = decoded["header"].get("alg")
        if alg == "HS256":
            print("✓ Algorithm is HS256 (correct)")
        else:
            print(f"✗ Algorithm is {alg} - need to update security.py")
            print(f"  Change: SUPABASE_JWT_ALGORITHMS = [\"{alg}\"]")

    if decoded.get("payload"):
        aud = decoded["payload"].get("aud")
        if aud == "authenticated":
            print("✓ Audience is 'authenticated' (correct)")
        else:
            print(f"✗ Audience is '{aud}' - need to update security.py")
            print(f"  Change: SUPABASE_JWT_AUDIENCE = \"{aud}\"")


if __name__ == "__main__":
    main()
