#!/usr/bin/env python3
"""Token-only Pasqal Cloud client, fed by pasqal_login.py.

Reads ~/.amico/pasqal_auth.json (written by the interactive login) and builds
an SDK instance through a TokenProvider — no username/password in this path,
mirroring Amicode's connector contract. Fails loudly with a re-login hint if
the token is missing or rejected.
"""

import json
import os
import sys

from pasqal_cloud import SDK
from pasqal_cloud.authentication import TokenProvider

AUTH_FILE = os.path.expanduser("~/.amico/pasqal_auth.json")
RELOGIN_HINT = (
    "run: ~/Documents/harmoniqs-hackathon/.venv/bin/python "
    "~/Documents/harmoniqs-hackathon/ch01/pasqal_login.py <email>"
)


class StoredTokenProvider(TokenProvider):
    """Serves the bearer token minted at interactive login."""

    def __init__(self, token: str):  # noqa: D107 — trivial
        self._token = token

    def get_token(self) -> str:
        return self._token


def connect() -> SDK:
    """Auth-file -> SDK. Raises SystemExit with a hint when auth is absent."""
    try:
        with open(AUTH_FILE) as f:
            auth = json.load(f)
    except FileNotFoundError:
        sys.exit(f"error: no Pasqal auth at {AUTH_FILE}; {RELOGIN_HINT}")
    return SDK(
        token_provider=StoredTokenProvider(auth["token"]),
        project_id=auth["project_id"],
    )


if __name__ == "__main__":
    sdk = connect()
    specs = sdk.get_device_specs_dict()
    print(f"token OK. project={sdk.project_id}")
    print(f"devices: {sorted(specs.keys())}")
