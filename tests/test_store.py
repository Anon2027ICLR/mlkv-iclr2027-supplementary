from mlkv import store


def _save(conn, key, stack_id, correct=True):
    store.save(
        conn, key,
        model="m", task="mgsm", lang="vi", config="baseline", item_id="i1",
        stack_id=stack_id, output="#### 42", n_output_tokens=10,
        answer_gold="42", correct=correct, drift=0.0, latency_s=1.0,
    )


def test_resumable(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    stack = store.register_stack(conn, {"torch": "x"})
    key = store.run_key("m", "mgsm", "vi", "baseline", "i1")
    assert not store.is_done(conn, key)
    _save(conn, key, stack)
    assert store.is_done(conn, key)


def test_key_changes_with_config(tmp_path):
    k1 = store.run_key("m", "mgsm", "vi", "baseline", "i1")
    k2 = store.run_key("m", "mgsm", "vi", "kv4", "i1")
    assert k1 != k2


def test_stack_registration_is_idempotent(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    s1 = store.register_stack(conn, {"torch": "2.5", "device": "mps"})
    s2 = store.register_stack(conn, {"device": "mps", "torch": "2.5"})  # key order differs
    assert s1 == s2


def test_summary(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    stack = store.register_stack(conn, {})
    _save(conn, store.run_key("m", "mgsm", "vi", "baseline", "i1"), stack, correct=True)
    store.save(
        conn, store.run_key("m", "mgsm", "vi", "baseline", "i2"),
        model="m", task="mgsm", lang="vi", config="baseline", item_id="i2",
        stack_id=stack, output="#### 1", n_output_tokens=5,
        answer_gold="2", correct=False, drift=None, latency_s=0.5,
    )
    rows = store.summary(conn)
    assert len(rows) == 1
    assert rows[0]["n"] == 2
    assert abs(rows[0]["accuracy"] - 0.5) < 1e-9


def test_compression_config_parsing():
    from mlkv.compression import parse

    assert parse("baseline").kind == "baseline"
    assert parse("kv4").params["nbits"] == 4
    press = parse("snapkv@r0.75")
    assert press.kind == "press" and press.params["ratio"] == 0.75
    import pytest
    with pytest.raises(ValueError):
        parse("bogus@r0.5")
