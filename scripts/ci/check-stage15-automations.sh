#!/bin/sh
set -eu

web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

# Private task and automation surfaces must remain authenticated.
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "${web_url}/api/automations")" = "401"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "${web_url}/api/tasks")" = "401"

docker compose exec -T worker test -f /tmp/aster-worker-ready

integration_payload="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"name":"CI Mail","kind":"smtp","enabled":true,"config":{"host":"smtp.invalid","port":587,"security":"starttls","from_address":"aster@example.com"},"credentials":{"username":"ci-owner","password":"never-return-this"}}' \
  "${web_url}/api/integrations")"

integration_id="$(printf '%s' "${integration_payload}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["kind"] == "smtp"; assert payload["credential_names"] == ["password", "username"]; print(payload["id"])')"

test -n "${integration_id}"
if printf '%s' "${integration_payload}" | grep --quiet 'never-return-this'; then
  echo "Integration response exposed a credential" >&2
  exit 1
fi

automation_payload="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"name":"CI Webhook","description":"Stage 15 stack check","instruction":"Summarize the trigger payload.","enabled":true,"trigger_type":"webhook","timezone":"UTC","schedule":{},"model_id":null,"persona_id":null,"use_default_persona":false,"notify_on_success":true,"notify_on_failure":true,"max_attempts":1,"retry_delay_seconds":0,"timeout_seconds":30,"deliveries":[]}' \
  "${web_url}/api/automations")"

automation_values="$(printf '%s' "${automation_payload}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["trigger_type"] == "webhook"; assert payload["webhook_configured"] is True; assert payload["webhook_token"]; assert payload["webhook_token"] not in payload["webhook_path"]; print(payload["id"] + "|" + payload["webhook_token"])')"
automation_id="${automation_values%%|*}"
webhook_token="${automation_values#*|}"
webhook_url="${web_url}/api/webhooks/${automation_id}"

first_delivery="$(curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --header "X-Aster-Webhook-Token: ${webhook_token}" \
  --header 'X-Aster-Delivery: ci-delivery-001' \
  --data '{"event":"deployment","state":"green"}' \
  "${webhook_url}")"

run_id="$(printf '%s' "${first_delivery}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["status"] == "accepted"; assert payload["run_id"]; print(payload["run_id"])')"

duplicate_delivery="$(curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --header "X-Aster-Webhook-Token: ${webhook_token}" \
  --header 'X-Aster-Delivery: ci-delivery-001' \
  --data '{"event":"deployment","state":"green"}' \
  "${webhook_url}")"
printf '%s' "${duplicate_delivery}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload == {"status":"duplicate","run_id":None}'

test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --header 'Content-Type: application/json' \
  --header 'X-Aster-Webhook-Token: wrong-secret-value-with-enough-length' \
  --data '{}' \
  "${webhook_url}")" = "404"

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/automation-runs/${run_id}" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["trigger_source"] == "webhook"; assert payload["trigger_payload"]["event"] == "deployment"'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/automations" \
  | AUTOMATION_ID="${automation_id}" python -c 'import json, os, sys; items=json.load(sys.stdin); custom=[item for item in items if item["id"] == os.environ["AUTOMATION_ID"]]; assert len(custom) == 1; assert custom[0]["builtin_key"] is None; assert custom[0]["webhook_token"] is None; assert all(item["webhook_token"] is None for item in items)'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/tasks" \
  | python -c 'import json, sys; items=json.load(sys.stdin); builtins=[item for item in items if item["builtin_key"]]; assert len(builtins) == 7; assert any(item["builtin_key"] == "memory_tidy" for item in builtins); assert any(item["builtin_key"] == "skills_audit" and not item["enabled"] for item in builtins)'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/notifications" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert "items" in payload; assert "unread_count" in payload'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/tasks" >/dev/null
curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/automations" >/dev/null

curl --fail --silent --show-error "${api_url}/openapi.json" \
  | python -c 'import json, sys; paths=json.load(sys.stdin)["paths"]; required=["/api/integrations", "/api/integrations/{integration_id}/test", "/api/automations", "/api/automations/{automation_id}/run", "/api/tasks", "/api/tasks/{task_id}/enabled", "/api/tasks/{task_id}/run", "/api/automation-runs", "/api/automation-runs/{run_id}/cancel", "/api/automation-runs/{run_id}/retry", "/api/notifications", "/api/webhooks/{automation_id}"]; assert all(path in paths for path in required); assert "/api/webhooks/{token}" not in paths'
