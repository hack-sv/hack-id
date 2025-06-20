#!/usr/bin/env python3
"""
Test script to verify the DEBUG_MODE and URL configuration works correctly.
"""

import os
import subprocess
import sys


def test_development_mode():
    """Test development mode configuration."""
    print("=== Testing Development Mode ===")

    # Run a separate Python process to test development mode
    env = os.environ.copy()
    env.pop("PROD", None)  # Remove PROD if set

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
from dotenv import load_dotenv
load_dotenv()

PROD = os.getenv("PROD", "").upper() == "TRUE"
DEBUG_MODE = not PROD

if PROD:
    BASE_URL = "http://id.hack.sv"
else:
    BASE_URL = "http://127.0.0.1:3000"

REDIRECT_URI = os.getenv("REDIRECT_URI") or f"{BASE_URL}/auth/google/callback"

print(f"PROD: {PROD}")
print(f"DEBUG_MODE: {DEBUG_MODE}")
print(f"BASE_URL: {BASE_URL}")
print(f"REDIRECT_URI: {REDIRECT_URI}")

assert PROD == False
assert DEBUG_MODE == True
assert BASE_URL == "http://127.0.0.1:3000"
assert REDIRECT_URI == "http://127.0.0.1:3000/auth/google/callback"
print("✅ Development mode test passed!")
""",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"Test failed with return code {result.returncode}")
        return False
    return True


def test_production_mode():
    """Test production mode configuration."""
    print("\n=== Testing Production Mode ===")

    # Run a separate Python process to test production mode
    env = os.environ.copy()
    env["PROD"] = "TRUE"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import os
from dotenv import load_dotenv
load_dotenv()

PROD = os.getenv("PROD", "").upper() == "TRUE"
DEBUG_MODE = not PROD

if PROD:
    BASE_URL = "http://id.hack.sv"
else:
    BASE_URL = "http://127.0.0.1:3000"

REDIRECT_URI = os.getenv("REDIRECT_URI") or f"{BASE_URL}/auth/google/callback"

print(f"PROD: {PROD}")
print(f"DEBUG_MODE: {DEBUG_MODE}")
print(f"BASE_URL: {BASE_URL}")
print(f"REDIRECT_URI: {REDIRECT_URI}")

assert PROD == True
assert DEBUG_MODE == False
assert BASE_URL == "http://id.hack.sv"
assert REDIRECT_URI == "http://id.hack.sv/auth/google/callback"
print("✅ Production mode test passed!")
""",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        print(f"Test failed with return code {result.returncode}")
        return False
    return True


if __name__ == "__main__":
    dev_success = test_development_mode()
    prod_success = test_production_mode()

    if dev_success and prod_success:
        print("\n🎉 All tests passed! Configuration is working correctly.")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
