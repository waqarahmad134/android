"""Contract test for VibeVoiceEngine.synthesize().

We cannot download the multi-GB weights in CI, so this test injects fake
processor/model objects and asserts that synthesize() calls model.generate()
with the exact arguments the upstream VibeVoice demo uses, and that it extracts
``outputs.speech_outputs[0]`` correctly. This guards the real integration path
without needing the model.
"""

import pytest

from vibevoice_studio.config import GenerationConfig
from vibevoice_studio.engine import VibeVoiceEngine

torch = pytest.importorskip("torch")


class _FakeProcessor:
    def __init__(self):
        self.tokenizer = object()
        self.last_call = None

    def __call__(self, **kwargs):
        self.last_call = kwargs
        # Mimic a BatchEncoding: a dict-like with tensor values.
        return {"input_ids": torch.zeros((1, 4), dtype=torch.long)}


class _FakeOutputs:
    def __init__(self, wave):
        self.speech_outputs = [wave]


class _FakeModel:
    def __init__(self):
        self.last_generate = None
        self.wave = torch.tensor([0.1, -0.2, 0.3], dtype=torch.float32)

    def generate(self, **kwargs):
        self.last_generate = kwargs
        return _FakeOutputs(self.wave)


def _engine_with_fakes(device="cpu"):
    eng = VibeVoiceEngine(GenerationConfig(cfg_scale=1.7))
    eng.processor = _FakeProcessor()
    eng.model = _FakeModel()
    eng.device = device
    return eng


def test_synthesize_passes_upstream_generate_args():
    eng = _engine_with_fakes()
    audio, sr = eng.synthesize("Speaker 1: hi\nSpeaker 2: yo", ["a.wav", "b.wav"], eng.cfg)

    # Processor called with text/voice_samples wrapped in a batch list.
    pcall = eng.processor.last_call
    assert pcall["text"] == ["Speaker 1: hi\nSpeaker 2: yo"]
    assert pcall["voice_samples"] == [["a.wav", "b.wav"]]
    assert pcall["return_tensors"] == "pt"

    # generate() called with the exact upstream contract.
    gcall = eng.model.last_generate
    assert gcall["cfg_scale"] == 1.7
    assert gcall["tokenizer"] is eng.processor.tokenizer
    assert gcall["generation_config"] == {"do_sample": False}

    # Audio is the flattened first speech output.
    assert sr == 24000
    assert list(map(lambda x: round(float(x), 1), audio)) == [0.1, -0.2, 0.3]
