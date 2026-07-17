#!/bin/sh
set -eu

web_url="${ASTER_CI_WEB_URL:-http://localhost:3000}"
api_url="${ASTER_CI_API_URL:-http://localhost:8000}"
cookie_jar="${ASTER_CI_COOKIE_JAR:-/tmp/aster.cookies}"
origin="${ASTER_CI_ORIGIN:-http://localhost:3000}"

preferences_payload="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  "${web_url}/api/model-preferences")"

model_id="$(printf '%s' "${preferences_payload}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["primary"] is not None; print(payload["primary"]["id"])')"

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --request PUT \
  --data "{\"primary_model_id\":\"${model_id}\",\"utility_model_id\":null,\"image_model_id\":\"${model_id}\"}" \
  "${web_url}/api/model-preferences" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["image"]["id"] == payload["primary"]["id"]'

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: application/json' \
  --header "Origin: ${origin}" \
  --request PUT \
  --data '{"supports_generation":true,"supports_editing":true,"supports_multiple_inputs":true,"supports_masks":true,"max_input_images":4,"default_size":"1024x1024","default_quality":"high","default_output_format":"png","default_background":null,"default_count":1,"default_input_fidelity":"high","provider_parameters":{"style":"natural"}}' \
  "${web_url}/api/image-model-profiles/${model_id}" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["supports_generation"] is True; assert payload["supports_editing"] is True; assert payload["max_input_images"] == 4; assert payload["provider_parameters"] == {"style":"natural"}'

python - <<'PY'
import base64
from pathlib import Path

Path("/tmp/aster-stage14.png").write_bytes(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlK7YQAAAAASUVORK5CYII="
))
PY

asset_payload="$(curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header 'Content-Type: image/png' \
  --header "Origin: ${origin}" \
  --data-binary @/tmp/aster-stage14.png \
  "${web_url}/api/media-assets/uploads?filename=stage14-ci.png")"

asset_id="$(printf '%s' "${asset_payload}" | python -c \
  'import json, sys; payload=json.load(sys.stdin); assert payload["source_type"] == "upload"; assert payload["media_type"] == "image/png"; assert payload["width"] == 1 and payload["height"] == 1; print(payload["id"])')"

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --dump-header /tmp/aster-stage14-headers \
  "${web_url}/api/media-assets/${asset_id}/content" \
  --output /tmp/aster-stage14-output.png

cmp /tmp/aster-stage14.png /tmp/aster-stage14-output.png
grep -i --quiet '^x-content-type-options: nosniff' /tmp/aster-stage14-headers

test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "${web_url}/api/media-assets/${asset_id}/content")" = "401"

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  "${web_url}/api/image-gallery" \
  | python -c 'import json, sys; payload=json.load(sys.stdin); assert payload["total"] == 0; assert payload["items"] == []'

curl --fail --silent --show-error \
  --cookie "${cookie_jar}" \
  --header "Origin: ${origin}" \
  --request DELETE \
  "${web_url}/api/media-assets/${asset_id}"

test "$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --cookie "${cookie_jar}" "${web_url}/api/media-assets/${asset_id}/content")" = "404"

curl --fail --silent --show-error --cookie "${cookie_jar}" \
  "${web_url}/images" >/dev/null

curl --fail --silent --show-error "${api_url}/openapi.json" \
  | python -c 'import json, sys; paths=json.load(sys.stdin)["paths"]; required=["/api/image-model-profiles", "/api/image-model-profiles/{model_id}", "/api/media-assets/uploads", "/api/media-assets/{asset_id}/content", "/api/media-assets/{asset_id}", "/api/conversations/{conversation_id}/image-operations", "/api/image-operations/{operation_id}", "/api/image-gallery"]; assert all(path in paths for path in required)'
