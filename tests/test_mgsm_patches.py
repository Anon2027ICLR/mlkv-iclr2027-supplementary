import pytest

from mlkv.tasks.mgsm import (
    VI_PATCHES,
    VI_TRUNCATE_AT,
    _apply_patch_list,
    _apply_vi_patches,
)


def test_patch_applied_with_expected_count():
    # index 139: "xanh lá cây" ×2 -> "xanh nước biển"
    text = "có kẹo xanh lá cây. Nếu có 12 viên kẹo xanh lá cây thì sao?"
    out = _apply_vi_patches(139, text)
    assert out.count("xanh nước biển") == 2
    assert "xanh lá cây" not in out


def test_unpatched_index_passthrough():
    assert _apply_vi_patches(0, "không có patch nào") == "không có patch nào"


def test_missing_substring_raises():
    # dataset revision drift must fail loudly, not silently skip
    with pytest.raises(RuntimeError, match="patch mismatch"):
        _apply_vi_patches(151, "câu hỏi không chứa cụm từ cần sửa")


def test_wrong_count_raises():
    # index 163 expects exactly 3 occurrences
    with pytest.raises(RuntimeError, match="expected 3"):
        _apply_vi_patches(163, "chỉ một bộ sưu tập hành động")


def test_patch_table_sane():
    for patches in VI_PATCHES.values():
        for old, new, count in patches:
            assert old != new and count >= 1
    for marker in VI_TRUNCATE_AT.values():
        assert marker


def test_truncation_cuts_solution_tail():
    text = "Câu hỏi ở đây? \n\nĐể giải quyết vấn đề này, đáp án là 7."
    assert _apply_vi_patches(18, text) == "Câu hỏi ở đây?"


def test_truncation_missing_marker_raises():
    with pytest.raises(RuntimeError, match="truncation marker"):
        _apply_vi_patches(18, "Câu hỏi không có phần lời giải nào.")


def test_patch_list_applies_in_order():
    # first patch consumes its occurrences, second counts the remainder
    patches = [("a b", "x b", 1), ("b", "c", 2)]
    assert _apply_patch_list(0, "a b b", patches) == "x c c"


def test_patch_list_count_checked_after_earlier_patches():
    # "b" appears 3 times initially, but only 2 remain after the first patch
    patches = [("a b", "x y", 1), ("b", "c", 3)]
    with pytest.raises(RuntimeError, match="expected 3"):
        _apply_patch_list(0, "a b b b", patches)


def test_patch_151_is_the_broken_item_fix():
    out = _apply_vi_patches(151, "một người đến trên xe đạp đơn.")
    assert out == "một người đến trên xe đạp một bánh."
