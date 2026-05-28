from app.agents.fastgpt import _extract_content, _extract_stream_content


def test_extract_content_supports_fastgpt_non_openai_fields():
    assert _extract_content({"answer": "top answer"}) == "top answer"
    assert _extract_content({"responseData": {"content": "nested content"}}) == "nested content"
    assert _extract_content({"choices": [{"message": {"answer": "choice answer"}}]}) == "choice answer"


def test_extract_stream_content_supports_openai_delta():
    chunk, snapshot = _extract_stream_content({"choices": [{"delta": {"content": "hello"}}]})

    assert chunk == "hello"
    assert snapshot == ""


def test_extract_stream_content_supports_fastgpt_answer_snapshots():
    chunk, snapshot = _extract_stream_content({"answer": "hello"})
    next_chunk, next_snapshot = _extract_stream_content({"answer": "hello world"}, snapshot)
    duplicate_chunk, duplicate_snapshot = _extract_stream_content({"answer": "hello world"}, next_snapshot)

    assert chunk == "hello"
    assert snapshot == "hello"
    assert next_chunk == " world"
    assert next_snapshot == "hello world"
    assert duplicate_chunk == ""
    assert duplicate_snapshot == "hello world"


def test_extract_stream_content_supports_top_level_content_and_text():
    content_chunk, content_snapshot = _extract_stream_content({"content": "content chunk"})
    text_chunk, text_snapshot = _extract_stream_content({"text": "text chunk"}, content_snapshot)

    assert content_chunk == "content chunk"
    assert content_snapshot == "content chunk"
    assert text_chunk == "text chunk"
    assert text_snapshot == "text chunk"


def test_extract_stream_content_supports_delta_dict_and_string():
    dict_chunk, dict_snapshot = _extract_stream_content({"delta": {"text": "delta text"}})
    string_chunk, string_snapshot = _extract_stream_content({"delta": "delta string"}, dict_snapshot)

    assert dict_chunk == "delta text"
    assert dict_snapshot == "delta text"
    assert string_chunk == "delta string"
    assert string_snapshot == "delta string"
