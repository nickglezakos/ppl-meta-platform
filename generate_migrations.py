#!/usr/bin/env python3
"""
Database Migration Generator for PPL Meta Platform

This script generates initial Alembic migrations for all services
by using standalone database configurations.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"


def generate_migrations():
    """Generate migrations for all services."""

    # Set environment variables
    env_vars = {
        "DATABASE_PASSWORD": "change-this-password",
        "DATABASE_URL": "postgresql://nickadmin:change-this-password@localhost:5433/ppl_db",
        "PYTHONPATH": os.getcwd(),
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    services = [
        "ppl-meta-node",
        "ppl-meta-media",
        "ppl-meta-gateway",
        "ppl-meta-orchestrator",
    ]

    results = {}

    for service in services:
        service_path = Path(service)
        if not service_path.exists():
            results[service] = (False, f"Service directory {service} not found")
            continue

        print(f"\n📋 Generating migration for {service}...")

        # Check if alembic is initialized
        migrations_path = service_path / "migrations"
        if not migrations_path.exists():
            print(f"   ❌ Alembic not initialized for {service}")
            results[service] = (False, "Alembic not initialized")
            continue

        # Change to service directory
        original_cwd = os.getcwd()
        os.chdir(service_path)

        try:
            # Set PYTHONPATH for this service
            os.environ["PYTHONPATH"] = str(service_path.absolute())

            # Generate migration
            cmd = 'alembic revision --autogenerate -m "Initial migration"'
            success, output = run_command(cmd)

            if success:
                print(f"   ✅ Migration generated successfully")
                results[service] = (True, "Migration generated")
            else:
                print(f"   ❌ Failed to generate migration: {output}")
                results[service] = (False, output)

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results[service] = (False, str(e))
        finally:
            os.chdir(original_cwd)

    return results


def apply_migrations():
    """Apply migrations to the database."""

    services = [
        "ppl-meta-node",
        "ppl-meta-media",
        "ppl-meta-gateway",
        "ppl-meta-orchestrator",
    ]
    results = {}

    for service in services:
        service_path = Path(service)
        if not service_path.exists():
            continue

        print(f"\n📋 Applying migrations for {service}...")

        # Change to service directory
        original_cwd = os.getcwd()
        os.chdir(service_path)

        try:
            # Set PYTHONPATH for this service
            os.environ["PYTHONPATH"] = str(service_path.absolute())

            # Apply migrations
            cmd = "alembic upgrade head"
            success, output = run_command(cmd)

            if success:
                print(f"   ✅ Migrations applied successfully")
                results[service] = (True, "Migrations applied")
            else:
                print(f"   ❌ Failed to apply migrations: {output}")
                results[service] = (False, output)

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results[service] = (False, str(e))
        finally:
            os.chdir(original_cwd)

    return results


def main():
    """Main function."""

    print("🚀 PPL Meta Platform Database Migration Generator")
    print("=" * 55)

    # Check if we have database connectivity
    print("\n🔍 Checking database connectivity...")
    success, output = run_command(
        "docker exec ppl-postgres pg_isready -U nickadmin -d ppl_db"
    )
    if not success:
        print(f"   ❌ Database not ready: {output}")
        print(
            "   💡 Please ensure PostgreSQL is running: docker-compose -f docker-compose.minimal.yml up -d postgres"
        )
        sys.exit(1)

    print("   ✅ Database is ready")

    if len(sys.argv) > 1 and sys.argv[1] == "apply":
        print("\n📦 Applying existing migrations...")
        results = apply_migrations()
    else:
        print("\n📦 Generating initial migrations...")
        results = generate_migrations()

    # Summary
    print("\n📊 Migration Summary:")
    print("-" * 30)
    for service, (success, message) in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {service}: {message}")

    # Next steps
    if not any(success for success, _ in results.values()):
        print("\n❌ No migrations were successful. Please check the errors above.")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "apply":
        print("\n🎉 Database migrations applied successfully!")
        print("\n📝 Next steps:")
        print("   1. Validate that your applications can connect to the database")
        print("   2. Test basic CRUD operations")
        print("   3. Set up CI/CD integration for future migrations")
    else:
        print("\n🎉 Migration files generated successfully!")
        print("\n📝 Next steps:")
        print("   1. Review the generated migration files")
        print("   2. Run: python generate_migrations.py apply")
        print("   3. Test your application with the new schema")


if __name__ == "__main__":
    main()
