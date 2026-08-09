from mlkv.qc_screen import ScreenRecord, chrf_scores, rank_and_flag, write_report


def _rec(i, score, audited=False):
    return ScreenRecord(index=i, vi=f"vi{i}", en=f"en{i}", back=f"bt{i}",
                        chrf=score, audited=audited)


class TestRankAndFlag:
    def test_flags_bottom_n_ascending(self):
        records = rank_and_flag([_rec(0, 90.0), _rec(1, 30.0), _rec(2, 60.0)], 2)
        assert [r.index for r in records] == [1, 2, 0]
        assert [r.flagged for r in records] == [True, True, False]

    def test_n_flag_larger_than_set(self):
        records = rank_and_flag([_rec(0, 50.0)], 15)
        assert records[0].flagged


class TestChrf:
    def test_identity_scores_high_and_divergence_low(self):
        ref = "He bought 16 apples and sold them for $2 each."
        good, bad = chrf_scores([ref, "Completely unrelated sentence."], [ref, ref])
        assert good > 95
        assert bad < good

    def test_noun_swap_lowers_score(self):
        # the error class the screen hunts: same structure, one noun diverges
        ref = "A trader buys some bags of wheat from a farmer."
        hyp = "A trader buys some bags of rice from a farmer."
        [score] = chrf_scores([hyp], [ref])
        assert score < 95


class TestReport:
    def test_report_contains_flagged_items_and_ranking(self, tmp_path):
        records = rank_and_flag(
            [_rec(0, 90.0), _rec(1, 30.0, audited=True), _rec(2, 60.0)], 1)
        out = tmp_path / "screen.md"
        write_report(records, str(out), 1)
        text = out.read_text()
        assert "F1. mgsm-vi-1" in text          # flagged block
        assert "already in 30-item audit" in text
        assert "F2." not in text                # only bottom-1 flagged
        assert "| 3 | mgsm-vi-0 | 90.0" in text  # full ranking table
