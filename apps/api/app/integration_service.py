import asyncio
import json
import smtplib
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx

from app.automation_models import IntegrationConnection
from app.security import SecretCipher


class IntegrationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    destination: str


def encrypt_credentials(cipher: SecretCipher, values: dict[str, str]) -> str | None:
    if not values:
        return None
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return cipher.encrypt(payload)


def decrypt_credentials(cipher: SecretCipher, value: str | None) -> dict[str, str]:
    if value is None:
        return {}
    decoded = json.loads(cipher.decrypt(value))
    if not isinstance(decoded, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in decoded.items()
    ):
        raise IntegrationError("invalid_credentials", "Stored integration credentials are invalid.")
    return decoded


def validate_integration_config(kind: str, config: dict[str, object]) -> dict[str, object]:
    normalized = dict(config)
    if kind == "smtp":
        host = normalized.get("host")
        port = normalized.get("port", 587)
        security = normalized.get("security", "starttls")
        from_address = normalized.get("from_address")
        if not isinstance(host, str) or not host.strip():
            raise IntegrationError("invalid_configuration", "SMTP host is required.")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise IntegrationError("invalid_configuration", "SMTP port is invalid.")
        if security not in {"plain", "starttls", "ssl"}:
            raise IntegrationError("invalid_configuration", "SMTP security is invalid.")
        if not isinstance(from_address, str) or "@" not in from_address:
            raise IntegrationError("invalid_configuration", "SMTP from_address is required.")
        normalized.update(
            host=host.strip(),
            port=port,
            security=security,
            from_address=from_address.strip(),
        )
        return normalized
    if kind in {"caldav", "webhook"}:
        key = "calendar_url" if kind == "caldav" else "url"
        raw_url = normalized.get(key)
        if not isinstance(raw_url, str):
            raise IntegrationError("invalid_configuration", f"{key} is required.")
        parsed = urlsplit(raw_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise IntegrationError("invalid_configuration", f"{key} must use HTTP or HTTPS.")
        normalized[key] = raw_url.rstrip("/")
        if kind == "caldav":
            auth_type = normalized.get("auth_type", "basic")
            if auth_type not in {"none", "basic", "bearer"}:
                raise IntegrationError("invalid_configuration", "CalDAV auth_type is invalid.")
            normalized["auth_type"] = auth_type
        return normalized
    raise IntegrationError("invalid_configuration", "Unsupported integration kind.")


def _smtp_connect(config: dict[str, object], credentials: dict[str, str]) -> smtplib.SMTP:
    host = str(config["host"])
    port = int(config["port"])
    timeout = min(float(config.get("timeout_seconds", 30)), 120.0)
    security = str(config["security"])
    if security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            host,
            port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.ehlo()
        if security == "starttls":
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
    username = credentials.get("username")
    password = credentials.get("password")
    if username:
        client.login(username, password or "")
    return client


def _test_smtp(config: dict[str, object], credentials: dict[str, str]) -> None:
    client = _smtp_connect(config, credentials)
    try:
        code, _ = client.noop()
        if code >= 400:
            raise IntegrationError("connection_failed", f"SMTP NOOP returned {code}.")
    finally:
        try:
            client.quit()
        except smtplib.SMTPException:
            client.close()


def _send_email(
    config: dict[str, object],
    credentials: dict[str, str],
    *,
    recipients: list[str],
    subject: str,
    body: str,
) -> None:
    message = EmailMessage()
    message["From"] = str(config["from_address"])
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)
    client = _smtp_connect(config, credentials)
    try:
        client.send_message(message)
    finally:
        try:
            client.quit()
        except smtplib.SMTPException:
            client.close()


def _auth_headers(config: dict[str, object], credentials: dict[str, str]) -> dict[str, str]:
    reserved = {"username", "password", "token"}
    headers = {
        key: value
        for key, value in credentials.items()
        if key.casefold() not in reserved
    }
    auth_type = str(config.get("auth_type", "none"))
    if auth_type == "bearer" and credentials.get("token"):
        headers["Authorization"] = f"Bearer {credentials['token']}"
    return headers


def _basic_auth(config: dict[str, object], credentials: dict[str, str]) -> httpx.BasicAuth | None:
    if config.get("auth_type") != "basic":
        return None
    username = credentials.get("username")
    if not username:
        return None
    return httpx.BasicAuth(username, credentials.get("password", ""))


