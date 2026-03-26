"""Check database health — verify all models exist and are queryable."""

import sys
from typing import Protocol, cast

from django.core.management.base import BaseCommand
from django.db import connection


class _ManagerLike(Protocol):
    def exists(self) -> bool: ...


class Command(BaseCommand):
    help = "Verify all Django models exist in the database and are queryable"

    def handle(self, *args: str, **options: object) -> None:
        """Run health checks."""
        self.stdout.write("=" * 60)
        self.stdout.write("DATABASE HEALTH CHECK")
        self.stdout.write("=" * 60)

        errors: list[str] = []

        # 1: Connection
        self.stdout.write("Checking database connection...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.stdout.write(self.style.SUCCESS("✓ Database connection OK"))
        except Exception as e:
            errors.append(f"Database connection failed: {e}")
            self.stdout.write(self.style.ERROR(f"✗ Database connection failed: {e}"))

        # 2: Pending migrations
        self.stdout.write("Checking migrations...")
        try:
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if plan:
                errors.append(f"Unapplied migrations: {len(plan)} pending")
                self.stdout.write(self.style.ERROR(f"✗ {len(plan)} unapplied migrations found"))
                for migration, _ in plan:
                    self.stdout.write(f"  - {migration}")
            else:
                self.stdout.write(self.style.SUCCESS("✓ All migrations applied"))
        except Exception as e:
            errors.append(f"Migration check failed: {e}")
            self.stdout.write(self.style.ERROR(f"✗ Migration check failed: {e}"))

        # 3: Core model queries
        self.stdout.write("Checking core models...")
        try:
            from core.models import BotState, DiscordTask, UserGroups
            from team.models import LinkRateLimit, LinkToken

            for model_cls in (UserGroups, DiscordTask, BotState, LinkToken, LinkRateLimit):
                name = cast(type, model_cls).__name__
                try:
                    cast(_ManagerLike, model_cls.objects).exists()
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {name}"))
                except Exception as e:
                    errors.append(f"{name}: {str(e)[:100]}")
                    self.stdout.write(self.style.ERROR(f"  ✗ {name}: {str(e)[:100]}"))
        except Exception as e:
            errors.append(f"Model import failed: {e}")
            self.stdout.write(self.style.ERROR(f"✗ Model import failed: {e}"))

        # 4: View imports
        self.stdout.write("Checking view imports...")
        try:
            from core import oauth, views

            if not callable(views.health_check):
                raise RuntimeError("views.health_check is not callable")
            if not callable(views.auth_198f_initiate):
                raise RuntimeError("views.auth_198f_initiate is not callable")
            if not callable(oauth.oauth_login):
                raise RuntimeError("oauth.oauth_login is not callable")

            self.stdout.write(self.style.SUCCESS("✓ View imports OK"))
        except Exception as e:
            errors.append(f"View import failed: {e}")
            self.stdout.write(self.style.ERROR(f"✗ View import failed: {e}"))

        # Summary
        self.stdout.write("=" * 60)
        if errors:
            self.stdout.write(self.style.ERROR(f"FAILED: {len(errors)} error(s) found"))
            for err in errors:
                self.stdout.write(f"  • {err}")
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("SUCCESS: All checks passed"))
            sys.exit(0)
