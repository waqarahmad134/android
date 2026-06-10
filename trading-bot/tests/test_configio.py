import os

import pytest

from src import configio


CONFIG_YAML = """\
mode: paper
exchange: binance
quote_currency: USDT
universe:
  - BTC/USDT
  - ETH/USDT
risk:
  max_position_pct: 0.15
  stop_loss_pct: 0.02
  daily_loss_limit_pct: 0.03
notifications:
  enabled: false
"""


@pytest.fixture
def cfg_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(CONFIG_YAML)
    return str(p)


def test_update_config_nested_and_typed(cfg_file):
    configio.update_config(cfg_file, {
        "risk.max_position_pct": "0.25",   # string -> float
        "mode": "paper",
        "notifications.enabled": "true",   # string -> bool
    })
    data = configio.read_config(cfg_file)
    assert data["risk"]["max_position_pct"] == 0.25
    assert data["notifications"]["enabled"] is True


def test_update_config_list_from_csv(cfg_file):
    configio.update_config(cfg_file, {"universe": "BTC/USDT, SOL/USDT, PAXG/USDT"})
    data = configio.read_config(cfg_file)
    assert data["universe"] == ["BTC/USDT", "SOL/USDT", "PAXG/USDT"]


def test_update_config_rejects_invalid(cfg_file):
    # max_position_pct must be in (0, 1]; 5 should fail validation and not persist.
    with pytest.raises(ValueError):
        configio.update_config(cfg_file, {"risk.max_position_pct": "5"})
    data = configio.read_config(cfg_file)
    assert data["risk"]["max_position_pct"] == 0.15  # unchanged


def test_env_roundtrip_and_masking(tmp_path):
    env = tmp_path / ".env"
    env.write_text("BINANCE_API_KEY=abcd1234efgh\n# comment\nOTHER=keepme\n")
    status = configio.env_status(str(env))
    assert status["BINANCE_API_KEY"]["set"] is True
    assert status["BINANCE_API_KEY"]["preview"].endswith("efgh")
    assert "abcd" not in status["BINANCE_API_KEY"]["preview"]

    configio.update_env(str(env), {"BYBIT_API_KEY": "newsecret"})
    text = env.read_text()
    assert "BYBIT_API_KEY=newsecret" in text
    assert "OTHER=keepme" in text          # unmanaged line preserved
    assert oct(os.stat(env).st_mode)[-3:] == "600"
