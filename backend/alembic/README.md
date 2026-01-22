# Database Migrations

Alembic manages database schema migrations for this project.

## Common Commands

```bash
uv run alembic upgrade head                               # Apply all migrations
uv run alembic downgrade -1                               # Rollback one migration
uv run alembic revision --autogenerate -m "description"   # Create new migration
uv run alembic current                                    # View current version
uv run alembic history                                    # View history
```

## Workflow

1. Edit models in `database/models.py`
2. Generate migration: `uv run alembic revision --autogenerate -m "add_field"`
3. Review generated file in `alembic/versions/`
4. Apply migration: `uv run alembic upgrade head`
5. Commit both model changes and migration file

## Tips

- Always review auto-generated migrations before applying
- Never edit applied migrations - create a new one instead
- Test on development database first
- Include migrations in version control
