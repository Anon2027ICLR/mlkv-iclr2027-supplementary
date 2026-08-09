"""MGSM loader (juletxara/mgsm) + Vietnamese extension.

MGSM: 250 human-translated GSM8K test items per language, parallel across
languages — which also makes the questions our fertility corpus.

Vietnamese is not in MGSM. We align `namfam/gsm8k-vietnamese` to the MGSM
item set by matching gold answers against the English split in order; items
that fail alignment are dropped (and counted, so QC is visible).
"""

from __future__ import annotations

import logging

from datasets import load_dataset

from mlkv.languages import LANGUAGES
from mlkv.metrics import parse_gold

logger = logging.getLogger(__name__)

MGSM_DATASET = "juletxara/mgsm"
VI_DATASET = "namfam/gsm8k-vietnamese"

# Translation fixes from the three-layer QC audit of MGSM-VI (records:
# docs/mgsm-vi-qc.md, docs/mgsm-vi-screen.md, docs/mgsm-vi-llm-audit.md).
# All wordings approved by a native VI speaker on 2026-08-09 and
# applied BEFORE any pilot runs, so no PROMPT_VERSION bump; adding patches
# after results exist REQUIRES bumping PROMPT_VERSION.
# Within one item, patches apply IN ORDER; occurrence counts are asserted on
# the progressively patched text. vi-40 was reviewed and ruled fine as-is.

# Items whose upstream `problem` field embeds the worked solution (leaks the
# answer): truncate at the marker, keep everything before it.
VI_TRUNCATE_AT: dict[int, str] = {
    18: "Để giải quyết",
}

# {GSM8K/MGSM index: [(old substring, approved replacement, expected count)]}
VI_PATCHES: dict[int, list[tuple[str, str, int]]] = {
    # --- layer 1: 30-item human audit ---
    163: [("bộ sưu tập hành động", "mô hình động", 3)],
    62: [("được quyền được 5%", "được hưởng 5%", 1)],
    35: [("anh ta ghi được 25% điểm số nhiều hơn", "anh ấy ghi nhiều hơn 25% điểm", 1)],
    188: [("bao lúa", "bao lúa mì", 4)],
    139: [("xanh lá cây", "xanh nước biển", 2)],
    151: [("xe đạp đơn", "xe đạp một bánh", 1)],
    # --- layer 2: chrF round-trip screen ---
    182: [("Jean năm nay là bao nhiêu tuổi?",
           "Jean hơn Mark 2 tuổi. Hai năm trước, Mark hơn một nửa tuổi của Jan "
           "5 tuổi. Nếu Jan năm nay 30 tuổi, Jean năm nay là bao nhiêu tuổi?", 1)],
    # --- layer 3, answer-affecting (wrong question semantics / numerals) ---
    53: [("Tổng doanh thu của thợ máy trong ngày có doanh thu cao hơn là bao nhiêu?",
          "Trong ngày có doanh thu cao hơn, thợ máy thu được nhiều hơn ngày "
          "còn lại bao nhiêu tiền?", 1)],
    184: [("Tỷ lệ xảy ra số lớn hơn 3 (được biểu thị dưới dạng phần trăm) so "
           "với việc tung hai số chẵn liên tiếp là bao nhiêu?",
           "Khả năng tung được số lớn hơn 3 cao hơn khả năng tung được hai số "
           "chẵn liên tiếp bao nhiêu phần trăm (điểm phần trăm)?", 1)],
    209: [("Mười hai chục cốc (240 cốc)", "Hai mươi tá cốc (240 cốc)", 1)],
    232: [("tìm thấy một nửa số con côn trùng so với số kiến",
           "tìm thấy số con bọ bằng một nửa số con kiến", 1)],
    # --- layer 3, ambiguity fixes ruled by the author ---
    133: [("đi bộ nhiều hơn 6 lần số dặm", "đi bộ nhiều gấp 6 lần số dặm", 1)],
    226: [("xác suất (làm tròn", "xác suất phần trăm (làm tròn", 1)],
    86: [("nó reo trong ba lần so với lần đầu tiên",
          "nó reo lâu gấp 3 lần so với lần đầu tiên", 1)],
    193: [("Vào lúc 12 giờ trưa Chủ nhật, có bao nhiêu con chim hồng nhựa hơn "
           "con chim hồng nhựa đã được sơn màu trắng?",
           "Vào lúc 12 giờ trưa Chủ nhật, có bao nhiêu con hồng hạc nhựa màu "
           "hồng nhiều hơn số hồng hạc nhựa màu trắng?", 1),
          ("chim hồng", "hồng hạc", 4)],
    # --- layer 3, benign concrete-noun fixes ---
    39: [("nhảy với tốc độ", "nhảy chân sáo với tốc độ", 2)],
    44: [("sáp ong và dây nhợ", "sáp ong và bấc nến", 1)],
    74: [("hoa cúc", "hoa dạ yến thảo", 3)],
    110: [("lát trái cây", "kẹo cuộn trái cây", 6), ("lát", "cuộn", 4)],
    111: [("Bờ biển", "Bờ hồ", 1)],
    132: [("đi trượt tuyết lướt 2 lần", "đi xe trượt luge 2 lần", 1)],
    150: [("đi trượt tuyết của mình", "đi ván trượt của mình", 1)],
    156: [("cho tất cả các con khỉ ăn", "cho tất cả các loài khỉ ăn", 1),
          ("các con khỉ lớn", "các con khỉ đột", 1)],
    159: [("ếch nhỏ", "nòng nọc", 2)],
    186: [("chuột nhắt", "chuột hamster", 1),
          ("mỗi con chuột được cho 5", "mỗi con chuột hamster được cho 5", 1)],
    203: [("ăn bánh mì trứng phô mai", "ăn trứng ốp la phô mai", 1)],
    222: [("hoa đỗ quyên", "hoa phong lữ", 2)],
    239: [("trong một phòng học", "trong một hội trường", 1),
          ("Phòng học có 3 lối vào", "Hội trường có 3 lối vào", 1)],
}


