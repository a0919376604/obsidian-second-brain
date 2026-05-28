import hashlib
from pathlib import Path

from scripts.architect.prompt_extract import ExtractedPrompt, extract_prompts


def test_extracts_toml_config_prompts(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "prompts.toml").write_text(
        '[summarize]\n'
        'template = """Summarize this:\n{conversation}\n\nReturn 3 bullets."""\n'
        '\n'
        '[classify]\n'
        'template = "Classify: {text}"\n'
    )
    prompts = extract_prompts(tmp_path)
    names = {p.name for p in prompts}
    assert "summarize" in names
    assert "classify" in names
    summ = next(p for p in prompts if p.name == "summarize")
    assert "Summarize this" in summ.body
    assert "{conversation}" in summ.body
    assert summ.is_dynamic is False
    assert summ.source.startswith("config/prompts.toml")
    assert summ.source_hash.startswith("sha256:")
    # Reproducible hash
    expected = "sha256:" + hashlib.sha256(summ.body.encode("utf-8")).hexdigest()
    assert summ.source_hash == expected
    assert summ.extraction_method == "toml-config"


def test_extracts_python_module_constant(tmp_path: Path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "intent.py").write_text(
        '"""Intent classifier prompts."""\n'
        '\n'
        'INTENT_PROMPT = """You are an intent classifier.\n'
        'Given: {user_message}\n'
        'Return: PRODUCT | COMPLAINT | OTHER.\n'
        '"""\n'
        '\n'
        '# Helper not exported\n'
        'def build(): pass\n'
    )
    prompts = extract_prompts(tmp_path)
    names = {p.name for p in prompts}
    assert "INTENT_PROMPT" in names
    intent = next(p for p in prompts if p.name == "INTENT_PROMPT")
    assert "intent classifier" in intent.body.lower()
    assert "{user_message}" in intent.body
    assert intent.is_dynamic is False
    assert intent.extraction_method == "module-constant"
    assert "prompts/intent.py" in intent.source


def test_extracts_system_prompt_pattern(tmp_path: Path):
    (tmp_path / "agent.py").write_text(
        '\n'
        'SYSTEM_PROMPT = """You are a helpful assistant focused on customer service."""\n'
        'USER_PROMPT_TEMPLATE = "Question: {q}"\n'
    )
    prompts = extract_prompts(tmp_path)
    names = {p.name for p in prompts}
    assert "SYSTEM_PROMPT" in names
    assert "USER_PROMPT_TEMPLATE" in names


def test_extracts_langchain_chat_prompt_template(tmp_path: Path):
    (tmp_path / "chain.py").write_text(
        'from langchain_core.prompts import ChatPromptTemplate\n'
        'from langchain_core.messages import SystemMessage, HumanMessage\n'
        '\n'
        'CHAT_PROMPT = ChatPromptTemplate.from_messages([\n'
        '    SystemMessage(content="You are an expert at categorization."),\n'
        '    HumanMessage(content="Categorize: {input}"),\n'
        '])\n'
    )
    prompts = extract_prompts(tmp_path)
    names = {p.name for p in prompts}
    assert "CHAT_PROMPT" in names
    cp = next(p for p in prompts if p.name == "CHAT_PROMPT")
    assert "expert at categorization" in cp.body
    assert "Categorize" in cp.body
    assert cp.is_dynamic is False
    assert cp.extraction_method == "langchain-chat-prompt-template"


def test_skips_non_prompt_string_constants(tmp_path: Path):
    """Random string constants (not prompt-like) should NOT be extracted."""
    (tmp_path / "config.py").write_text(
        'DATABASE_URL = "postgresql://localhost/db"\n'
        'API_VERSION = "v1"\n'
        'SIMPLE_NAME = "Hello"\n'
    )
    prompts = extract_prompts(tmp_path)
    # No PROMPT-suffix or PROMPT-prefix names → nothing extracted from Python constants.
    # But config.py has no .toml so 0 prompts.
    assert prompts == []


def test_source_hash_changes_when_body_changes(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "prompts.toml").write_text('[p]\ntemplate = "v1"\n')
    h1 = extract_prompts(tmp_path)[0].source_hash
    (tmp_path / "config" / "prompts.toml").write_text('[p]\ntemplate = "v2"\n')
    h2 = extract_prompts(tmp_path)[0].source_hash
    assert h1 != h2
