"""JWT token utilities for authentication."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


logger = logging.getLogger(__name__)


class JWTManager:
    """Manager for creating and validating JWT tokens."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """
        Initialize the JWT manager.

        Args:
            secret: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token lifetime
            refresh_token_expire_days: Refresh token lifetime

        """
        self.secret = secret
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        username: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new access token.

        Args:
            user_id: The user's unique identifier
            username: The user's username
            additional_claims: Optional additional JWT claims

        Returns:
            Encoded JWT access token

        """
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "username": username,
            "type": "access",
            "iat": now,
            "exp": expire,
        }

        if additional_claims:
            payload.update(additional_claims)

        token: str = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new refresh token.

        Args:
            user_id: The user's unique identifier
            additional_claims: Optional additional JWT claims

        Returns:
            Encoded JWT refresh token

        """
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }

        if additional_claims:
            payload.update(additional_claims)

        refresh_token: str = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return refresh_token

    def decode_access_token(self, token: str) -> dict[str, Any] | None:
        """
        Decode and validate an access token.

        Args:
            token: The JWT token to decode

        Returns:
            Decoded payload if valid, None if invalid or expired

        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])

            # Verify it's an access token
            if payload.get("type") != "access":
                logger.warning("Token is not an access token")
                return None

            result: dict[str, Any] = payload
            return result

        except jwt.ExpiredSignatureError:
            logger.debug("Access token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid access token: {e}")
            return None

    def decode_refresh_token(self, token: str) -> dict[str, Any] | None:
        """
        Decode and validate a refresh token.

        Args:
            token: The JWT refresh token to decode

        Returns:
            Decoded payload if valid, None if invalid or expired

        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                logger.warning("Token is not a refresh token")
                return None

            result: dict[str, Any] = payload
            return result

        except jwt.ExpiredSignatureError:
            logger.debug("Refresh token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid refresh token: {e}")
            return None

    def get_token_expiry(self, token: str) -> datetime | None:
        """
        Get the expiry time of a token without full validation.

        Args:
            token: The JWT token

        Returns:
            Expiry datetime if extractable, None otherwise

        """
        try:
            # Decode without verification to get expiry
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=UTC)
            return None
        except jwt.InvalidTokenError:
            return None


def generate_secret_key(length: int = 32) -> str:
    """
    Generate a secure random secret key.

    Args:
        length: Length of the key in bytes (default 32)

    Returns:
        Hex-encoded random string

    """
    import secrets

    return secrets.token_hex(length)
