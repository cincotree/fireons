# Database Migrations with Alembic

This project uses Alembic for managing database schema migrations.

## Quick Reference

### Common Commands

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Create a new migration (auto-generate from model changes)
uv run alembic revision --autogenerate -m "description_of_changes"

# View current migration version
uv run alembic current

# View migration history
uv run alembic history

# View all pending migrations
uv run alembic show head
```

## Workflow

### Making Model Changes

1. **Edit your models** in `database/models.py`
2. **Generate migration**: `uv run alembic revision --autogenerate -m "add_user_field"`
3. **Review the generated migration** in `alembic/versions/`
4. **Apply the migration**: `uv run alembic upgrade head`
5. **Commit both** the model changes AND the migration file

### Downgrading (Rollback)

```bash
# Rollback one migration
uv run alembic downgrade -1

# Rollback to a specific revision
uv run alembic downgrade <revision_id>

# Rollback all migrations
uv run alembic downgrade base
```

## Configuration

- **Database URL**: Set via `DATABASE_URL` environment variable (defaults to local PostgreSQL)
- **Models**: Imported from `database.models` in `alembic/env.py`
- **Async Support**: Configured to work with async SQLAlchemy

## Migration Files

Migration files are stored in `alembic/versions/` and follow this naming pattern:
```
<revision_id>_<description>.py
```

Each migration has:
- `upgrade()` - Applies changes to move forward
- `downgrade()` - Reverts changes to go backward

## Tips

1. **Always review auto-generated migrations** before applying them
2. **Test migrations** on a development database first
3. **Never edit applied migrations** - create a new one instead
4. **Include migrations in version control** alongside code changes
5. **Run migrations as part of deployment** process

## Troubleshooting

### "Target database is not up to date"
Your database is behind. Run: `uv run alembic upgrade head`

### "Can't locate revision identified by..."
Your database has migrations not in your codebase. Check git history or colleagues.

### Changes not detected
Ensure your models are imported in `alembic/env.py` and the server isn't caching.

## Example: Adding a New Field

1. Edit `database/models.py`:
```python
class User(Base):
    # ... existing fields
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
```

2. Generate migration:
```bash
uv run alembic revision --autogenerate -m "add_phone_number_to_users"
```

3. Review the generated file in `alembic/versions/`

4. Apply migration:
```bash
uv run alembic upgrade head
```

Done! Your database now has the `phone_number` column.
