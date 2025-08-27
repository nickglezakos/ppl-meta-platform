"""
User Service - User management and authentication

Handles:
- User account creation and management
- Owner privileges and role-based access
- User authentication and sessions
- Integration with license limits

GitHub Issue: #44
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from models.platform_models import (
    UserAccount,
    UserListResponse,
    UserManagementRequest,
    UserManagementResponse,
    UserRole,
)

logger = logging.getLogger(__name__)


class UserService:
    """User management and authentication service"""

    def __init__(self, platform_service, data_dir: Optional[str] = None):
        """Initialize user service"""
        self.platform_service = platform_service
        self.data_dir = Path(data_dir or "data")
        self.data_dir.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "users.db"
        self._background_tasks = []

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Create users table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    role TEXT DEFAULT 'user',
                    created_date TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    preferences TEXT DEFAULT '{}',
                    permissions TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}'
                )
            """
            )

            # Create sessions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    expires_date TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """
            )

            conn.commit()
            conn.close()
            logger.info("✅ User database initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize user database: {e}")
            raise

    async def create_owner_user(self, email: str, username: str = None) -> UserAccount:
        """Create the platform owner user"""
        try:
            if not username:
                username = email.split("@")[0]

            # Check if owner already exists
            existing_owner = await self._get_user_by_role(UserRole.OWNER)
            if existing_owner:
                logger.info(f"Owner user already exists: {existing_owner.email}")
                return existing_owner

            # Create owner user
            owner = UserAccount(
                user_id=uuid4(),
                username=username,
                email=email,
                role=UserRole.OWNER,
                created_date=datetime.now(),
                is_active=True,
                permissions=["*"],  # Owner has all permissions
                metadata={"created_by": "ppl-meta-bootcore", "is_owner": True},
            )

            # Save to database
            await self._save_user(owner)

            logger.info(f"✅ Created owner user: {email}")
            return owner

        except Exception as e:
            logger.error(f"❌ Failed to create owner user: {e}")
            raise

    async def create_user(
        self, request: UserManagementRequest
    ) -> UserManagementResponse:
        """Create a new user"""
        try:
            # Check if username/email already exists
            existing_user = await self._get_user_by_username(request.username)
            if existing_user:
                return UserManagementResponse(
                    success=False,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    username=request.username,
                    email=request.email,
                    role=request.role,
                    message="Username already exists",
                )

            existing_user = await self._get_user_by_email(request.email)
            if existing_user:
                return UserManagementResponse(
                    success=False,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    username=request.username,
                    email=request.email,
                    role=request.role,
                    message="Email already exists",
                )

            # Check user limits (TODO: integrate with license service)
            current_count = await self.get_user_count()
            max_users = 5  # TODO: Get from license service

            if current_count >= max_users:
                return UserManagementResponse(
                    success=False,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    username=request.username,
                    email=request.email,
                    role=request.role,
                    message=f"Maximum users reached ({max_users})",
                )

            # Create user
            user = UserAccount(
                user_id=uuid4(),
                username=request.username,
                email=request.email,
                role=request.role,
                created_date=datetime.now(),
                is_active=True,
                permissions=request.permissions,
                metadata={
                    "created_by": "ppl-meta-bootcore",
                    "invitation_sent": request.send_invitation,
                },
            )

            # Save to database
            await self._save_user(user)

            # Generate activation link
            activation_link = None
            if request.send_invitation:
                activation_link = f"/activate?token={self._generate_token()}"

            logger.info(f"✅ Created user: {request.username}")

            return UserManagementResponse(
                success=True,
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                activation_link=activation_link,
                message="User created successfully",
            )

        except Exception as e:
            logger.error(f"❌ Failed to create user: {e}")
            return UserManagementResponse(
                success=False,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                username=request.username,
                email=request.email,
                role=request.role,
                message=f"Failed to create user: {str(e)}",
            )

    async def get_users(self) -> UserListResponse:
        """Get list of all users"""
        try:
            users = await self._load_all_users()
            owner = await self._get_user_by_role(UserRole.OWNER)

            return UserListResponse(
                users=users,
                total_count=len(users),
                owner_info=owner,
                max_users=5,  # TODO: Get from license service
            )

        except Exception as e:
            logger.error(f"❌ Failed to get users: {e}")
            return UserListResponse(
                users=[], total_count=0, owner_info=None, max_users=1
            )

    async def _save_user(self, user: UserAccount):
        """Save user to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO users (
                    user_id, username, email, password_hash, role,
                    created_date, last_login, is_active, preferences,
                    permissions, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(user.user_id),
                    user.username,
                    user.email,
                    user.password_hash,
                    user.role.value,
                    user.created_date.isoformat(),
                    user.last_login.isoformat() if user.last_login else None,
                    1 if user.is_active else 0,
                    json.dumps(user.preferences),
                    json.dumps(user.permissions),
                    json.dumps(user.metadata),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to save user: {e}")
            raise

    async def _load_all_users(self) -> List[UserAccount]:
        """Load all users from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM users ORDER BY created_date DESC
            """
            )

            rows = cursor.fetchall()
            conn.close()

            users = []
            for row in rows:
                user = self._parse_user_row(row)
                if user:
                    users.append(user)

            return users

        except Exception as e:
            logger.error(f"❌ Failed to load users: {e}")
            return []

    async def _get_user_by_username(self, username: str) -> Optional[UserAccount]:
        """Get user by username"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM users WHERE username = ?
            """,
                (username,),
            )

            row = cursor.fetchone()
            conn.close()

            return self._parse_user_row(row) if row else None

        except Exception as e:
            logger.error(f"❌ Failed to get user by username: {e}")
            return None

    async def _get_user_by_email(self, email: str) -> Optional[UserAccount]:
        """Get user by email"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM users WHERE email = ?
            """,
                (email,),
            )

            row = cursor.fetchone()
            conn.close()

            return self._parse_user_row(row) if row else None

        except Exception as e:
            logger.error(f"❌ Failed to get user by email: {e}")
            return None

    async def _get_user_by_role(self, role: UserRole) -> Optional[UserAccount]:
        """Get user by role"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM users WHERE role = ? LIMIT 1
            """,
                (role.value,),
            )

            row = cursor.fetchone()
            conn.close()

            return self._parse_user_row(row) if row else None

        except Exception as e:
            logger.error(f"❌ Failed to get user by role: {e}")
            return None

    def _parse_user_row(self, row) -> Optional[UserAccount]:
        """Parse database row into UserAccount"""
        if not row:
            return None

        try:
            (
                user_id,
                username,
                email,
                password_hash,
                role,
                created_date,
                last_login,
                is_active,
                preferences,
                permissions,
                metadata,
            ) = row

            return UserAccount(
                user_id=UUID(user_id),
                username=username,
                email=email,
                password_hash=password_hash,
                role=UserRole(role),
                created_date=datetime.fromisoformat(created_date),
                last_login=datetime.fromisoformat(last_login) if last_login else None,
                is_active=bool(is_active),
                preferences=json.loads(preferences) if preferences else {},
                permissions=json.loads(permissions) if permissions else [],
                metadata=json.loads(metadata) if metadata else {},
            )
        except Exception as e:
            logger.error(f"❌ Failed to parse user row: {e}")
            return None

    def _generate_token(self) -> str:
        """Generate activation token"""
        import secrets

        return secrets.token_urlsafe(32)

    async def get_user_count(self) -> int:
        """Get total user count"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            count = cursor.fetchone()[0]

            conn.close()
            return count

        except Exception as e:
            logger.error(f"❌ Failed to get user count: {e}")
            return 0

    async def health_check(self) -> str:
        """Health check for user service"""
        try:
            # Check database connectivity
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()

            return "healthy"

        except Exception as e:
            logger.error(f"❌ User service health check failed: {e}")
            return "unhealthy"

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        # Background session cleanup task
        task = asyncio.create_task(self._cleanup_expired_sessions())
        self._background_tasks.append(task)

    async def _cleanup_expired_sessions(self):
        """Background task for cleaning up expired sessions"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                # Delete expired sessions
                cursor.execute(
                    """
                    DELETE FROM user_sessions 
                    WHERE datetime(expires_date) < datetime('now')
                """
                )

                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"🧹 Cleaned up {deleted} expired sessions")

                conn.commit()
                conn.close()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Session cleanup error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

    async def cleanup(self):
        """Cleanup resources"""
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._background_tasks.clear()
        logger.info("✅ User service cleanup complete")
