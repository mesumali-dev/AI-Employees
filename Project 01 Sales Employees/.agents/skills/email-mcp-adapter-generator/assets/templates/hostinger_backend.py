#!/usr/bin/env python3
"""
hostinger_backend.py — Hostinger implementation of EmailBackend.

GENERATED / REFRESHED by the email-mcp-adapter-generator skill. You can
hand-edit it, but re-running the generator will not clobber an existing
file (delete it first to force a rebuild). Account facts (mailbox
resourceId, from-address) live in hostinger_config.json beside this file.

Why REST and not the MCP protocol at runtime:
The Hostinger MCP server is a thin passthrough over the REST API at
api.mail.hostinger.com — its tools just forward raw {method, path, body}.
Speaking the MCP JSON-RPC protocol from a script would mean spawning the
mcp-remote Node bridge and parsing streaming responses, all to make the
exact same HTTP call. So this backend calls REST directly, using the
HOSTINGER_API_TOKEN from the project-root .env (via env_utils).

Endpoint facts:
  - REST base:      https://api.mail.hostinger.com
  - Discover mbox:  GET  /api/v1/me   -> data.mailboxes[].{resourceId,address}
  - Send:           POST /api/v1/mailboxes/{resourceId}/send
                    body: {to:[...], subject, text, displayName?}
                    204 == sent and copied to Sent folder.
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Make sibling modules importable whether run as a module or by path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backends.base import EmailBackend, SendResult  # noqa: E402
import env_utils  # noqa: E402

REST_BASE = "https://api.mail.hostinger.com"
DISCOVER_PATH = "/api/v1/me"
SEND_PATH = "/api/v1/mailboxes/{mailbox}/send"


class HostingerBackend(EmailBackend):
    provider = "hostinger"

    def __init__(self, token=None, mailbox_resource_id=None,
                 from_address=None, timeout=30):
        # Token: explicit arg wins, else read HOSTINGER_API_TOKEN from the
        # project-root .env so the secret lives in exactly one place.
        if token is None:
            token = env_utils.require_token("hostinger")
        self.token = token
        self.timeout = timeout
        self.mailbox_resource_id = mailbox_resource_id
        self.from_address = from_address
        # Prefer the config baked by the generator — no network needed to
        # learn the mailbox. Fall back to a live /me discovery only if the
        # config is absent and no resourceId was passed.
        if self.mailbox_resource_id is None:
            self._load_cached_config()
        if self.mailbox_resource_id is None:
            self._discover_mailbox()

    def _load_cached_config(self):
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "hostinger_config.json")
        if not os.path.isfile(cfg_path):
            return
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        # Honour a preferred from_address if it matches a known mailbox.
        if self.from_address:
            for m in cfg.get("mailboxes", []):
                if m.get("address") == self.from_address:
                    self.mailbox_resource_id = m.get("resourceId")
                    return
        self.mailbox_resource_id = cfg.get("default_mailbox_resource_id")
        if self.from_address is None:
            self.from_address = cfg.get("default_from_address")

    # ---- HTTP helper -------------------------------------------------

    def _request(self, method, path, body=None):
        url = REST_BASE + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Accept", "application/json")
        # Hostinger's API sits behind Cloudflare, which rejects the
        # default Python urllib User-Agent with a 403 (error 1010). Any
        # ordinary UA string clears it.
        req.add_header("User-Agent", "hostinger-email-drafter/1.0")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8") or ""
            return resp.status, raw

    # ---- discovery ---------------------------------------------------

    def _discover_mailbox(self):
        status, raw = self._request("GET", DISCOVER_PATH)
        payload = json.loads(raw) if raw else {}
        mailboxes = (payload.get("data") or {}).get("mailboxes") or []
        if not mailboxes:
            raise RuntimeError("Hostinger /me returned no mailboxes.")
        # Prefer a mailbox matching a preset from_address; else first one.
        chosen = None
        if self.from_address:
            chosen = next(
                (m for m in mailboxes
                 if m.get("address") == self.from_address),
                None,
            )
        chosen = chosen or mailboxes[0]
        self.mailbox_resource_id = chosen.get("resourceId")
        self.from_address = chosen.get("address")

    # ---- the one method the interface requires -----------------------

    def send(self, to, subject, body, display_name=None):
        payload = {"to": [to], "subject": subject, "text": body}
        if display_name:
            payload["displayName"] = display_name
        path = SEND_PATH.format(mailbox=self.mailbox_resource_id)
        try:
            status, raw = self._request("POST", path, payload)
        except urllib.error.HTTPError as e:
            detail = _short_http_error(e)
            return SendResult.failure(f"HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            return SendResult.failure(f"network error: {e.reason}")
        except Exception as e:  # noqa: BLE001 - keep one bad send from aborting batch
            return SendResult.failure(f"unexpected: {e}")

        if status in (200, 201, 202, 204):
            return SendResult.success()
        return SendResult.failure(f"unexpected status {status}: {raw[:200]}")


def _short_http_error(e):
    """Turn a Hostinger error envelope into a one-line reason."""
    try:
        body = json.loads(e.read().decode("utf-8"))
        # envelope: {"code": "...", "error": "...", "params": {...}}
        return body.get("code") or body.get("error") or str(e)
    except Exception:  # noqa: BLE001
        return e.reason if hasattr(e, "reason") else str(e)


# Factory the send_batch runner looks for. Every backend module exposes a
# build() returning a ready EmailBackend, so the runner stays uniform
# across providers.
def build(**kwargs):
    return HostingerBackend(**kwargs)
