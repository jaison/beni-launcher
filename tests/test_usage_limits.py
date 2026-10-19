import os
import sys
import time
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from usage_limits import (  # noqa: E402
    compute_status,
    limits_for_day,
    validate_category_limits,
    weekday_key,
)


LIMITS = {
    "enabled": True,
    "totalMinutes": 60,
    "categories": {"jogos": {"minutes": 30}, "educativo": {"minutes": 30}},
    "weekdays": {
        "sat": {"totalMinutes": 150, "categories": {"jogos": 120, "educativo": 30}},
        "sun": {"totalMinutes": None, "categories": {"jogos": 90}},
    },
}


def at(year, month, day, hour=12):
    return time.mktime(datetime(year, month, day, hour).timetuple())


class WeekdayLimitsTest(unittest.TestCase):
    def test_validation_keeps_weekdays(self):
        clean = validate_category_limits(LIMITS)
        self.assertEqual(clean["weekdays"]["sat"]["categories"]["jogos"], 120)
        self.assertIsNone(clean["weekdays"]["sun"]["totalMinutes"])

    def test_validation_rejects_bad_day(self):
        with self.assertRaises(ValueError):
            validate_category_limits({**LIMITS, "weekdays": {"sab": {}}})

    def test_validation_drops_unknown_category(self):
        clean = validate_category_limits({**LIMITS, "weekdays": {"mon": {"categories": {"xyz": 5}}}})
        self.assertEqual(clean["weekdays"]["mon"], {})

    def test_limits_for_day(self):
        self.assertEqual(limits_for_day(LIMITS, "mon")["totalMinutes"], 60)
        sat = limits_for_day(LIMITS, "sat")
        self.assertEqual(sat["totalMinutes"], 150)
        self.assertEqual(sat["categories"]["jogos"]["minutes"], 120)
        sun = limits_for_day(LIMITS, "sun")
        self.assertIsNone(sun["totalMinutes"])
        self.assertEqual(sun["categories"]["educativo"]["minutes"], 30)  # sem override: padrão
        self.assertEqual(LIMITS["categories"]["jogos"]["minutes"], 30)  # não altera o original

    def test_weekday_key(self):
        self.assertEqual(weekday_key(at(2026, 10, 19)), "mon")
        self.assertEqual(weekday_key(at(2026, 10, 24)), "sat")

    def test_status_uses_todays_limits(self):
        profile = {"categoryLimits": LIMITS, "tiles": [{"id": "luanti", "category": "jogos"}]}
        usage = {"totalSeconds": 40 * 60, "categories": {"jogos": 40 * 60}}
        monday = compute_status(profile, usage, now=at(2026, 10, 19))
        self.assertEqual(monday["weekday"], "mon")
        self.assertIn("luanti", monday["blockedTileIds"])
        saturday = compute_status(profile, usage, now=at(2026, 10, 24))
        self.assertNotIn("luanti", saturday["blockedTileIds"])
        jogos = next(c for c in saturday["categories"] if c["id"] == "jogos")
        self.assertEqual(jogos["minutes"], 120)
        self.assertEqual(jogos["availableSeconds"], 80 * 60)
        self.assertTrue(saturday["weekdayLimits"])


if __name__ == "__main__":
    unittest.main()