def _apply_patch_list(index: int, question: str,
                      patches: list[tuple[str, str, int]]) -> str:
    for old, new, count in patches:
        found = question.count(old)
        if found != count:
            raise RuntimeError(
                f"VI patch mismatch at index {index}: expected {count}×{old!r}, "
                f"found {found} — dataset revision changed since the QC audit?"
            )
        question = question.replace(old, new)
    return question


def _apply_vi_patches(index: int, question: str) -> str:
    """Apply author-approved translation fixes; fail loudly if the dataset
    revision no longer matches the audited text."""
    marker = VI_TRUNCATE_AT.get(index)
    if marker is not None:
        if question.count(marker) != 1:
            raise RuntimeError(
                f"VI truncation marker mismatch at index {index}: {marker!r}"
            )
        question = question[:question.index(marker)].rstrip()
    return _apply_patch_list(index, question, VI_PATCHES.get(index, []))


def _mgsm_split(lang: str):
    return load_dataset(MGSM_DATASET, lang, split="test")


def load(lang: str, max_items: int | None = None) -> list[dict]:
    language = LANGUAGES[lang]
    instruction = language.instruction

    if language.in_mgsm:
        ds = _mgsm_split(lang)
        items = [
            {
                "item_id": f"mgsm-{lang}-{i}",
                "question": row["question"],
                "prompt": f"{row['question']}\n\n{instruction}",
                "gold": row["answer_number"],
                "lang": lang,
            }
            for i, row in enumerate(ds)
        ]
    elif lang == "vi":
        items = _load_vietnamese(instruction)
    else:
        raise ValueError(f"no MGSM source for language: {lang}")

    return items[:max_items] if max_items else items


def _load_vietnamese(instruction: str) -> list[dict]:
    """Align the community VI translation of GSM8K test to MGSM's 250 items."""
    en = _mgsm_split("en")
    vi = load_dataset(VI_DATASET, split="test")

    vi_rows = list(vi)
    vi_fields = vi_rows[0].keys()
    q_field = next((f for f in ("question_vi", "question", "vi_question", "problem") if f in vi_fields), None)
    a_field = next((f for f in ("answer", "answer_number", "final_answer") if f in vi_fields), None)
    idx_field = "index" if "index" in vi_fields else None
    if q_field is None or a_field is None:
        raise RuntimeError(f"unexpected schema in {VI_DATASET}: {sorted(vi_fields)}")

    def gold_of(row) -> float | None:
        raw = row[a_field]
        if isinstance(raw, str) and "####" in raw:  # GSM8K rationale format
            raw = raw.split("####")[-1]
        try:
            return parse_gold(raw)
        except (ValueError, TypeError):
            return None

    # Prefer the dataset's own GSM8K index for alignment; fall back to position.
    # MGSM took the first 250 GSM8K test items, so MGSM item i ↔ GSM8K index i.
    by_index = {row[idx_field]: row for row in vi_rows} if idx_field else None

    items, dropped = [], 0
    for i, en_row in enumerate(en):
        vi_row = by_index.get(i) if by_index is not None else (
            vi_rows[i] if i < len(vi_rows) else None
        )
        if vi_row is None:
            dropped += 1
            continue
        vi_gold = gold_of(vi_row)
        en_gold = parse_gold(en_row["answer_number"])
        if vi_gold is None or abs(vi_gold - en_gold) > 1e-6:
            dropped += 1
            continue
        question = _apply_vi_patches(i, vi_row[q_field])
        items.append(
            {
                "item_id": f"mgsm-vi-{i}",
                "question": question,
                "prompt": f"{question}\n\n{instruction}",
                "gold": en_row["answer_number"],
                "lang": "vi",
            }
        )
    if dropped:
        logger.warning("VI alignment: %d/%d items dropped (answer mismatch)", dropped, len(en))
    if len(items) < 200:
        logger.warning(
            "VI alignment yielded only %d items — positional alignment may be "
            "wrong for this dataset revision; inspect before trusting.", len(items)
        )
    return items


def questions_for_fertility(lang: str) -> list[str]:
    """Parallel question texts (no instruction) as the fertility corpus."""
    return [item["question"] for item in load(lang)]