def _escape_ical(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _icalendar(
    *,
    uid: str,
    summary: str,
    description: str,
    start: datetime,
    duration_minutes: int,
) -> str:
    end = start + timedelta(minutes=duration_minutes)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Aster//Automation//EN",
            "CALSCALE:GREGORIAN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{start.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{_escape_ical(summary)}",
            f"DESCRIPTION:{_escape_ical(description)}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )


async def test_integration(
    integration: IntegrationConnection,
    *,
    cipher: SecretCipher,
    timeout_seconds: float,
) -> str:
    config = validate_integration_config(integration.kind, integration.config)
    credentials = decrypt_credentials(cipher, integration.encrypted_credentials)
    try:
        if integration.kind == "smtp":
            await asyncio.to_thread(_test_smtp, config, credentials)
            return "SMTP connection succeeded."
        url = str(
            config["calendar_url"] if integration.kind == "caldav" else config["url"]
        )
        method = "OPTIONS" if integration.kind == "caldav" else "POST"
        kwargs: dict[str, object] = {}
        if integration.kind == "caldav":
            kwargs["auth"] = _basic_auth(config, credentials)
        else:
            kwargs["json"] = {
                "type": "aster.integration_test",
                "sent_at": datetime.now(UTC).isoformat(),
            }
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.request(
                method,
                url,
                headers=_auth_headers(config, credentials),
                **kwargs,
            )
        if response.status_code >= 400:
            raise IntegrationError(
                "connection_failed",
                f"Integration returned HTTP {response.status_code}.",
            )
        return f"{integration.kind.upper()} connection succeeded."
    except IntegrationError:
        raise
    except (OSError, smtplib.SMTPException, httpx.HTTPError) as error:
        raise IntegrationError(
            "connection_failed", "The integration could not be reached."
        ) from error


async def deliver_email(
    integration: IntegrationConnection,
    *,
    cipher: SecretCipher,
    recipients: list[str],
    subject: str,
    body: str,
) -> DeliveryResult:
    if not recipients or any("@" not in item for item in recipients):
        raise IntegrationError("invalid_delivery", "Email recipients are invalid.")
    config = validate_integration_config("smtp", integration.config)
    credentials = decrypt_credentials(cipher, integration.encrypted_credentials)
    try:
        await asyncio.to_thread(
            _send_email,
            config,
            credentials,
            recipients=recipients,
            subject=subject,
            body=body,
        )
    except (OSError, smtplib.SMTPException) as error:
        raise IntegrationError("delivery_failed", "Email delivery failed.") from error
    return DeliveryResult(destination=", ".join(recipients))


async def deliver_webhook(
    integration: IntegrationConnection,
    *,
    cipher: SecretCipher,
    payload: dict[str, object],
    timeout_seconds: float,
) -> DeliveryResult:
    config = validate_integration_config("webhook", integration.config)
    credentials = decrypt_credentials(cipher, integration.encrypted_credentials)
    url = str(config["url"])
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.post(
                url,
                json=payload,
                headers=_auth_headers(config, credentials),
            )
        if response.status_code >= 400:
            raise IntegrationError(
                "delivery_failed", f"Webhook returned HTTP {response.status_code}."
            )
    except IntegrationError:
        raise
    except httpx.HTTPError as error:
        raise IntegrationError("delivery_failed", "Webhook delivery failed.") from error
    return DeliveryResult(destination=url)


async def deliver_calendar_event(
    integration: IntegrationConnection,
    *,
    cipher: SecretCipher,
    uid: UUID,
    summary: str,
    description: str,
    start: datetime,
    duration_minutes: int,
    timeout_seconds: float,
) -> DeliveryResult:
    if not 5 <= duration_minutes <= 10_080:
        raise IntegrationError("invalid_delivery", "Calendar duration is invalid.")
    config = validate_integration_config("caldav", integration.config)
    credentials = decrypt_credentials(cipher, integration.encrypted_credentials)
    base_url = str(config["calendar_url"])
    event_url = f"{base_url}/{quote(str(uid))}.ics"
    body = _icalendar(
        uid=f"{uid}@aster",
        summary=summary,
        description=description,
        start=start,
        duration_minutes=duration_minutes,
    )
    headers = _auth_headers(config, credentials)
    headers.update(
        {
            "Content-Type": "text/calendar; charset=utf-8",
            "If-None-Match": "*",
        }
    )
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.put(
                event_url,
                content=body.encode("utf-8"),
                headers=headers,
                auth=_basic_auth(config, credentials),
            )
        if response.status_code >= 400:
            raise IntegrationError(
                "delivery_failed", f"CalDAV returned HTTP {response.status_code}."
            )
    except IntegrationError:
        raise
    except httpx.HTTPError as error:
        raise IntegrationError("delivery_failed", "Calendar delivery failed.") from error
    return DeliveryResult(destination=event_url)
