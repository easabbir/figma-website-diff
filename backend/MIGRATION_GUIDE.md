# Migration Guide - Alembic Setup

## Overview
This guide covers migrating from raw SQL migrations to Alembic-managed migrations.

## Prerequisites
- PostgreSQL database running
- DATABASE_URL environment variable set
- Python dependencies installed (including alembic)

## Initial Setup (For Existing Database)

### Step 1: Verify Current Database State
```bash
# Connect to your database and verify tables exist
psql $DATABASE_URL -c "\dt"
```

You should see tables: users, comparisons, viewport_results, jobs, otp_tokens, reset_tokens

### Step 2: Stamp Current State
Since your database already has tables created, we need to tell Alembic the current state:

```bash
# Mark the database as being at the "head" revision
alembic stamp head
```

This creates the `alembic_version` table without running any migrations.

### Step 3: Verify Alembic Setup
```bash
# Check current revision
alembic current

# View migration history
alembic history
```

## Creating New Migrations

### Auto-generate Migration
When you modify models in `app/db/models.py`:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "descriptive message"

# Example:
alembic revision --autogenerate -m "add profile_image to users"
```

### Manual Migration
For data migrations or complex changes:

```bash
# Create empty migration file
alembic revision -m "migrate user data"
```

Then edit the generated file in `alembic/versions/`.

## Applying Migrations

### Upgrade to Latest
```bash
# Apply all pending migrations
alembic upgrade head
```

### Upgrade One Step
```bash
# Apply just the next migration
alembic upgrade +1
```

### Upgrade to Specific Revision
```bash
# Upgrade to specific revision
alembic upgrade <revision_id>
```

## Rolling Back Migrations

### Downgrade One Step
```bash
# Revert last migration
alembic downgrade -1
```

### Downgrade to Specific Revision
```bash
# Downgrade to specific revision
alembic downgrade <revision_id>
```

### Downgrade All
```bash
# Revert all migrations (dangerous!)
alembic downgrade base
```

## Common Workflows

### Adding a New Column
1. Add column to model in `app/db/models.py`:
   ```python
   class User(Base, TimestampMixin):
       # ... existing fields
       new_column = Column(String(100), nullable=True)
   ```

2. Generate migration:
   ```bash
   alembic revision --autogenerate -m "add new_column to users"
   ```

3. Review generated migration in `alembic/versions/`

4. Apply migration:
   ```bash
   alembic upgrade head
   ```

### Renaming a Column
1. Create manual migration:
   ```bash
   alembic revision -m "rename user column"
   ```

2. Edit the migration file:
   ```python
   def upgrade():
       op.alter_column('users', 'old_name', new_column_name='new_name')
   
   def downgrade():
       op.alter_column('users', 'new_name', new_column_name='old_name')
   ```

3. Update model in `app/db/models.py`

4. Apply migration:
   ```bash
   alembic upgrade head
   ```

### Adding an Index
1. Add index to model:
   ```python
   from sqlalchemy import Index
   
   class User(Base, TimestampMixin):
       # ... fields
       __table_args__ = (
           Index('ix_users_email_active', 'email', 'is_active'),
       )
   ```

2. Generate and apply migration:
   ```bash
   alembic revision --autogenerate -m "add index to users"
   alembic upgrade head
   ```

## Troubleshooting

### "Target database is not up to date"
```bash
# Check current revision
alembic current

# View available revisions
alembic history

# Upgrade to head
alembic upgrade head
```

### "Can't locate revision identified by"
```bash
# Stamp to a known good state
alembic stamp head
```

### Migration conflicts (multiple heads)
```bash
# List heads
alembic heads

# Merge heads
alembic merge <revision1> <revision2> -m "merge migrations"
```

### Database out of sync with models
```bash
# Generate migration to sync
alembic revision --autogenerate -m "sync database with models"

# Review the generated migration carefully
# Then apply:
alembic upgrade head
```

## Environment-Specific Migrations

### Development
```bash
# Use local DATABASE_URL
alembic upgrade head
```

### Staging
```bash
# Set staging DATABASE_URL
export DATABASE_URL="postgresql://user:pass@staging-db:5432/dbname"
alembic upgrade head
```

### Production
```bash
# ALWAYS test migrations in staging first!
# Backup database before running migrations
pg_dump $DATABASE_URL > backup.sql

# Run migrations
alembic upgrade head

# Verify application works
# If issues, rollback:
alembic downgrade -1
```

## Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test migrations** in development/staging before production
3. **Backup database** before production migrations
4. **Version control** all migration files
5. **Never edit applied migrations** - create a new one instead
6. **Use descriptive messages** for migration names
7. **Test rollback** (downgrade) before deploying
8. **Keep migrations small** and focused on one change

## Integration with CI/CD

### Pre-deployment Check
```bash
# Check for pending migrations
alembic check

# Dry-run (shows SQL without executing)
alembic upgrade head --sql
```

### Automated Deployment Script
```bash
#!/bin/bash
set -e

echo "Backing up database..."
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

echo "Running migrations..."
alembic upgrade head

echo "Verifying application..."
# Add health check here

echo "Migration complete!"
```

## Reverting from Alembic (Emergency)

If you need to revert to the old system:

1. Stop the application
2. Remove `alembic_version` table:
   ```sql
   DROP TABLE alembic_version;
   ```
3. Revert code changes
4. Restart application

## Support

For issues or questions:
- Check Alembic documentation: https://alembic.sqlalchemy.org/
- Review migration files in `alembic/versions/`
- Check application logs
- Verify DATABASE_URL is correct
