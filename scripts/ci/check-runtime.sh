#!/bin/sh
set -eu

runtime_json="$(docker compose exec -T api python - <<'PY'
import json

from app.config import settings

print(json.dumps({
    "database_url": settings.database_url,
    "endpoint_timeout": settings.aster_endpoint_timeout_seconds,
    "stream_timeout": settings.aster_stream_timeout_seconds,
    "session_cookie_name": settings.aster_session_cookie_name,
    "session_secure": settings.aster_session_secure,
    "mcp_stdio_enabled": settings.aster_mcp_stdio_enabled,
    "mcp_timeout": settings.aster_mcp_timeout_seconds,
    "tool_max_rounds": settings.aster_tool_max_rounds,
    "tool_argument_max_characters": settings.aster_tool_argument_max_characters,
    "tool_result_max_characters": settings.aster_tool_result_max_characters,
    "memory_max_items": settings.aster_memory_max_items,
    "memory_suggestion_max_items": settings.aster_memory_suggestion_max_items,
    "rag_max_sources": settings.aster_rag_max_sources,
    "rag_context_max_characters": settings.aster_rag_context_max_characters,
    "rag_candidate_limit": settings.aster_rag_candidate_limit,
    "document_max_bytes": settings.aster_document_max_bytes,
    "document_max_characters": settings.aster_document_max_characters,
    "document_chunk_characters": settings.aster_document_chunk_characters,
    "document_chunk_overlap": settings.aster_document_chunk_overlap,
    "document_max_chunks": settings.aster_document_max_chunks,
    "embedding_batch_size": settings.aster_embedding_batch_size,
    "media_root": settings.aster_media_root,
    "image_timeout_seconds": settings.aster_image_timeout_seconds,
    "image_upload_max_bytes": settings.aster_image_upload_max_bytes,
    "image_output_max_bytes": settings.aster_image_output_max_bytes,
    "image_max_pixels": settings.aster_image_max_pixels,
    "image_max_inputs": settings.aster_image_max_inputs,
    "image_max_outputs": settings.aster_image_max_outputs,
    "automation_poll_seconds": settings.aster_automation_poll_seconds,
    "automation_lease_seconds": settings.aster_automation_lease_seconds,
    "automation_heartbeat_seconds": settings.aster_automation_heartbeat_seconds,
    "automation_scheduler_batch_size": settings.aster_automation_scheduler_batch_size,
    "automation_output_max_characters": settings.aster_automation_output_max_characters,
    "integration_timeout_seconds": settings.aster_integration_timeout_seconds,
    "webhook_max_bytes": settings.aster_webhook_max_bytes,
    "communication_lease_seconds": settings.aster_communication_lease_seconds,
    "communication_message_max_characters": settings.aster_communication_message_max_characters,
    "communication_attachment_max_bytes": settings.aster_communication_attachment_max_bytes,
    "communication_max_attachments": settings.aster_communication_max_attachments,
}))
PY
)"

printf '%s' "${runtime_json}" | grep --quiet 'postgresql+asyncpg://'
printf '%s' "${runtime_json}" | grep --quiet '"endpoint_timeout": 30.0'
printf '%s' "${runtime_json}" | grep --quiet '"stream_timeout": 120.0'
printf '%s' "${runtime_json}" | grep --quiet '"session_cookie_name": "aster_session"'
printf '%s' "${runtime_json}" | grep --quiet '"session_secure": false'
printf '%s' "${runtime_json}" | grep --quiet '"mcp_stdio_enabled": false'
printf '%s' "${runtime_json}" | grep --quiet '"mcp_timeout": 30.0'
printf '%s' "${runtime_json}" | grep --quiet '"tool_max_rounds": 8'
printf '%s' "${runtime_json}" | grep --quiet '"tool_argument_max_characters": 100000'
printf '%s' "${runtime_json}" | grep --quiet '"tool_result_max_characters": 100000'
printf '%s' "${runtime_json}" | grep --quiet '"memory_max_items": 12'
printf '%s' "${runtime_json}" | grep --quiet '"memory_suggestion_max_items": 8'
printf '%s' "${runtime_json}" | grep --quiet '"rag_max_sources": 8'
printf '%s' "${runtime_json}" | grep --quiet '"rag_context_max_characters": 24000'
printf '%s' "${runtime_json}" | grep --quiet '"rag_candidate_limit": 2000'
printf '%s' "${runtime_json}" | grep --quiet '"document_max_bytes": 5000000'
printf '%s' "${runtime_json}" | grep --quiet '"document_max_characters": 2000000'
printf '%s' "${runtime_json}" | grep --quiet '"document_chunk_characters": 1600'
printf '%s' "${runtime_json}" | grep --quiet '"document_chunk_overlap": 200'
printf '%s' "${runtime_json}" | grep --quiet '"document_max_chunks": 2000'
printf '%s' "${runtime_json}" | grep --quiet '"embedding_batch_size": 64'
printf '%s' "${runtime_json}" | grep --quiet '"media_root": "/var/lib/aster/media"'
printf '%s' "${runtime_json}" | grep --quiet '"image_timeout_seconds": 300.0'
printf '%s' "${runtime_json}" | grep --quiet '"image_upload_max_bytes": 20000000'
printf '%s' "${runtime_json}" | grep --quiet '"image_output_max_bytes": 25000000'
printf '%s' "${runtime_json}" | grep --quiet '"image_max_pixels": 40000000'
printf '%s' "${runtime_json}" | grep --quiet '"image_max_inputs": 8'
printf '%s' "${runtime_json}" | grep --quiet '"image_max_outputs": 4'
printf '%s' "${runtime_json}" | grep --quiet '"automation_poll_seconds": 2.0'
printf '%s' "${runtime_json}" | grep --quiet '"automation_lease_seconds": 120'
printf '%s' "${runtime_json}" | grep --quiet '"automation_heartbeat_seconds": 30'
printf '%s' "${runtime_json}" | grep --quiet '"automation_scheduler_batch_size": 25'
printf '%s' "${runtime_json}" | grep --quiet '"automation_output_max_characters": 100000'
printf '%s' "${runtime_json}" | grep --quiet '"integration_timeout_seconds": 30.0'
printf '%s' "${runtime_json}" | grep --quiet '"webhook_max_bytes": 1000000'
printf '%s' "${runtime_json}" | grep --quiet '"communication_lease_seconds": 180'
printf '%s' "${runtime_json}" | grep --quiet '"communication_message_max_characters": 200000'
printf '%s' "${runtime_json}" | grep --quiet '"communication_attachment_max_bytes": 15000000'
printf '%s' "${runtime_json}" | grep --quiet '"communication_max_attachments": 16'

docker compose exec -T worker test -f /tmp/aster-worker-ready
