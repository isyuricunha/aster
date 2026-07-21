#!/bin/sh
set -eu

api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

json_field() {
  field="$1"
  python -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "${field}"
}

test "$(curl -sS -o /dev/null -w '%{http_code}' "${api_url}/api/agents")" = "401"
test "$(curl -sS -o /dev/null -w '%{http_code}' "${web_url}/api/agents")" = "401"

agent_json="$(curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -d '{
    "name": "Stage 17 bounded operator",
    "description": "Validate durable bounded agent controls.",
    "goal": "Return a concise status report without external actions.",
    "enabled": true,
    "paused": false,
    "trigger_type": "manual",
    "timezone": "UTC",
    "schedule": {},
    "model_id": null,
    "persona_id": null,
    "use_default_persona": false,
    "memory_enabled": false,
    "rag_enabled": false,
    "max_steps": 8,
    "max_model_calls": 6,
    "max_tool_calls": 4,
    "max_runtime_seconds": 300,
    "max_estimated_tokens": 50000,
    "max_estimated_cost_microusd": null,
    "input_cost_per_million_microusd": null,
    "output_cost_per_million_microusd": null,
    "notify_on_completion": true,
    "notify_on_failure": true,
    "tools": [],
    "communication_scopes": [],
    "knowledge_scopes": []
  }' \
  "${web_url}/api/agents")"
agent_id="$(printf '%s' "${agent_json}" | json_field id)"
test -n "${agent_id}"
printf '%s' "${agent_json}" | grep --quiet '"max_steps":8'
printf '%s' "${agent_json}" | grep --quiet '"tools":\[\]'

run_json="$(curl -fsS -b "${cookie_jar}" \
  -H "Origin: ${origin}" \
  -X POST \
  "${web_url}/api/agents/${agent_id}/run")"
run_id="$(printf '%s' "${run_json}" | json_field id)"
printf '%s' "${run_json}" | grep --quiet '"status":"queued"'

curl -fsS -b "${cookie_jar}" -H "Origin: ${origin}" -X POST \
  "${web_url}/api/agent-runs/${run_id}/pause" | grep --quiet '"status":"paused"'
curl -fsS -b "${cookie_jar}" -H "Origin: ${origin}" -X POST \
  "${web_url}/api/agent-runs/${run_id}/resume" | grep --quiet '"status":"queued"'
curl -fsS -b "${cookie_jar}" -H "Origin: ${origin}" -X POST \
  "${web_url}/api/agent-runs/${run_id}/cancel" | grep --quiet '"status":"cancelled"'

account_json="$(curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -d '{
    "name": "Stage 17 event inbox",
    "kind": "imap",
    "enabled": false,
    "config": {
      "host": "imap.example.test",
      "port": 993,
      "security": "ssl",
      "folder": "INBOX"
    },
    "credentials": {},
    "poll_interval_seconds": 60
  }' \
  "${web_url}/api/communication-accounts")"
account_id="$(printf '%s' "${account_json}" | json_field id)"
test -n "${account_id}"
printf '%s' "${account_json}" | grep --quiet '"credential_names":\[\]'

communication_agent_json="$(curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -d "{
    \"name\": \"Stage 17 event operator\",
    \"description\": \"Validate communication dispatch scopes.\",
    \"goal\": \"Summarize matching future messages.\",
    \"enabled\": true,
    \"paused\": false,
    \"trigger_type\": \"communication\",
    \"timezone\": \"UTC\",
    \"schedule\": {},
    \"model_id\": null,
    \"persona_id\": null,
    \"use_default_persona\": false,
    \"memory_enabled\": false,
    \"rag_enabled\": false,
    \"max_steps\": 8,
    \"max_model_calls\": 6,
    \"max_tool_calls\": 4,
    \"max_runtime_seconds\": 300,
    \"max_estimated_tokens\": 50000,
    \"max_estimated_cost_microusd\": null,
    \"input_cost_per_million_microusd\": null,
    \"output_cost_per_million_microusd\": null,
    \"notify_on_completion\": true,
    \"notify_on_failure\": true,
    \"tools\": [],
    \"communication_scopes\": [{
      \"account_id\": \"${account_id}\",
      \"allow_read\": true,
      \"allow_reply\": false,
      \"reply_approval_policy\": \"always\"
    }],
    \"knowledge_scopes\": []
  }" \
  "${web_url}/api/agents")"
communication_agent_id="$(printf '%s' "${communication_agent_json}" | json_field id)"
test -n "${communication_agent_id}"
printf '%s' "${communication_agent_json}" | grep --quiet '"allow_read":true'
printf '%s' "${communication_agent_json}" | grep --quiet '"allow_reply":false'

rule_json="$(curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -d "{
    \"name\": \"Stage 17 trusted event\",
    \"agent_id\": \"${communication_agent_id}\",
    \"account_id\": \"${account_id}\",
    \"enabled\": true,
    \"sender_pattern\": \"*@example.test\",
    \"source_ids\": [\"INBOX\"],
    \"body_contains\": \"agent\",
    \"require_mention\": false
  }" \
  "${web_url}/api/agent-communication-rules")"
printf '%s' "${rule_json}" | grep --quiet '"agent_name":"Stage 17 event operator"'
printf '%s' "${rule_json}" | grep --quiet '"account_name":"Stage 17 event inbox"'

curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -X PUT \
  -d '{"emergency_stop":true,"reason":"Stage 17 CI stop."}' \
  "${web_url}/api/agent-control" | grep --quiet '"emergency_stop":true'

test "$(curl -sS -o /dev/null -w '%{http_code}' -b "${cookie_jar}" \
  -H "Origin: ${origin}" -X POST \
  "${web_url}/api/agents/${agent_id}/run")" = "409"

curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -X PUT \
  -d '{"emergency_stop":false,"reason":""}' \
  "${web_url}/api/agent-control" | grep --quiet '"emergency_stop":false'

curl -fsS -b "${cookie_jar}" "${web_url}/api/agents" \
  | grep --quiet 'Stage 17 bounded operator'
curl -fsS -b "${cookie_jar}" "${web_url}/api/agent-runs?limit=100" \
  | grep --quiet '"status":"cancelled"'
curl -fsS -b "${cookie_jar}" "${web_url}/api/agent-communication-rules" \
  | grep --quiet 'Stage 17 trusted event'
curl -fsS -b "${cookie_jar}" "${web_url}/agents" \
  | grep --quiet 'Agents'

docker compose exec -T api alembic current | grep --quiet '0018_skills'
docker compose config | grep --quiet 'ASTER_AGENT_LEASE_SECONDS'
docker compose config | grep --quiet 'ASTER_AGENT_LOOP_REPEAT_LIMIT'
