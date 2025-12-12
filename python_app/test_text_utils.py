from python_app.text_utils import split_text


def test_split_by_punctuation_respects_limit():
    text = "你好，世界。这是一个测试，用于验证切分。"
    parts = split_text(text, 6)
    assert all(len(part) <= 6 for part in parts)
    assert "".join(parts).replace(" ", "") == text.replace(" ", "")


def test_split_long_sentence_is_chunked():
    long_text = "a" * 15
    parts = split_text(long_text, 4)
    assert parts == ["aaaa", "aaaa", "aaaa", "aaa"]
