#!/bin/sh
set -eu

web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

mcp_payload="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"name":"CI MCP","transport":"streamable_http","url":"https://mcp.invalid/mcp","headers":{"Authorization":"Bearer ci-secret"},"enabled":true,"timeout_seconds":30}' \
  "${web_url}/api/mcp-servers")"

mcp_id="$(printf '%s' "${mcp_payload}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["header_names"] == ["Authorization"]; assert "ci-secret" not in str(payload); print(payload["id"])')"

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/mcp-servers/${mcp_id}" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["header_names"] == ["Authorization"]; assert "ci-secret" not in str(payload)'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  --header "Origin: ${origin}" \
  --request DELETE "${web_url}/api/mcp-servers/${mcp_id}"

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"format":"aster-conversation","version":3,"title":"Tool history import","messages":[{"role":"user","content":"Use a tool.","status":"completed","error_message":null,"model_id":null},{"role":"assistant","content":"","status":"completed","error_message":null,"model_id":"chat-model","tool_calls":[{"id":"call-ci","type":"function","function":{"name":"mcp_ci_echo","arguments":"{\"value\":\"portable\"}"}}]},{"role":"tool","content":"portable","status":"completed","error_message":null,"model_id":null,"tool_call_id":"call-ci","tool_name":"echo"},{"role":"assistant","content":"Portable result used.","status":"completed","error_message":null,"model_id":"chat-model"}]}' \
  "${web_url}/api/conversations/import" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["messages"][1]["tool_calls"][0]["id"] == "call-ci"; assert payload["messages"][2]["role"] == "tool"'

curl --fail --silent --show-error "${api_url}/openapi.json" \
  | python -c 'import json, sys; paths=json.load(sys.stdin)["paths"]; required=["/api/model-profiles/{model_id}", "/api/model-routing", "/api/personas", "/api/personas/{persona_id}", "/api/persona-preferences", "/api/conversations/import", "/api/conversations/{conversation_id}/tools", "/api/conversations/{conversation_id}/tool-executions", "/api/conversations/{conversation_id}/messages/{message_id}/edit-and-resend", "/api/conversations/{conversation_id}/messages/{message_id}/regenerate", "/api/messages/{message_id}/stop", "/api/mcp-servers", "/api/mcp-servers/{server_id}", "/api/mcp-servers/{server_id}/test", "/api/mcp-servers/{server_id}/sync", "/api/mcp-tools", "/api/mcp-tools/{tool_id}", "/api/tool-executions/{execution_id}/approve", "/api/tool-executions/{execution_id}/deny", "/api/auth/setup", "/api/auth/login", "/api/auth/password"]; assert all(path in paths for path in required)'

for path in / /settings/models /settings/persona /settings/tools /settings/account; do
  curl --fail --silent --show-error --cookie "${cookie_jar}" \
    "${web_url}${path}" >/dev/null
done

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  --cookie-jar "${cookie_jar}" \
  --header "Origin: ${origin}" \
  --request POST "${web_url}/api/auth/logout" >/dev/null

test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --cookie "${cookie_jar}" "${web_url}/api/auth/me")" = "401"
