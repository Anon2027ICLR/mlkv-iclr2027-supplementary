import json

from mlkv.qc_llm_audit import PROMPT_TEMPLATE, AuditRecord, write_report


def test_prompt_template_placeholders():
    filled = PROMPT_TEMPLATE.replace("{en}", "EN_TEXT").replace("{vi}", "VI_TEXT")
    assert "EN_TEXT" in filled and "VI_TEXT" in filled
    assert "{en}" not in filled and "{vi}" not in filled
    # the schema line must be valid JSON-ish guidance with grounded quotes
    assert "en_quote" in filled and "vi_quote" in filled


def test_report_lists_suspects_with_cross_references(tmp_path):
    records = [
        AuditRecord(0, "en0", "vi0", "OK"),
        AuditRecord(5, "en5", "vi5", "SUSPECT",
                    issues=[{"type": "noun", "en_quote": "wheat",
                             "vi_quote": "lúa", "detail": "rice vs wheat"}],
                    audited=True, chrf_flagged=True),
        AuditRecord(9, "en9", "vi9", "ERROR"),
    ]
    out = tmp_path / "audit.md"
    write_report(records, str(out), "test-model", 100, 50)
    text = out.read_text()
    assert "S1. mgsm-vi-5" in text
    assert "in 30-item audit; chrF-flagged" in text
    assert "«wheat» ↔ VI «lúa»" in text
    assert "mgsm-vi-0" not in text          # OK items not listed
    assert "API errors" in text and "mgsm-vi-9" in text
    assert "**SUSPECT**: 1 / 3" in text


def test_report_valid_without_errors(tmp_path):
    out = tmp_path / "audit.md"
    write_report([AuditRecord(1, "e", "v", "OK")], str(out), "m", 1, 1)
    text = out.read_text()
    assert "SUSPECT**: 0" in text
    assert "API errors" not in text


def test_issue_json_shape_roundtrip():
    # the schema we demand from the model parses as JSON
    example = json.loads('{"verdict": "SUSPECT", "issues": [{"type": "t", '
                         '"en_quote": "a", "vi_quote": "b", "detail": "d"}]}')
    assert example["verdict"] == "SUSPECT"
