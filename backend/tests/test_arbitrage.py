import pytest

from app.core.arbitrage import (
    ArbitrageError,
    InvalidOddsError,
    MissingOddsError,
    arbitrage_pct,
    compute_arbitrage,
    sum_inverse,
    theoretical_roi_pct,
)


class TestValidArbitrage:
    def test_two_way_arbitrage(self):
        r = compute_arbitrage([2.10, 2.05], ["home", "away"], 1000)
        assert r.is_arbitrage
        assert r.sum_inverse < 1
        assert r.roi_pct == pytest.approx((1 / r.sum_inverse - 1) * 100, abs=1e-9)
        assert r.total_stake == pytest.approx(1000, abs=0.02)

    def test_payouts_equalized(self):
        r = compute_arbitrage([2.10, 2.05], ["home", "away"], 1000)
        payouts = [l.payout for l in r.legs]
        assert max(payouts) - min(payouts) < 1.0

    def test_three_way_arbitrage(self):
        r = compute_arbitrage([3.5, 4.2, 2.6], ["home", "draw", "away"], 1000)
        assert r.sum_inverse < 1
        assert r.is_arbitrage
        assert r.roi_pct > 9
        assert len(r.legs) == 3

    def test_multi_outcome_six_way(self):
        odds = [3.0, 4.5, 6.5, 8.0, 12.0, 15.0]
        r = compute_arbitrage(odds, [f"o{i}" for i in range(6)], 2000)
        assert r.sum_inverse < 1
        assert len(r.legs) == 6
        assert r.total_stake == pytest.approx(2000, abs=0.03)

    def test_exact_math(self):
        odds = [2.0, 3.0]
        expected_s = 1 / 2 + 1 / 3
        assert sum_inverse(odds) == pytest.approx(expected_s)
        assert arbitrage_pct(odds) == pytest.approx((1 - expected_s) * 100)
        assert theoretical_roi_pct(odds) == pytest.approx((1 / expected_s - 1) * 100)


class TestNoArbitrage:
    def test_two_way_no_arb(self):
        r = compute_arbitrage([1.8, 1.9], ["home", "away"], 1000)
        assert not r.is_arbitrage
        assert r.sum_inverse > 1
        assert r.roi_pct < 0

    def test_three_way_no_arb(self):
        r = compute_arbitrage([2.0, 3.5, 1.8], ["home", "draw", "away"], 1000)
        assert not r.is_arbitrage

    def test_negative_profit_documented(self):
        r = compute_arbitrage([1.5, 2.5], ["home", "away"], 1000)
        assert r.guaranteed_profit < 0


class TestInvalidOdds:
    def test_missing_odds(self):
        with pytest.raises(MissingOddsError):
            compute_arbitrage([2.0, None])

    def test_none_input(self):
        with pytest.raises(MissingOddsError):
            compute_arbitrage(None)

    def test_zero_odds(self):
        with pytest.raises(InvalidOddsError):
            compute_arbitrage([2.0, 0.0])

    def test_negative_odds(self):
        with pytest.raises(InvalidOddsError):
            compute_arbitrage([2.0, -1.5])

    def test_odds_equal_one(self):
        with pytest.raises(InvalidOddsError):
            compute_arbitrage([2.0, 1.0])

    def test_single_outcome(self):
        with pytest.raises(MissingOddsError):
            compute_arbitrage([2.0])

    def test_nan_and_inf(self):
        with pytest.raises(InvalidOddsError):
            compute_arbitrage([2.0, float("nan")])
        with pytest.raises(InvalidOddsError):
            compute_arbitrage([2.0, float("inf")])

    def test_outcome_mismatch(self):
        with pytest.raises(ArbitrageError):
            compute_arbitrage([2.0, 2.2], ["home", "draw", "away"])

    def test_non_numeric(self):
        with pytest.raises(InvalidOddsError):
            compute_arbitrage([2.0, "2.5"])

    def test_bad_bankroll(self):
        with pytest.raises(ArbitrageError):
            compute_arbitrage([2.1, 2.0], total_bankroll=0)


class TestRoundingAndFees:
    def test_rounding_keeps_total(self):
        r = compute_arbitrage([1.93, 2.11], ["home", "away"], 777.77,
                              stake_step=0.5)
        assert r.total_stake <= 777.77
        assert abs(r.total_stake % 0.5) < 1e-9 or r.total_stake == pytest.approx(
            sum(l.stake for l in r.legs))

    def test_fee_reduces_profit(self):
        r0 = compute_arbitrage([2.1, 2.05], ["home", "away"], 1000, fee_pct=0)
        assert r0.is_arbitrage
        r1 = compute_arbitrage([2.1, 2.05], ["home", "away"], 1000, fee_pct=5)
        assert r1.guaranteed_profit < r0.guaranteed_profit

    def test_fee_reduces_effective_odds(self):
        r = compute_arbitrage([2.1, 2.05], ["home", "away"], 1000, fee_pct=5)
        assert r.legs[0].payout < r.legs[0].stake * 2.1 - 1e-9

    def test_fee_makes_profit_negative(self):
        r = compute_arbitrage([2.1, 2.05], ["home", "away"], 1000, fee_pct=10)
        # 3.7% edge cannot survive a 10% commission on winnings
        assert not r.is_arbitrage
        assert r.guaranteed_profit < 0

    def test_fee_info_note(self):
        r = compute_arbitrage([2.1, 2.05], ["home", "away"], 1000, fee_pct=2)
        assert any("Commission" in n for n in r.notes)

    def test_stake_step_zero_disables_rounding(self):
        r = compute_arbitrage([2.1, 2.05], ["home", "away"], 999.99, stake_step=0)
        assert r.total_stake == pytest.approx(999.99, abs=1e-6)
