import unittest

from backend.network_agent import normalize_peer_candidates, select_peer_candidates


class NetworkAgentTests(unittest.TestCase):
    def test_normalize_peer_candidates_skips_invalid_rows(self):
        payload = {
            "peers": [
                {
                    "addr": "1.2.3.4:19335",
                    "score": 0.91,
                    "blocks_behind": 0,
                    "median_ping_ms": 42,
                },
                {"score": 0.99},
                "bad",
            ],
        }

        candidates = normalize_peer_candidates(payload)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].address, "1.2.3.4:19335")
        self.assertEqual(candidates[0].score, 0.91)

    def test_select_peer_candidates_prefers_synced_high_score_low_ping(self):
        payload = {
            "peers": [
                {
                    "addr": "slow.example:19335",
                    "score": 0.92,
                    "blocks_behind": 0,
                    "median_ping_ms": 200,
                },
                {
                    "addr": "fast.example:19335",
                    "score": 0.92,
                    "blocks_behind": 0,
                    "median_ping_ms": 40,
                },
                {
                    "addr": "behind.example:19335",
                    "score": 0.99,
                    "blocks_behind": 8,
                    "median_ping_ms": 20,
                },
                {
                    "addr": "weak.example:19335",
                    "score": 0.4,
                    "blocks_behind": 0,
                    "median_ping_ms": 5,
                },
            ],
        }

        selected = select_peer_candidates(
            normalize_peer_candidates(payload),
            min_score=0.7,
            limit=3,
        )

        self.assertEqual(
            [peer.address for peer in selected],
            [
                "fast.example:19335",
                "slow.example:19335",
                "behind.example:19335",
            ],
        )


if __name__ == "__main__":
    unittest.main()
