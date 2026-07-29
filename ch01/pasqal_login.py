#!/usr/bin/env python3
"""One-shot interactive Pasqal Cloud login -> stored bearer token.

Run this YOURSELF in the terminal (the password prompt is getpass, nothing
is echoed or stored):

    ~/Documents/harmoniqs-hackathon/.venv/bin/python \
        ~/Documents/harmoniqs-hackathon/ch01/pasqal_login.py your@email.com

It authenticates via the pasqal-cloud SDK, verifies the connection by listing
device specs, and writes ONLY the short-lived bearer token + project id to
~/.amico/pasqal_auth.json (chmod 600). No password is ever written anywhere.

Everything downstream (scoring, submission) reads that file and authenticates
token-only, matching Amicode's own connector contract (PASQAL_TOKEN +
PASQAL_PROJECT_ID, ADR 0001).
"""

import base64
import datetime
import json
import os
import stat
import sys

from pasqal_cloud import SDK

PROJECT_ID = os.environ.get("PASQAL_PROJECT_ID", "")  # e.g. "00000000-0000-0000-0000-000000000000"
AUTH_FILE = os.path.expanduser("~/.amico/pasqal_auth.json")


def jwt_expiry(token: str) -> str:
    """Best-effort decode of the JWT exp claim (no verification needed)."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp")
        if exp:
            dt = datetime.datetime.fromtimestamp(exp, datetime.timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    except Exception:
        pass
    return "unknown"


def main() -> None:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <account-email>", file=sys.stderr)
        sys.exit(64)
    if not PROJECT_ID:
        print("error: set PASQAL_PROJECT_ID (find it in the Pasqal Cloud portal)",
              file=sys.stderr)
        sys.exit(64)
    email = sys.argv[1]

    # password=None -> the SDK prompts via getpass; it never touches this file.
    sdk = SDK(username=email, project_id=PROJECT_ID)

    specs = sdk.get_device_specs_dict()
    print(f"authenticated. project={PROJECT_ID}")
    print(f"devices visible: {sorted(specs.keys())}")

    token = sdk.user_token()
    payload = {
        "token": token,
        "project_id": PROJECT_ID,
        "minted_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
    fd = os.open(AUTH_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(payload, f)
    os.chmod(AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print(f"token stored at {AUTH_FILE} (0600), expires ~{jwt_expiry(token)}")
    print("done — downstream scripts can now run token-only.")


if __name__ == "__main__":
    main()
