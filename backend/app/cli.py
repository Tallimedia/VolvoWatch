"""Small operational helpers: `python -m app.cli <command>`."""

from __future__ import annotations

import secrets
import sys

from cryptography.fernet import Fernet


def gen_keys() -> None:
    print("# Paste these into backend/.env")
    print(f"FERNET_KEY={Fernet.generate_key().decode()}")
    print(f"DEVICE_TOKEN_PEPPER={secrets.token_urlsafe(32)}")


def show_config() -> None:
    from .config import get_settings

    s = get_settings()
    print(f"public_base_url   {s.public_base_url}")
    print(f"redirect_uri      {s.volvo_redirect_uri}")
    print(f"database_url      {s.database_url}")
    print(f"scopes            {len(s.scope_list)} -> {' '.join(s.scope_list)}")
    print(f"client_id set     {bool(s.volvo_client_id)}")
    print(f"client_secret set {bool(s.volvo_client_secret)}")
    print(f"vcc_api_key set    {bool(s.volvo_vcc_api_key)}")
    print(f"fernet_key set     {bool(s.fernet_key)}")
    print(f"pepper set         {bool(s.device_token_pepper)}")


COMMANDS = {"gen-keys": gen_keys, "show-config": show_config}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: python -m app.cli [{' | '.join(COMMANDS)}]")
        raise SystemExit(1)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
