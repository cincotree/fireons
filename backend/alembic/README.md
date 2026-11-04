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

## Backward compatible migrations

The release script (`scripts/deploy-api.sh`) applies migrations to the production database before the new code is published and smoke-tested. If the smoke test fails, the alias stays on the previous code while the schema is already ahead. Every migration must therefore work with both the previous and the new release:

- Add columns as nullable or with a default. Make them required in a later release.
- Do not drop or rename a column or table in the same release that stops using it. Ship the code change first, then drop it in the next release.
- Add new tables and indexes freely. Create large indexes concurrently.
- Backfill data in a separate step from the schema change.

There is no automatic rollback. To undo a release, run the Release workflow with an older ref, which republishes that code against the current schema.

## Tips

- Always review auto-generated migrations before applying
- Never edit applied migrations - create a new one instead
- Test on development database first
- Include migrations in version control
