import unittest

from app.constraints import parse_flight_request
from app.runtime import BrowserManager


class FlightRuntimeTests(unittest.TestCase):
    def test_parses_preferences(self):
        request = parse_flight_request("Find non-stop flights from Hyderabad, IN to Delhi, IN on 2026-08-25, shortest first")
        assert request is not None
        self.assertEqual(request.origin, "Hyderabad, IN")
        self.assertTrue(request.non_stop_only)
        self.assertEqual(request.sort_by, "duration")

    def test_extracts_flight_cards(self):
        options = BrowserManager._extract_flight_options("Partial Refundable\nIndiGo\n6E-179\n07:15\n4h 45m\n1 stop\n12:00\n₹6,722")
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].price, "₹6,722")


if __name__ == "__main__":
    unittest.main()
