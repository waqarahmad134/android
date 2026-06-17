"""Device detection tests that monkeypatch torch availability."""

import types

import vibevoice_studio.device as device
from vibevoice_studio.config import GenerationConfig


def _fake_torch(cuda=False, mps=False):
    torch = types.SimpleNamespace()
    torch.cuda = types.SimpleNamespace(is_available=lambda: cuda)
    torch.backends = types.SimpleNamespace(
        mps=types.SimpleNamespace(is_available=lambda: mps)
    )
    torch.bfloat16 = "bfloat16"
    torch.float16 = "float16"
    torch.float32 = "float32"
    return torch


def test_detect_cuda_preferred(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch(cuda=True))
    assert device.detect_device() == "cuda"


def test_detect_mps_when_no_cuda(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch(cuda=False, mps=True))
    assert device.detect_device() == "mps"


def test_detect_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch())
    assert device.detect_device() == "cpu"


def test_preferred_ignored_when_unavailable(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch())
    # cuda requested but unavailable -> cpu
    assert device.detect_device("cuda") == "cpu"


def test_select_dtype_cuda_is_bf16(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch(cuda=True))
    assert device.select_dtype("cuda") == "bfloat16"


def test_select_dtype_cpu_is_fp32(monkeypatch):
    monkeypatch.setattr(device, "_torch", lambda: _fake_torch())
    assert device.select_dtype("cpu") == "float32"


def test_attn_cpu_is_sdpa():
    assert device.select_attn_implementation("cpu") == "sdpa"


def test_attn_cuda_without_flash_is_sdpa(monkeypatch):
    monkeypatch.setattr(device.importlib.util, "find_spec", lambda name: None)
    assert device.select_attn_implementation("cuda") == "sdpa"


def test_describe_runtime_mock():
    rt = device.describe_runtime(GenerationConfig(), mock=True)
    assert rt.mock is True
    assert rt.device == "cpu"
