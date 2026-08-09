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

    def test_budget_mode_requires_prefill_len(self):
        with pytest.raises(ValueError):
            parse("snapkv@b2048").press()

    def test_budget_satisfied_is_noop_without_kvpress(self):
        # ratio == 0 short-circuits BEFORE the kvpress import, so the no-op
        # path must work on the Mac dev box (no CUDA extras installed)
        assert parse("snapkv@b2048").press(prefill_len=512) is None

    def test_budget_exceeded_needs_kvpress(self):
        kvpress = pytest.importorskip("kvpress")
        press = parse("snapkv@b2048").press(prefill_len=4096)
        assert press.compression_ratio == pytest.approx(0.5)
