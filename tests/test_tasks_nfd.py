import unicodedata

from mlkv.tasks import nfd_variant


def test_nfd_decomposes_prompt_and_question():
    items = [{
        "item_id": "mgsm-vi-0",
        "question": "Hãy giải bài toán",
        "prompt": "Hãy giải bài toán\n\nKết thúc",
        "gold": 18,
        "lang": "vi",
    }]
    out = nfd_variant(items)
    assert unicodedata.is_normalized("NFD", out[0]["prompt"])
    assert unicodedata.is_normalized("NFD", out[0]["question"])
    # content unchanged up to normalization; ids/gold untouched
    assert unicodedata.normalize("NFC", out[0]["prompt"]) == items[0]["prompt"]
    assert out[0]["item_id"] == "mgsm-vi-0" and out[0]["gold"] == 18


def test_nfd_inflates_byte_length_for_vietnamese():
    items = [{"item_id": "x", "prompt": "Hãy giải bài toán từng bước", "gold": 1, "lang": "vi"}]
    out = nfd_variant(items)
    assert len(out[0]["prompt"].encode()) > len(items[0]["prompt"].encode())


def test_originals_not_mutated():
    items = [{"item_id": "x", "prompt": "Hãy", "gold": 1, "lang": "vi"}]
    nfd_variant(items)
    assert unicodedata.is_normalized("NFC", items[0]["prompt"])
