"""
Database-backed authentication provider.

This provider uses SQLAlchemy for database operations and supports:
- PostgreSQL (recommended for production)
- SQLite (development/single-user deployments)

Features:
- Password hashing with bcrypt
- Role-based access control
- Refresh token rotation
- User management (create, update, delete)

Requirements:
    Install with: pip install numerous-apps[auth-db]

Database Setup:
    The provider will create tables automatically on first run.
    For production, use proper migrations.

Usage:
    from numerous.apps.auth import DatabaseAuthProvider
    from numerous.apps import create_app

    auth = DatabaseAuthProvider(
        database_url="postgresql+asyncpg://user:pass@localhost/mydb"
    )
    app = create_app(template="index.html.j2", auth_provider=auth)
"""

import logging
from typing import Any


try:
    import uuid

    import bcrypt
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        ForeignKey,
        String,
        Table,
        func,
        select,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import (
        DeclarativeBase,
        Mapped,
        mapped_column,
        relationship,
        sessionmaker,
    )

    HAS_DB_DEPS = True
except ImportError as e:
    HAS_DB_DEPS = False
    _import_error = e

from datetime import UTC

from ..base import BaseAuthProvider
from ..exceptions import UserExistsError, UserNotFoundError
from ..models import AuthResult, CreateUserRequest, UpdateUserRequest, User


logger = logging.getLogger(__name__)


def _check_deps() -> None:
    """Check that database dependencies are installed."""
    if not HAS_DB_DEPS:
        raise ImportError(
            "Database authentication requires additional dependencies. "
            "Install with: pip install numerous-apps[auth-db]"
        ) from _import_error


# Only define ORM models if dependencies are available
if HAS_DB_DEPS:

    class Base(DeclarativeBase):  # type: ignore[misc]
        """Base class for SQLAlchemy models."""


