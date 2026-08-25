import pytest

from mlkv.compression import CompressionConfig, budget_ratio, parse


class TestParse:
    def test_baseline(self):
        cfg = parse("baseline")
        assert cfg.kind == "baseline" and cfg.name == "baseline"

    def test_kvquant(self):
        cfg = parse("kv4")
        assert cfg.kind == "kvquant" and cfg.params["nbits"] == 4
        assert cfg.generate_kwargs()["cache_config"]["nbits"] == 4

    def test_press_ratio(self):
        cfg = parse("snapkv@r0.75")
        assert cfg.kind == "press"
        assert cfg.params == {"press": "snapkv", "ratio": 0.75}

    def test_press_budget(self):
        cfg = parse("snapkv@b2048")
        assert cfg.kind == "press"
        assert cfg.params == {"press": "snapkv", "budget": 2048}
        assert cfg.name == "snapkv@b2048"  # verbatim — keys the store

    def test_unknown_config_raises(self):
        for bad in ["snapkv", "snapkv@b0", "snapkv@r1.5", "nosuch@r0.5", "kv3"]:
            with pytest.raises(ValueError):
                parse(bad)


class TestBudgetRatio:
    def test_prompt_within_budget(self):
        assert budget_ratio(2048, 1000) == 0.0
        assert budget_ratio(2048, 2048) == 0.0

    def test_prompt_exceeds_budget(self):
        assert budget_ratio(2048, 4096) == pytest.approx(0.5)
        assert budget_ratio(1024, 8192) == pytest.approx(0.875)

    def test_ratio_grows_with_prefill(self):
        rs = [budget_ratio(1024, n) for n in (1024, 2048, 4096, 16384)]
        assert rs == sorted(rs) and rs[-1] < 1.0


class TestEffectiveRatio:
    def test_baseline_and_kvquant_none(self):
        assert parse("baseline").effective_ratio(4096) is None
        assert parse("kv4").effective_ratio(4096) is None

    def test_ratio_config_constant(self):
        cfg = parse("snapkv@r0.75")
        assert cfg.effective_ratio(100) == cfg.effective_ratio(100000) == 0.75

    def test_budget_config_varies_per_item(self):
        cfg = parse("snapkv@b2048")
        assert cfg.effective_ratio(1000) == 0.0
        assert cfg.effective_ratio(4096) == pytest.approx(0.5)


class TestPress:
    def test_non_press_kinds_return_none(self):
        assert parse("baseline").press() is None
        assert parse("kv4").press(prefill_len=100) is None

    def test_press_requires_prefill_len(self):
        with pytest.raises(ValueError):
            parse("snapkv@b2048").press()
        with pytest.raises(ValueError):
            parse("snapkv@r0.75").press()

    def test_short_prompt_below_snapkv_window_is_noop(self):
        # SnapKV cannot compress prompts shorter than its observation window
        # (64); such items run uncompressed with kv_ratio recorded as 0.0 —
        # and the no-op path must work without kvpress installed.
        cfg = parse("snapkv@r0.75")
        assert cfg.effective_ratio(57) == 0.0
        assert cfg.press(prefill_len=57) is None
        assert cfg.effective_ratio(65) == 0.75

    def test_budget_satisfied_is_noop_without_kvpress(self):
        # ratio == 0 short-circuits BEFORE the kvpress import, so the no-op
        # path must work on the Mac dev box (no CUDA extras installed)
        assert parse("snapkv@b2048").press(prefill_len=512) is None

    def test_budget_exceeded_needs_kvpress(self):
        kvpress = pytest.importorskip("kvpress")
        press = parse("snapkv@b2048").press(prefill_len=4096)
        assert press.compression_ratio == pytest.approx(0.5)


def test_press_window_override_parses():
    cfg = parse("snapkv@r0.75:w128")
    assert cfg.kind == "press"
    assert cfg.params == {"press": "snapkv", "ratio": 0.75, "window": 128}
    # window+1 floor replaces the default PRESS_MIN_PREFILL
    assert cfg.effective_ratio(128) == 0.0
    assert cfg.effective_ratio(129) == 0.75


def test_press_window_override_reaches_kvpress_kwargs():
    cfg = parse("snapkv@r0.75:w256")
    kvpress = pytest.importorskip("kvpress")
    press = cfg.press(prefill_len=4096)
    assert press.window_size == 256
    assert press.compression_ratio == 0.75


def test_press_without_window_unchanged():
    cfg = parse("snapkv@r0.75")
    assert "window" not in cfg.params
    assert cfg.effective_ratio(64) == 0.0   # default snapkv floor 65
    assert cfg.effective_ratio(65) == 0.75


def test_malformed_window_rejected():
    for bad in ("snapkv@r0.75:w0", "snapkv@r0.75:w", "snapkv@r0.75w128"):
        with pytest.raises(ValueError):
            parse(bad)


class TestPerItemOracleWindow:
    """":wq<c>" — the per-item oracle window w_i = c + |Q_i|
    (docs/iclr-oracle-preregister.md)."""

    def test_parse(self):
        cfg = parse("snapkv@r0.75:wq167")
        assert cfg.kind == "press"
        assert cfg.params == {"press": "snapkv", "ratio": 0.75, "wq_c": 167}

    def test_window_is_c_plus_q(self):
        cfg = parse("snapkv@r0.75:wq167")
        assert cfg.resolved_window(q_tokens=53) == 220
        assert cfg.resolved_window(q_tokens=170) == 337

    def test_needs_q_tokens(self):
        cfg = parse("snapkv@r0.75:wq167")
        with pytest.raises(ValueError):
            cfg.resolved_window()
        with pytest.raises(ValueError):
            cfg.effective_ratio(8192)

    def test_min_prefill_moves_per_item(self):
        cfg = parse("snapkv@r0.75:wq167")
        # prompts at or under the per-item window run uncompressed
        assert cfg.effective_ratio(220, q_tokens=53) == 0.0
        assert cfg.effective_ratio(221, q_tokens=53) == 0.75
        assert cfg.effective_ratio(8192, q_tokens=53) == 0.75

    def test_fixed_window_unaffected(self):
        cfg = parse("snapkv@r0.75:w247")
        assert cfg.resolved_window() == 247
        assert cfg.resolved_window(q_tokens=99) == 247
        assert cfg.effective_ratio(8192) == 0.75

    def test_rejects_malformed(self):
        for bad in ("snapkv@r0.75:wq0", "snapkv@r0.75:wq", "snapkv@r0.75:wq167:w64"):
            with pytest.raises(ValueError):
                parse(bad)
