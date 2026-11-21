import json

from app.config import Settings, runtime_settings_path
from app.services.runtime_settings import (
    public_settings,
    reset_runtime_settings,
    save_runtime_settings,
)


def test_runtime_settings_reload_and_mask_secrets(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, llm_api_key="environment-key")
    settings.ensure_directories()
    updated = save_runtime_settings(
        settings,
        {"llm_model": "runtime-model", "llm_api_key": "runtime-secret"},
    )
    payload = public_settings(updated)
    assert payload["llm_model"] == "runtime-model"
    assert payload["llm_api_key_configured"] is True
    assert payload["runtime_override_active"] is True
    assert "runtime-secret" not in json.dumps(payload)
    assert "llm_api_key" not in payload

    reloaded = Settings(data_dir=tmp_path)
    assert reloaded.llm_model == "runtime-model"
    assert reloaded.llm_api_key.get_secret_value() == "runtime-secret"

    cleared = save_runtime_settings(reloaded, {"clear_llm_api_key": True})
    assert cleared.llm_api_key.get_secret_value() == ""
    assert public_settings(cleared)["llm_api_key_configured"] is False

    reset = reset_runtime_settings(cleared)
    assert not runtime_settings_path(tmp_path).exists()
    assert public_settings(reset)["runtime_override_active"] is False


def test_runtime_settings_preserve_new_values_on_save(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path, dense_top_k=20, sparse_top_k=20)
    settings.ensure_directories()
    updated = save_runtime_settings(settings, {"dense_top_k": 35})
    assert updated.dense_top_k == 35
    assert updated.sparse_top_k == 20
    assert updated.llm_model == settings.llm_model
