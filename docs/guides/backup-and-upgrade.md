# Backup and upgrade

A complete Aster backup contains:

1. PostgreSQL data;
2. the private `aster-media` volume;
3. the deployment `.env`, especially `ASTER_ENCRYPTION_KEY`.

The database contains application state and encrypted credentials. The media volume contains generated images, image inputs, and communication attachments.

## Back up bundled PostgreSQL

```bash
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > aster-backup.sql
```

For external PostgreSQL, use the backup process provided by the database host.

## Back up private media

Find the Compose volume:

```bash
docker volume ls --filter name=aster-media
```

Create a tar archive through a temporary container:

```bash
docker run --rm \
  -v aster_aster-media:/source:ro \
  -v "$PWD":/backup \
  alpine \
  tar -czf /backup/aster-media.tar.gz -C /source .
```

The exact volume name may include the Compose project prefix. Use the value returned by `docker volume ls`.

## Preserve the encryption key

Store the deployment `.env` securely. Credentials encrypted in PostgreSQL cannot be decrypted after `ASTER_ENCRYPTION_KEY` is lost or changed.

Do not commit `.env` or backup archives to the repository.

## Restore bundled PostgreSQL

Stop application services that write to the database:

```bash
docker compose stop web worker api
```

Restore into an empty target database:

```bash
cat aster-backup.sql | docker compose exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

For a non-empty database, recreate the database or use an appropriate `pg_restore` workflow before importing. Do not blindly apply a plain SQL dump over conflicting application data.

## Restore private media

```bash
docker run --rm \
  -v aster_aster-media:/target \
  -v "$PWD":/backup:ro \
  alpine \
  sh -c 'rm -rf /target/* && tar -xzf /backup/aster-media.tar.gz -C /target'
```

Confirm the volume name before running a destructive restore.

## Upgrade

Create fresh backups, then:

```bash
git switch main
git pull --ff-only origin main
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

The API applies pending Alembic migrations before readiness. The worker starts only after the API becomes healthy.

## Validate after upgrade

```bash
curl -fsS http://localhost:${API_PORT:-8000}/ready
docker compose exec -T api alembic current
docker compose exec -T worker test -f /tmp/aster-worker-ready
```

Then verify login, one existing conversation, private media, and any configured automation, communication, or agent integrations.

## Rollback

Application rollback is safe only when the checked-out code remains compatible with the current database schema.

For a guaranteed rollback:

1. stop the stack;
2. restore the matching database backup;
3. restore the matching media archive when necessary;
4. restore the matching `.env`;
5. check out the previous source revision;
6. rebuild the stack.

Never rotate the encryption key as part of an ordinary rollback.
