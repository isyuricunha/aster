#!/bin/sh
set -eu

web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

# Private automation surfaces must remain authenticated.
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "${web_url}/api/automations")" = "401"

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
  'import json, sys; payload=json.load(sys.stdin); assert payload["trigger_type"] == "webhook"; assert payload["webhook_configured"] is True; assert payload["webhook_token"]; print(payload["id"] + "|" + payload["webhook_token"])')"
automation_id="${automation_values%%|*}"
webhook_token="${automation_values#*|}"

first_delivery="$(curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --header 'X-Aster-Delivery: ci-delivery-001' \
  --data '{"event":"deployment","state":"green"}' \
  "${web_url}/api/webhooks/${webhook_token}")"

run_id="$(printf '%s' "${first_delivery}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["status"] == "accepted"; assert payload["run_id"]; print(payload["run_id"])')"

duplicate_delivery="$(curl --fail --silent --show-error \
  --header 'Content-Type: application/json' \
  --header 'X-Aster-Delivery: ci-delivery-001' \
  --data '{"event":"deployment","state":"green"}' \
  "${web_url}/api/webhooks/${webhook_token}")"
printf '%s' "${duplicate_delivery}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload == {"status":"duplicate","run_id":None}'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/automation-runs/${run_id}" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["trigger_source"] == "webhook"; assert payload["trigger_payload"]["event"] == "deployment"'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/automations" \
  | python -c 'import json, sys; items=json.load(sys.stdin); assert len(items) == 1; assert items[0]["webhook_token"] is None'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/notifications" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert "items" in payload; assert "unread_count" in payload'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/automations" >/dev/null

curl --fail --silent --show-error "${api_url}/openapi.json" \
  | python -c 'import json, sys; paths=json.load(sys.stdin)["paths"]; required=["/api/integrations", "/api/integrations/{integration_id}/test", "/api/automations", "/api/automations/{automation_id}/run", "/api/automation-runs", "/api/automation-runs/{run_id}/cancel", "/api/automation-runs/{run_id}/retry", "/api/notifications", "/api/webhooks/{token}"]; assert all(path in paths for path in required)'
