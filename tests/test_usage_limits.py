import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from usage_limits import (  # noqa: E402
    HISTORY_DAYS,
    UsageTracker,
    compute_status,
    default_category_for_tile,
    limits_for_day,
    load_usage,
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


POOLED = {
    "enabled": True,
    "totalMinutes": 60,
    "categories": {
        "jogos": {"minutes": 30},
        "educativo": {"minutes": 30},
        "passatempo": {"minutes": None, "pool": "jogos"},
    },
}


class PooledCategoryTest(unittest.TestCase):
    profile = {
        "categoryLimits": POOLED,
        "tiles": [
            {"id": "luanti", "category": "jogos"},
            {"id": "paint", "category": "passatempo"},
            {"id": "khan", "category": "educativo"},
        ],
    }

    def test_validation_keeps_pool(self):
        clean = validate_category_limits(POOLED)
        self.assertEqual(clean["categories"]["passatempo"]["pool"], "jogos")

    def test_validation_drops_bad_pool(self):
        bad = {**POOLED, "categories": {**POOLED["categories"], "passatempo": {"minutes": 5, "pool": "nada"}}}
        clean = validate_category_limits(bad)
        self.assertNotIn("pool", clean["categories"]["passatempo"])

    def test_pool_shares_time(self):
        usage = {"totalSeconds": 20 * 60, "categories": {"jogos": 10 * 60, "passatempo": 10 * 60}}
        status = compute_status(self.profile, usage, now=at(2026, 10, 19))
        cats = {c["id"]: c for c in status["categories"]}
        self.assertEqual(cats["jogos"]["availableSeconds"], 10 * 60)
        self.assertEqual(cats["passatempo"]["availableSeconds"], 10 * 60)
        self.assertEqual(cats["passatempo"]["minutes"], 30)
        self.assertEqual(cats["educativo"]["availableSeconds"], 30 * 60)

    def test_pool_exhausted_blocks_both(self):
        usage = {"totalSeconds": 30 * 60, "categories": {"jogos": 5 * 60, "passatempo": 25 * 60}}
        status = compute_status(self.profile, usage, now=at(2026, 10, 19))
        self.assertIn("luanti", status["blockedTileIds"])
        self.assertIn("paint", status["blockedTileIds"])
        self.assertNotIn("khan", status["blockedTileIds"])

    def test_alternatives_skip_same_pool(self):
        usage = {"totalSeconds": 0, "categories": {}}
        status = compute_status(self.profile, usage, {"tileId": "paint", "category": "passatempo"}, now=at(2026, 10, 19))
        self.assertEqual([a["id"] for a in status["active"]["alternatives"]], ["educativo"])

    def test_default_category(self):
        self.assertEqual(default_category_for_tile({"id": "colorir"}), "passatempo")
        self.assertEqual(default_category_for_tile({"id": "khan"}), "educativo")


RULE = {"enabled": True, "goalPercent": 50, "reducedPercent": 50, "mode": "fixed"}
# 2026-10-19 é segunda; "ontem" é domingo 2026-10-18.
MONDAY = at(2026, 10, 19)


def rule_profile(rule=RULE, **extra):
    limits = {**POOLED, **extra}
    if rule is not None:
        limits["learningRule"] = rule
    return {
        "categoryLimits": validate_category_limits(limits),
        "tiles": [
            {"id": "luanti", "category": "jogos"},
            {"id": "paint", "category": "passatempo"},
            {"id": "khan", "category": "educativo"},
        ],
    }


def day_usage(learn_min=0, play_min=0):
    cats = {}
    if learn_min:
        cats["educativo"] = learn_min * 60.0
    if play_min:
        cats["jogos"] = play_min * 60.0
    return {"totalSeconds": (learn_min + play_min) * 60.0, "categories": cats}


def cats_of(status):
    return {c["id"]: c for c in status["categories"]}


class LearningRuleTest(unittest.TestCase):
    def status(self, profile, yesterday=None, today=None, now=MONDAY):
        history = {"2026-10-18": yesterday} if yesterday is not None else {}
        return compute_status(profile, today, now=now, history=history)

    def test_validation_defaults_and_errors(self):
        clean = validate_category_limits({**POOLED, "learningRule": {"enabled": True}})
        self.assertEqual(clean["learningRule"], RULE)
        self.assertNotIn("learningRule", validate_category_limits(POOLED))
        for bad in (
            {"enabled": "sim"},
            {"goalPercent": 0},
            {"reducedPercent": 101},
            {"goalPercent": 50.5},
            {"mode": "outro"},
            {"extra": 1},
            [],
        ):
            with self.assertRaises(ValueError, msg=bad):
                validate_category_limits({**POOLED, "learningRule": bad})

    def test_rule_off_keeps_current_behavior(self):
        for profile in (rule_profile(rule=None), rule_profile(rule={**RULE, "enabled": False})):
            status = self.status(profile, yesterday=day_usage(0, 30))
            self.assertEqual(cats_of(status)["jogos"]["minutes"], 30)
            self.assertFalse(status["learningRule"]["active"])
            self.assertEqual(status["learningRule"]["reason"], "off")

    def test_limits_disabled_means_rule_off(self):
        profile = rule_profile(enabled=False)
        status = self.status(profile, yesterday=day_usage(0, 30))
        self.assertFalse(status["learningRule"]["enabled"])
        self.assertFalse(status["learningRule"]["active"])

    def test_goal_missed_halves_play_and_pool(self):
        status = self.status(rule_profile(), yesterday=day_usage(0, 30), today=day_usage(0, 5))
        rule = status["learningRule"]
        self.assertTrue(rule["active"])
        self.assertEqual(rule["reason"], "goal_missed")
        self.assertEqual((rule["baseMinutes"], rule["minutes"], rule["percent"]), (30, 15, 50))
        self.assertEqual(rule["yesterdayLearnedSeconds"], 0)
        self.assertEqual(rule["goalSeconds"], 15 * 60)
        cats = cats_of(status)
        self.assertEqual(cats["jogos"]["minutes"], 15)
        self.assertEqual(cats["jogos"]["availableSeconds"], 10 * 60)
        self.assertEqual(cats["passatempo"]["minutes"], 15)  # divide o pool
        self.assertTrue(cats["passatempo"]["learningReduced"])
        self.assertEqual(cats["educativo"]["minutes"], 30)  # Aprender não muda
        self.assertNotIn("learningReduced", cats["educativo"])
        self.assertEqual(status["totalMinutes"], 60)  # total do dia não muda

    def test_reduced_pool_blocks_passatempo(self):
        today = {"totalSeconds": 15 * 60, "categories": {"jogos": 5 * 60, "passatempo": 10 * 60}}
        status = self.status(rule_profile(), yesterday=day_usage(0, 30), today=today)
        self.assertIn("luanti", status["blockedTileIds"])
        self.assertIn("paint", status["blockedTileIds"])
        self.assertNotIn("khan", status["blockedTileIds"])

    def test_goal_met_no_reduction(self):
        status = self.status(rule_profile(), yesterday=day_usage(15, 30))
        self.assertEqual(status["learningRule"]["reason"], "goal_met")
        self.assertFalse(status["learningRule"]["active"])
        self.assertEqual(cats_of(status)["jogos"]["minutes"], 30)

    def test_no_usage_yesterday_no_penalty(self):
        for yesterday in (None, day_usage(0, 0)):
            status = self.status(rule_profile(), yesterday=yesterday)
            self.assertEqual(status["learningRule"]["reason"], "no_usage")
            self.assertEqual(cats_of(status)["jogos"]["minutes"], 30)

    def test_older_history_is_not_yesterday(self):
        profile = rule_profile()
        status = compute_status(profile, None, now=MONDAY, history={"2026-10-17": day_usage(0, 30)})
        self.assertEqual(status["learningRule"]["reason"], "no_usage")

    def test_learning_without_limit_has_no_goal(self):
        profile = rule_profile()
        profile["categoryLimits"]["categories"]["educativo"]["minutes"] = None
        status = self.status(profile, yesterday=day_usage(0, 30))
        self.assertEqual(status["learningRule"]["reason"], "no_goal")
        self.assertEqual(cats_of(status)["jogos"]["minutes"], 30)

    def test_play_without_limit_today(self):
        profile = rule_profile(weekdays={"mon": {"categories": {"jogos": None}}})
        status = self.status(profile, yesterday=day_usage(0, 30))
        self.assertEqual(status["learningRule"]["reason"], "no_play_limit")
        self.assertIsNone(cats_of(status)["jogos"]["minutes"])

    def test_weekday_overrides(self):
        # Domingo (ontem) Aprender 10 min -> meta 5 min; segunda (hoje) Jogar 40 min -> 20 min.
        weekdays = {"sun": {"categories": {"educativo": 10}}, "mon": {"categories": {"jogos": 40}}}
        profile = rule_profile(weekdays=weekdays)
        missed = self.status(profile, yesterday=day_usage(4, 30))
        self.assertEqual(missed["learningRule"]["goalSeconds"], 5 * 60)
        self.assertEqual(cats_of(missed)["jogos"]["minutes"], 20)
        met = self.status(profile, yesterday=day_usage(5, 30))
        self.assertEqual(met["learningRule"]["reason"], "goal_met")
        self.assertEqual(cats_of(met)["jogos"]["minutes"], 40)

    def test_proportional_mode(self):
        profile = rule_profile(rule={**RULE, "mode": "proportional"})
        half = self.status(profile, yesterday=day_usage(7.5, 30))  # metade da meta de 15
        self.assertEqual(half["learningRule"]["percent"], 75)
        self.assertEqual(cats_of(half)["jogos"]["minutes"], 22)
        zero = self.status(profile, yesterday=day_usage(0, 30))
        self.assertEqual(cats_of(zero)["jogos"]["minutes"], 15)

    def test_today_progress(self):
        status = self.status(rule_profile(), today=day_usage(10, 0))
        today = status["learningRule"]["today"]
        self.assertEqual((today["goalSeconds"], today["learnedSeconds"], today["met"]), (900, 600, False))
        self.assertTrue(self.status(rule_profile(), today=day_usage(15, 0))["learningRule"]["today"]["met"])


class UsageHistoryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.directory.name, "usage-today.json")
        self.now = at(2026, 10, 18, 20)
        self.alive = True
        self.profile = rule_profile()

    def tearDown(self):
        self.directory.cleanup()

    def tracker(self, stop=lambda: None):
        return UsageTracker(
            self.path, lambda: {"default": self.profile}, lambda: self.alive, stop,
            clock=lambda: self.now,
        )

    def play(self, tracker, tile, category, seconds):
        tracker.set_active("default", tile, category)
        for _ in range(int(seconds // 5)):
            self.now += 5
            tracker.tick()
        tracker.clear_active()

    def test_roll_day_moves_usage_to_history(self):
        tracker = self.tracker()
        self.play(tracker, "luanti", "jogos", 20 * 60)
        self.now = at(2026, 10, 19, 9)
        status = tracker.status("default", self.profile)
        self.assertEqual(status["date"], "2026-10-19")
        self.assertEqual(status["totalUsedSeconds"], 0)
        self.assertTrue(status["learningRule"]["active"])
        self.assertEqual(cats_of(status)["jogos"]["minutes"], 15)
        self.assertEqual(tracker.usage["history"]["default"]["2026-10-18"]["categories"]["jogos"], 1200)

    def test_history_survives_restart_and_old_file(self):
        tracker = self.tracker()
        self.play(tracker, "khan", "educativo", 20 * 60)
        tracker.shutdown()
        # Servidor parado na virada: o arquivo de ontem vira histórico ao carregar.
        self.now = at(2026, 10, 19, 9)
        status = self.tracker().status("default", self.profile)
        self.assertEqual(status["learningRule"]["reason"], "goal_met")
        self.assertEqual(status["learningRule"]["yesterdayLearnedSeconds"], 1200)

    def test_old_file_without_history_loads(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"usageVersion": 1, "date": "2026-10-18",
                       "profiles": {"default": {"totalSeconds": 600, "categories": {"jogos": 600}}}}, handle)
        usage = load_usage(self.path, now=at(2026, 10, 18, 21))
        self.assertEqual(usage["profiles"]["default"]["totalSeconds"], 600)
        self.assertEqual(usage["history"], {})
        rolled = load_usage(self.path, now=at(2026, 10, 19, 8))
        self.assertEqual(rolled["profiles"], {})
        self.assertEqual(rolled["history"]["default"]["2026-10-18"]["totalSeconds"], 600)

    def test_history_is_pruned_and_sanitized(self):
        history = {"default": {
            "2026-09-01": {"totalSeconds": 60, "categories": {}},
            "2026-10-10": {"totalSeconds": 60, "categories": {"jogos": 60, "x": "y"}},
            "ontem": {"totalSeconds": 60, "categories": {}},
            "2026-10-19": {"totalSeconds": 60, "categories": {}},
        }, "outro": "lixo"}
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"usageVersion": 1, "date": "2026-10-19", "profiles": {}, "history": history}, handle)
        usage = load_usage(self.path, now=at(2026, 10, 19, 8))
        self.assertEqual(list(usage["history"]), ["default"])
        self.assertEqual(list(usage["history"]["default"]), ["2026-10-10"])
        self.assertEqual(usage["history"]["default"]["2026-10-10"]["categories"], {"jogos": 60.0})
        self.assertEqual(HISTORY_DAYS, 14)

    def test_reset_keeps_history(self):
        tracker = self.tracker()
        self.play(tracker, "luanti", "jogos", 60)
        self.now = at(2026, 10, 19, 9)
        self.play(tracker, "luanti", "jogos", 60)
        tracker.reset("default")
        self.assertIn("2026-10-18", tracker.usage["history"]["default"])
        self.assertTrue(tracker.status("default", self.profile)["learningRule"]["active"])

    def test_enforcement_uses_reduced_limit(self):
        stopped = []
        tracker = self.tracker(stop=lambda: stopped.append(1))
        self.play(tracker, "luanti", "jogos", 30)  # ontem: só jogou
        self.now = at(2026, 10, 19, 9)
        tracker.set_active("default", "luanti", "jogos")
        for _ in range((15 * 60 + 30) // 5):
            self.now += 5
            tracker.tick()
            if stopped:
                break
        self.assertTrue(stopped)
        self.assertLess(tracker.usage["profiles"]["default"]["totalSeconds"], 15 * 60 + 15)


if __name__ == "__main__":
    unittest.main()
