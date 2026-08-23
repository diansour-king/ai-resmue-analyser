import hashlib
import hmac
import secrets

_TOKEN_BYTES = 32


def new_token() -> tuple[str, str]:
    """Return (secret, hash). The secret is shown once; only the hash is ever stored."""
    secret = secrets.token_urlsafe(_TOKEN_BYTES)
    return secret, hash_token(secret)


def hash_token(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def tokens_match(secret: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(secret), stored_hash)
