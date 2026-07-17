#!/bin/sh
set -eu

web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

curl --fail --silent --show-error "${web_url}/api/auth/status" \
  | grep --quiet '"setup_required":true'

test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "${web_url}/api/persona")" = "401"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "${web_url}/api/mcp-servers")" = "401"

curl --fail --silent --show-error \
  --cookie-jar "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"username":"owner","password":"correct horse battery staple"}' \
  "${web_url}/api/auth/setup" | grep --quiet '"username":"owner"'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/auth/status" | grep --quiet '"authenticated":true'

test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"username":"another","password":"another secure password"}' \
  "${web_url}/api/auth/setup")" = "409"

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/model-endpoints" >/dev/null
curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/model-routing" | grep --quiet '"fallbacks":\[\]'
curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/persona" | grep --quiet '"name":"Migrated Assistant"'
curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/personas" | grep --quiet '"name":"Migrated Assistant"'
curl --fail --silent --show-error --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"user_message":"Hello"}' \
  "${web_url}/api/message-composition/preview" \
  | grep --quiet 'Preserve these legacy instructions.'

persona_id="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"name":"CI Persona","description":"Smoke test","instructions":"Be exact.","enabled":true,"instruction_role":"developer"}' \
  "${web_url}/api/personas" \
  | python -c 'import json, sys; print(json.load(sys.stdin)["id"])')"

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --request PUT \
  --data "{\"default_persona_id\":\"${persona_id}\"}" \
  "${web_url}/api/persona-preferences" \
  | grep --quiet '"name":"CI Persona"'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data "{\"user_message\":\"Hello\",\"persona_id\":\"${persona_id}\",\"use_default_persona\":false}" \
  "${web_url}/api/message-composition/preview" \
  | grep --quiet 'Your name is CI Persona'

conversation_id="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"title":"CI chat"}' \
  "${web_url}/api/conversations" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["persona"]["name"] == "CI Persona"; print(payload["id"])')"

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/conversations/${conversation_id}" \
  | grep --quiet '"title":"CI chat"'

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"format":"aster-conversation","version":1,"title":"Imported CI chat","messages":[{"role":"user","content":"Searchable import","status":"completed","error_message":null,"model_id":null}]}' \
  "${web_url}/api/conversations/import" \
  | grep --quiet '"title":"Imported CI chat"'

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --data '{"format":"aster-conversation","version":2,"title":"Snapshot import","persona":{"source_persona_id":null,"name":"Exported Persona","description":"Portable snapshot","instructions":"Stay portable.","instruction_role":"system"},"messages":[]}' \
  "${web_url}/api/conversations/import" \
  | grep --quiet '"name":"Exported Persona"'

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/api/conversations?query=Searchable" \
  | grep --quiet '"title":"Imported CI chat"'

curl --fail --silent --show-error "${api_url}/openapi.json" >/dev/null
