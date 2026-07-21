#!/bin/sh
set -eu

api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

# Verify the Skills API remains private even when a prior contract logged out the CI owner.
test "$(curl -sS -o /dev/null -w '%{http_code}' "${api_url}/api/skills")" = "401"
test "$(curl -sS -o /dev/null -w '%{http_code}' "${web_url}/api/skills")" = "401"

# Stage 12 deliberately revokes the shared session. Authenticate explicitly so this
# contract is independent of the order in which the stack checks are executed.
curl -fsS \
  -b "${cookie_jar}" \
  -c "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -d '{"username":"owner","password":"correct horse battery staple"}' \
  "${web_url}/api/auth/login" >/dev/null

preferences="$(curl -fsS -b "${cookie_jar}" "${web_url}/api/skill-audit-preferences")"
printf '%s' "${preferences}" | python -c \
  'import json,sys; p=json.load(sys.stdin); assert p["auto_approve_threshold"] == 85; assert p["max_self_edit_attempts"] == 2; assert p["max_skills_per_run"] == 10; assert p["teacher_rewrite_enabled"] is False'

starter_skills="$(curl -fsS -b "${cookie_jar}" "${web_url}/api/skills")"
printf '%s' "${starter_skills}" | python -c \
  'import json,sys; p=json.load(sys.stdin); s=next(x for x in p if x["name"] == "Concise Summarizer"); assert s["status"] == "draft"; assert len(s["test_cases"]) == 2; assert "starter-template" in s["tags"]'

first_skill_id=""
index=1
while [ "${index}" -le 5 ]; do
  skill="$(curl -fsS -b "${cookie_jar}" \
    -H 'Content-Type: application/json' \
    -H "Origin: ${origin}" \
    -d "{\"name\":\"Stage 18 skill ${index}\",\"description\":\"Bounded CI skill.\",\"instructions\":\"Handle only Stage 18 input ${index} and never invent external actions.\",\"source_type\":\"manual\",\"tags\":[\"ci\"],\"trigger_phrases\":[\"stage 18 skill ${index}\"],\"test_cases\":[{\"input\":\"Stage 18 input ${index}\",\"expected\":\"Return only the bounded result.\"}]}" \
    "${web_url}/api/skills")"
  printf '%s' "${skill}" | python -c \
    'import json,sys; p=json.load(sys.stdin); assert p["status"] == "draft"; assert p["audit_status"] == "pending"; assert p["content_revision"] == 1'
  if [ -z "${first_skill_id}" ]; then
    first_skill_id="$(printf '%s' "${skill}" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  fi
  index=$((index + 1))
done

skills="$(curl -fsS -b "${cookie_jar}" "${web_url}/api/skills")"
printf '%s' "${skills}" | python -c \
  'import json,sys; p=json.load(sys.stdin); assert len([s for s in p if s["name"].startswith("Stage 18 skill")]) == 5'

tasks="$(curl -fsS -b "${cookie_jar}" "${web_url}/api/tasks")"
printf '%s' "${tasks}" | python -c \
  'import json,sys; p=json.load(sys.stdin); task=next(x for x in p if x["builtin_key"] == "skills_audit"); assert task["enabled"] is True; assert task["state"]["availability"] == "ready"; assert task["schedule"]["display_schedule"] == "Every 5 skills added"'

updated="$(curl -fsS -b "${cookie_jar}" \
  -H 'Content-Type: application/json' \
  -H "Origin: ${origin}" \
  -X PUT \
  -d '{"name":"Stage 18 skill 1 revised","description":"Bounded CI skill.","instructions":"Handle only the revised Stage 18 input and never invent external actions.","source_type":"manual","tags":["ci","revised"],"trigger_phrases":["stage 18 revised skill"],"test_cases":[{"input":"Revised Stage 18 input","expected":"Return only the bounded result."}]}' \
  "${web_url}/api/skills/${first_skill_id}")"
printf '%s' "${updated}" | python -c \
  'import json,sys; p=json.load(sys.stdin); assert p["content_revision"] == 2; assert p["audit_status"] == "pending"; assert p["status"] == "draft"'

curl -fsS -b "${cookie_jar}" "${web_url}/skills" | grep --quiet 'Skills'
curl -fsS "${api_url}/openapi.json" | python -c \
  'import json,sys; paths=json.load(sys.stdin)["paths"]; required=["/api/skills","/api/skills/{skill_id}","/api/skills/{skill_id}/audit","/api/skill-audit-attempts","/api/skill-audit-preferences"]; assert all(path in paths for path in required)'

docker compose exec -T api alembic current | grep --quiet '0020_communication_subject_text'
