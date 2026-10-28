import unittest

from financial_extractor import (
    _candidate_score,
    _match_alias,
    _parse_amount,
    _target_year,
    _years_in_header,
)


class FinancialExtractorUnitTests(unittest.TestCase):
    def test_matches_label_at_row_start(self):
        self.assertEqual(
            _match_alias("Total current assets | 1,10,270", "CURRENT_ASSETS")[0],
            "total current assets",
        )

    def test_does_not_match_narrative_phrase(self):
        self.assertIsNone(
            _match_alias("The company reported current assets of 1,10,270", "CURRENT_ASSETS")[0]
        )

    def test_avoids_mapping_continuing_profit_to_total_net_profit(self):
        self.assertIsNone(
            _match_alias("Profit for the year from continuing operations | 49,096", "NET_PROFIT")[0]
        )

    def test_parses_indian_number_grouping(self):
        self.assertEqual(_parse_amount("1,10,270"), 110270.0)
        self.assertEqual(_parse_amount("2,67,021"), 267021.0)

    def test_parses_negative_only_for_allowed_metrics(self):
        self.assertIsNone(_parse_amount("(1,428)"))
        self.assertEqual(_parse_amount("(1,428)", allow_negative=True), -1428.0)
        self.assertEqual(_parse_amount("-20", allow_negative=True), -20.0)

    def test_target_year(self):
        self.assertEqual(_target_year("FY 2025-26"), 2026)
        self.assertEqual(_target_year("FY2026"), 2026)

    def test_header_period_range_maps_to_end_year_only(self):
        self.assertEqual(_years_in_header("2025-26"), {2026})

    def test_table_header_year(self):
        self.assertIn(2026, _years_in_header("As at March 31, 2026"))

    def test_unconfirmed_target_year_lowers_confidence(self):
        matched, _ = _candidate_score(
            "CURRENT_ASSETS",
            "Standalone Balance Sheet Current Assets",
            2026,
            "STANDALONE",
            False,
            True,
        )
        confirmed, _ = _candidate_score(
            "CURRENT_ASSETS",
            "Standalone Balance Sheet Current Assets",
            2026,
            "STANDALONE",
            True,
            True,
        )
        self.assertLess(matched, confirmed)

    def test_scope_mismatch_lowers_confidence(self):
        standalone, _ = _candidate_score(
            "CURRENT_ASSETS",
            "Standalone Balance Sheet Current Assets",
            2026,
            "STANDALONE",
            True,
            True,
        )
        consolidated, _ = _candidate_score(
            "CURRENT_ASSETS",
            "Consolidated Balance Sheet Current Assets",
            2026,
            "STANDALONE",
            True,
            True,
        )
        self.assertLess(consolidated, standalone)


if __name__ == "__main__":
    unittest.main()
