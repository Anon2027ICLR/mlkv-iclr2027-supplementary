from mlkv.compression import parse
from mlkv.runner import _count_new_tokens, _plan_batches, effective_batch_size


class TestEffectiveBatchSize:
    def test_press_forced_single_stream(self):
        assert effective_batch_size(parse("snapkv@r0.75"), 16) == 1
        assert effective_batch_size(parse("snapkv@b1024"), 16) == 1

    def test_quant_and_baseline_batch(self):
        assert effective_batch_size(parse("baseline"), 16) == 16
        assert effective_batch_size(parse("kv4"), 16) == 16
        assert effective_batch_size(parse("kv2h"), 16) == 16

    def test_default_is_single(self):
        assert effective_batch_size(parse("baseline"), 1) == 1


class TestPlanBatches:
    def test_sorted_by_length_and_chunked(self):
        entries = ["aaaa", "a", "aaa", "aa", "aaaaa"]
        batches = _plan_batches(entries, 2, length_of=len)
        assert batches == [["a", "aa"], ["aaa", "aaaa"], ["aaaaa"]]

    def test_empty(self):
        assert _plan_batches([], 8, length_of=len) == []


class TestCountNewTokens:
    def test_no_padding_hits_max_length(self):
        assert _count_new_tokens([5, 6, 7], pad_id=0) == 3

    def test_eos_then_pads_counts_the_eos(self):
        # pad==eos: [tok, tok, eos, pad, pad] -> 3 (matches single-stream len)
        assert _count_new_tokens([5, 6, 0, 0, 0], pad_id=0) == 3

    def test_single_eos_only(self):
        assert _count_new_tokens([0], pad_id=0) == 1
