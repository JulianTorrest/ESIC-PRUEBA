import hashlib
import os

import streamlit as st


def _get_config(field: str, default: str) -> str:
    try:
        return st.secrets["auth"][field]
    except (KeyError, FileNotFoundError, TypeError):
        env_map = {
            "APP_USERNAME": "ESIC_APP_USERNAME",
            "APP_PASSWORD": "ESIC_APP_PASSWORD",
        }
        return os.environ.get(env_map.get(field, ""), default)


def get_default_credentials() -> dict:
    return {
        "username": _get_config("APP_USERNAME", "esic"),
        "password": _get_config("APP_PASSWORD", "esic2026"),
    }


def check_credentials(username: str, password: str) -> bool:
    """Valida usuario y contraseña."""
    creds = get_default_credentials()
    u_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    p_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    expected_u = hashlib.sha256(creds["username"].encode("utf-8")).hexdigest()
    expected_p = hashlib.sha256(creds["password"].encode("utf-8")).hexdigest()
    return u_hash == expected_u and p_hash == expected_p
