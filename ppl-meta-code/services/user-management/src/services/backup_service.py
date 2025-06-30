import os
import re
import subprocess

from datetime import datetime
from sqlalchemy.orm import Session

from src.models.user import User, UserAction
from src.models.role import Role, Capability, UserRole, RoleCapability


def export_data(db: Session):
    users = db.query(User).all()
    roles = db.query(Role).all()
    capabilities = db.query(Capability).all()
    user_roles = db.query(UserRole).all()
    role_capabilities = db.query(RoleCapability).all()
    user_actions = db.query(UserAction).all()

    return {
        "users": [u.__dict__ for u in users],
        "roles": [r.__dict__ for r in roles],
        "capabilities": [c.__dict__ for c in capabilities],
        "user_roles": [ur.__dict__ for ur in user_roles],
        "role_capabilities": [rc.__dict__ for rc in role_capabilities],
        "user_actions": [ua.__dict__ for ua in user_actions],
    }

def backup_database(db_url: str, backup_path: str) -> bool:
    """
    Create a backup of the PostgreSQL database at the given URL.
    Returns True if successful, False otherwise.
    """
    if db_url.startswith("postgresql://"):
        match = re.match(
            r"postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", db_url
        )
        if not match:
            return False
        user, password, host, port, dbname = match.groups()
        port = port or "5432"
        env = os.environ.copy()
        env["PGPASSWORD"] = password
        with open(backup_path, "wb") as f:
            result = subprocess.run(
                [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-F", "c",  # custom format
                    dbname
                ],
                env=env,
                stdout=f,
                check=False  # Explicitly set check
            )
        return result.returncode == 0
    return False

def restore_database(db_url: str, backup_path: str) -> bool:
    """
    Restore a PostgreSQL database from a backup file.
    Backs up the current database before restoring.
    Returns True if successful, False otherwise.
    """
    if db_url.startswith("postgresql://"):
        match = re.match(
            r"postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)", db_url
        )
        if not match:
            return False
        user, password, host, port, dbname = match.groups()
        port = port or "5432"
        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # Backup current DB before restoring
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_before_restore = f"{dbname}_before_restore_{timestamp}.dump"
        with open(backup_before_restore, "wb") as f:
            subprocess.run(
                [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-F", "c",
                    dbname
                ],
                env=env,
                stdout=f,
                check=False  # Explicitly set check
            )

        # Drop and recreate the database
        drop_cmd = [
            "dropdb",
            "-h", host,
            "-p", port,
            "-U", user,
            dbname
        ]
        create_cmd = [
            "createdb",
            "-h", host,
            "-p", port,
            "-U", user,
            dbname
        ]
        restore_cmd = [
            "pg_restore",
            "-h", host,
            "-p", port,
            "-U", user,
            "-d", dbname,
            "--clean",
            backup_path
        ]
        # Drop DB
        subprocess.run(drop_cmd, env=env, check=False)
        # Create DB
        subprocess.run(create_cmd, env=env, check=False)
        # Restore DB
        result = subprocess.run(restore_cmd, env=env, check=False)
        return result.returncode == 0
    return False

def restore_data(db: Session, data: dict):
    db.query(UserAction).delete()
    db.query(UserRole).delete()
    db.query(RoleCapability).delete()
    db.query(Capability).delete()
    db.query(Role).delete()
    db.query(User).delete()
    db.commit()

    for u in data.get("users", []):
        u.pop("_sa_instance_state", None)
        db.add(User(**u))
    for r in data.get("roles", []):
        r.pop("_sa_instance_state", None)
        db.add(Role(**r))
    for c in data.get("capabilities", []):
        c.pop("_sa_instance_state", None)
        db.add(Capability(**c))
    for ur in data.get("user_roles", []):
        ur.pop("_sa_instance_state", None)
        db.add(UserRole(**ur))
    for rc in data.get("role_capabilities", []):
        rc.pop("_sa_instance_state", None)
        db.add(RoleCapability(**rc))
    for ua in data.get("user_actions", []):
        ua.pop("_sa_instance_state", None)
        db.add(UserAction(**ua))
    db.commit()

