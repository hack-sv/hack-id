import os
import string

os.environ.setdefault("SECRET_KEY", "test-secret")

from models.auth import generate_verification_code, generate_verification_token


def test_generate_verification_code_length_and_digits():
    code = generate_verification_code()
    assert len(code) == 6
    assert all(c in string.digits for c in code)


def test_generate_verification_token_length_and_alphabet():
    token = generate_verification_token()
    assert len(token) == 32
    alphabet = string.ascii_letters + string.digits
    assert all(c in alphabet for c in token)
