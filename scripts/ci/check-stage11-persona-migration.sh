#!/bin/sh
set -eu

legacy_conversation_id="00000000-0000-0000-0000-000000000111"

docker compose exec -T api alembic downgrade 0007_model_profiles

docker compose exec -T postgres sh -lc \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<SQL
UPDATE persona_settings
SET
  name = 'Migrated Assistant',
  instructions = 'Preserve these legacy instructions.',
  enabled = true,
  instruction_role = 'developer'
WHERE id = 1;

INSERT INTO conversations (id, title, created_at, updated_at)
VALUES (
  '${legacy_conversation_id}',
  'Legacy conversation',
  now(),
  now()
);
SQL

docker compose exec -T api alembic upgrade head

persona_result="$(
  docker compose exec -T postgres sh -lc \
    'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT name || '|' || instructions
FROM personas
WHERE name = 'Migrated Assistant';
SQL
)"
persona_result="$(printf '%s' "${persona_result}" | tr -d '\r')"
test "${persona_result}" = "Migrated Assistant|Preserve these legacy instructions."

default_result="$(
  docker compose exec -T postgres sh -lc \
    'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT personas.name
FROM persona_preferences
JOIN personas ON personas.id = persona_preferences.default_persona_id
WHERE persona_preferences.id = 1;
SQL
)"
default_result="$(printf '%s' "${default_result}" | tr -d '\r')"
test "${default_result}" = "Migrated Assistant"

snapshot_result="$(
  docker compose exec -T postgres sh -lc \
    'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT persona_name || '|' || persona_instructions
FROM conversations
WHERE id = '00000000-0000-0000-0000-000000000111';
SQL
)"
snapshot_result="$(printf '%s' "${snapshot_result}" | tr -d '\r')"
test "${snapshot_result}" = "Migrated Assistant|Preserve these legacy instructions."

retrieval_result="$(
  docker compose exec -T postgres sh -lc \
    'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT memory_enabled || '|' || rag_enabled
FROM conversation_retrieval_settings
WHERE conversation_id = '00000000-0000-0000-0000-000000000111';
SQL
)"
retrieval_result="$(printf '%s' "${retrieval_result}" | tr -d '\r')"
test "${retrieval_result}" = "true|true" || test "${retrieval_result}" = "t|t"

instruction_role_result="$(
  docker compose exec -T postgres sh -lc \
    'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT column_default || '|' || is_nullable
FROM information_schema.columns
WHERE table_name = 'model_profiles'
  AND column_name = 'instruction_role';
SQL
)"
instruction_role_result="$(printf '%s' "${instruction_role_result}" | tr -d '\r')"
printf '%s' "${instruction_role_result}" | grep --quiet "system"
printf '%s' "${instruction_role_result}" | grep --quiet "NO"

docker compose exec -T api alembic current | grep --quiet '0014_model_instruction_roles'
