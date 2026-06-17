from vibevoice_studio.script_parser import parse_script, validate_script


def test_parse_single_speaker():
    parsed = parse_script("Speaker 1: Hello world.")
    assert parsed.num_speakers() == 1
    assert parsed.speaker_indices == [1]
    assert parsed.lines[0].text == "Hello world."


def test_parse_multi_speaker():
    raw = "Speaker 1: Hi.\nSpeaker 2: Hello.\nSpeaker 1: Bye."
    parsed = parse_script(raw)
    assert parsed.speaker_indices == [1, 2]
    assert len(parsed.lines) == 3


def test_continuation_lines_merge():
    raw = "Speaker 1: This is\na single turn\nSpeaker 2: Done."
    parsed = parse_script(raw)
    assert parsed.lines[0].text == "This is a single turn"
    assert parsed.lines[1].text == "Done."


def test_leading_prose_attributed_to_speaker_one():
    parsed = parse_script("Just some narration.\nSpeaker 2: A reply.")
    assert parsed.lines[0].speaker_index == 1
    assert parsed.speaker_indices == [1, 2]


def test_blank_lines_ignored():
    parsed = parse_script("\n\nSpeaker 1: Hi.\n\n\nSpeaker 2: Yo.\n")
    assert len(parsed.lines) == 2


def test_to_engine_text_roundtrip():
    raw = "Speaker 1: A\nSpeaker 2: B"
    assert parse_script(raw).to_engine_text() == "Speaker 1: A\nSpeaker 2: B"


def test_validate_empty():
    assert validate_script(parse_script("   ")) != []


def test_validate_too_many_speakers():
    raw = "\n".join(f"Speaker {i}: line" for i in range(1, 6))
    errors = validate_script(parse_script(raw))
    assert any("up to 4 speakers" in e for e in errors)


def test_validate_non_contiguous():
    raw = "Speaker 1: a\nSpeaker 3: b"
    errors = validate_script(parse_script(raw))
    assert any("contiguous" in e for e in errors)


def test_validate_ok():
    raw = "Speaker 1: a\nSpeaker 2: b"
    assert validate_script(parse_script(raw)) == []