if HAS_DB_DEPS:
    # Association table for user-role many-to-many
    user_roles = Table(
        "user_roles",
        Base.metadata,
        Column(
            "user_id",
            String(36),
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        Column(
            "role_id",
            String(36),
            ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    class UserModel(Base):
        """SQLAlchemy model for users."""

        __tablename__ = "users"

        id: Mapped[str] = mapped_column(
            String(36), primary_key=True, default=lambda: str(uuid.uuid4())
        )
        username: Mapped[str] = mapped_column(
            String(255), unique=True, nullable=False, index=True
        )
        email: Mapped[str | None] = mapped_column(
            String(255), unique=True, nullable=True
        )
        password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
        is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
        created_at: Mapped[Any] = mapped_column(
            DateTime(timezone=True), server_default=func.now()
        )
        updated_at: Mapped[Any] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        )

        roles: Mapped[list["RoleModel"]] = relationship(
            secondary=user_roles, back_populates="users"
        )
        refresh_tokens: Mapped[list["RefreshTokenModel"]] = relationship(
            back_populates="user", cascade="all, delete-orphan"
        )

        def to_user(self) -> User:
            """Convert to User model."""
            return User(
                id=self.id,
                username=self.username,
                email=self.email,
                roles=[role.name for role in self.roles],
                is_admin=self.is_admin,
                is_active=self.is_active,
            )

    class RoleModel(Base):
        """SQLAlchemy model for roles."""

        __tablename__ = "roles"

        id: Mapped[str] = mapped_column(
            String(36), primary_key=True, default=lambda: str(uuid.uuid4())
        )
        name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
        description: Mapped[str | None] = mapped_column(String(500), nullable=True)

        users: Mapped[list["UserModel"]] = relationship(
            secondary=user_roles, back_populates="roles"
        )

    class RefreshTokenModel(Base):
        """SQLAlchemy model for refresh tokens."""

        __tablename__ = "refresh_tokens"

        id: Mapped[str] = mapped_column(
            String(36), primary_key=True, default=lambda: str(uuid.uuid4())
        )
        user_id: Mapped[str] = mapped_column(
            String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
        token_hash: Mapped[str] = mapped_column(
            String(255), unique=True, nullable=False, index=True
        )
        expires_at: Mapped[Any] = mapped_column(DateTime(timezone=True), nullable=False)
        revoked: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[Any] = mapped_column(
            DateTime(timezone=True), server_default=func.now()
        )

        user: Mapped["UserModel"] = relationship(back_populates="refresh_tokens")


class DatabaseAuthProvider(BaseAuthProvider):
    """
    Database-backed authentication provider.

    Supports PostgreSQL and SQLite databases for user storage.

    Example::

        # PostgreSQL
        auth = DatabaseAuthProvider(
            database_url="postgresql+asyncpg://user:pass@localhost/mydb"
        )

        # SQLite (for development)
        auth = DatabaseAuthProvider(
            database_url="sqlite+aiosqlite:///./app.db"
        )
    """

    def __init__(
        self,
        database_url: str,
        jwt_secret: str | None = None,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        create_tables: bool = True,
    ) -> None:
        """
        Initialize the database auth provider.

        Args:
            database_url: SQLAlchemy async database URL
            jwt_secret: Secret for JWT signing (generated if not provided)
            access_token_expire_minutes: Access token lifetime
            refresh_token_expire_days: Refresh token lifetime
            create_tables: Whether to create tables automatically

        """
        _check_deps()

        import os
        import secrets

        # Get or generate JWT secret
        if jwt_secret is None:
            jwt_secret = os.getenv("NUMEROUS_JWT_SECRET")
        if jwt_secret is None:
            jwt_secret = secrets.token_hex(32)
            logger.warning(
                "No JWT secret provided. Using randomly generated secret. "
                "Set NUMEROUS_JWT_SECRET for production!"
            )

        super().__init__(
            jwt_secret=jwt_secret,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days,
        )

        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        self._initialized = False
        self._create_tables = create_tables

    async def _ensure_initialized(self) -> None:
        """Ensure database tables are created."""
        if not self._initialized and self._create_tables:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._initialized = True

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        hashed: str = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return hashed

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        result: bool = bcrypt.checkpw(password.encode(), password_hash.encode())
        return result

    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()

    async def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user with username and password."""
        await self._ensure_initialized()

        from sqlalchemy.orm import selectinload

        async with self.async_session() as session:
            stmt = (
                select(UserModel)
                .where(UserModel.username == username)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if not user_model:
                return AuthResult.fail("Invalid username or password")

            if not self._verify_password(password, user_model.password_hash):
                return AuthResult.fail("Invalid username or password")

            if not user_model.is_active:
                return AuthResult.fail("User account is inactive")

            return AuthResult.ok(user_model.to_user())

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        await self._ensure_initialized()

        from sqlalchemy.orm import selectinload

        async with self.async_session() as session:
            stmt = (
                select(UserModel)
                .where(UserModel.id == user_id)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if user_model:
                user: User = user_model.to_user()
                return user
            return None

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        await self._ensure_initialized()

        from sqlalchemy.orm import selectinload

        async with self.async_session() as session:
            stmt = (
                select(UserModel)
                .where(UserModel.username == username)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if user_model:
                user: User = user_model.to_user()
                return user
            return None

    async def create_refresh_token(self, user: User) -> str:
        """Create and store a refresh token."""
        await self._ensure_initialized()

        from datetime import datetime, timedelta

        token = await super().create_refresh_token(user)
        token_hash = self._hash_token(token)

        async with self.async_session() as session:
            refresh_token = RefreshTokenModel(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(UTC)
                + timedelta(days=self.refresh_token_expire_days),
            )
            session.add(refresh_token)
            await session.commit()

        return token

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, int] | None:
        """Generate new access token from refresh token."""
        await self._ensure_initialized()

        from datetime import datetime

        token_hash = self._hash_token(refresh_token)

        async with self.async_session() as session:
            stmt = select(RefreshTokenModel).where(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.revoked.is_(False),
                RefreshTokenModel.expires_at > datetime.now(UTC),
            )
            result = await session.execute(stmt)
            token_model = result.scalar_one_or_none()

            if not token_model:
                return None

            # Get user
            user = await self.get_user(token_model.user_id)
            if not user or not user.is_active:
                return None

            return await self.create_access_token(user)

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token."""
        await self._ensure_initialized()

        token_hash = self._hash_token(refresh_token)

        async with self.async_session() as session:
            stmt = select(RefreshTokenModel).where(
                RefreshTokenModel.token_hash == token_hash
            )
            result = await session.execute(stmt)
            token_model = result.scalar_one_or_none()

            if token_model:
                token_model.revoked = True
                await session.commit()
                return True
            return False

    # =========================================================================
    # User Management Methods (for admin interface)
    # =========================================================================

    def list_users(self) -> list[User]:
        """List all users synchronously (for simple cases)."""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.list_users_async())

    async def list_users_async(self) -> list[User]:
        """List all users."""
        await self._ensure_initialized()

        from sqlalchemy.orm import selectinload

        async with self.async_session() as session:
            stmt = (
                select(UserModel)
                .order_by(UserModel.username)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            users = result.scalars().all()
            return [u.to_user() for u in users]

    async def create_user(self, user_data: CreateUserRequest) -> User:
        """Create a new user."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            # Check if user exists
            stmt = select(UserModel).where(UserModel.username == user_data.username)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise UserExistsError(f"User '{user_data.username}' already exists")

            # Check email uniqueness
            if user_data.email:
                stmt = select(UserModel).where(UserModel.email == user_data.email)
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise UserExistsError(f"Email '{user_data.email}' already in use")

            # Create user
            user_model = UserModel(
                username=user_data.username,
                email=user_data.email,
                password_hash=self._hash_password(user_data.password),
                is_admin=user_data.is_admin,
            )

            # Add roles
            if user_data.roles:
                for role_name in user_data.roles:
                    stmt = select(RoleModel).where(RoleModel.name == role_name)
                    result = await session.execute(stmt)
                    role = result.scalar_one_or_none()
                    if role:
                        user_model.roles.append(role)

            session.add(user_model)
            await session.commit()

            # Eagerly load roles to avoid lazy loading issues
            from sqlalchemy.orm import selectinload

            stmt = (
                select(UserModel)
                .where(UserModel.id == user_model.id)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one()

            return user_model.to_user()

    async def update_user(self, user_id: str, user_data: UpdateUserRequest) -> User:
        """Update an existing user."""
        await self._ensure_initialized()

        from sqlalchemy.orm import selectinload

        async with self.async_session() as session:
            stmt = (
                select(UserModel)
                .where(UserModel.id == user_id)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if not user_model:
                raise UserNotFoundError(f"User not found: {user_id}")

            # Update fields
            if user_data.email is not None:
                user_model.email = user_data.email
            if user_data.password is not None:
                user_model.password_hash = self._hash_password(user_data.password)
            if user_data.is_admin is not None:
                user_model.is_admin = user_data.is_admin
            if user_data.is_active is not None:
                user_model.is_active = user_data.is_active
            if user_data.roles is not None:
                # Clear existing roles and add new ones
                user_model.roles = []
                for role_name in user_data.roles:
                    stmt_role = select(RoleModel).where(RoleModel.name == role_name)
                    result_role = await session.execute(stmt_role)
                    role = result_role.scalar_one_or_none()
                    if role:
                        user_model.roles.append(role)

            await session.commit()

            # Reload with roles
            stmt = (
                select(UserModel)
                .where(UserModel.id == user_id)
                .options(selectinload(UserModel.roles))
            )
            result = await session.execute(stmt)
            user_model = result.scalar_one()

            updated_user: User = user_model.to_user()
            return updated_user

    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        await self._ensure_initialized()

        async with self.async_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            user_model = result.scalar_one_or_none()

            if not user_model:
                raise UserNotFoundError(f"User not found: {user_id}")

            await session.delete(user_model)
            await session.commit()

    def get_settings(self) -> dict[str, Any]:
        """Get provider settings (non-sensitive)."""
        settings = super().get_settings()
        settings.update(
            {
                "provider_type": "database",
                "database_url": self.database_url.split("@")[-1]
                if "@" in self.database_url
                else "***",
            }
        )
        return settings
