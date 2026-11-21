import json
import os

from app.config import (
    RUNTIME_PUBLIC_FIELDS,
    Settings,
    get_settings,
    read_runtime_settings,
    runtime_settings_path,
)


def public_settings(settings: Settings) -> dict:
    payload = {key: getattr(settings, key) for key in sorted(RUNTIME_PUBLIC_FIELDS)}
    payload.update(
        {
            "llm_api_key_configured": bool(settings.llm_api_key.get_secret_value()),
            "dashscope_api_key_configured": bool(settings.dashscope_api_key.get_secret_value()),
            "dashscope_workspace_configured": bool(settings.dashscope_workspace_id),
            "runtime_override_active": runtime_settings_path(settings.data_dir).exists(),
        }
    )
    return payload


def save_runtime_settings(settings: Settings, changes: dict) -> Settings:
    path = runtime_settings_path(settings.data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    runtime = read_runtime_settings(settings.data_dir)
    public = {key: getattr(settings, key) for key in RUNTIME_PUBLIC_FIELDS}
    for key in RUNTIME_PUBLIC_FIELDS:
        if key in changes:
            public[key] = changes[key]
    secrets = runtime.get("secrets", {})
    for key, clear_key in (
        ("llm_api_key", "clear_llm_api_key"),
        ("dashscope_api_key", "clear_dashscope_api_key"),
        ("dashscope_workspace_id", "clear_dashscope_workspace_id"),
    ):
        value = changes.get(key)
        if changes.get(clear_key):
            secrets[key] = ""
        elif isinstance(value, str) and value.strip():
            secrets[key] = value.strip()

    payload = {"version": 1, "values": public, "secrets": secrets}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    get_settings.cache_clear()
    updated = Settings(
        data_dir=settings.data_dir,
        database_url=settings.database_url,
        qdrant_url=settings.qdrant_url,
    )
    updated.ensure_directories()
    return updated


def reset_runtime_settings(settings: Settings) -> Settings:
    path = runtime_settings_path(settings.data_dir)
    if path.exists():
        path.unlink()
    get_settings.cache_clear()
    defaults = Settings(
        data_dir=settings.data_dir,
        database_url=settings.database_url,
        qdrant_url=settings.qdrant_url,
    )
    defaults.ensure_directories()
    return defaults
