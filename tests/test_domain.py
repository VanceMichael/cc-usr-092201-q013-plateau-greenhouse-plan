import unittest
from datetime import datetime
from pathlib import Path

from domain_context.loader import load_domain

FIXTURE = Path("fixtures/domain.json")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


class DomainFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = load_domain(FIXTURE)
        cls.sample = cls.value["sample"]

    def test_fixture_is_complete(self):
        self.assertEqual(self.value["domain"], "plateau-greenhouse-plan")
        self.assertGreaterEqual(self.value["version"], 2)
        self.assertGreaterEqual(len(self.value["facts"]), 2)

    def test_planning_is_season_based_around_greenhouse_and_batch(self):
        planning = self.value["planning"]
        self.assertEqual(planning["unit"], "作物季次")
        self.assertEqual(
            set(planning["modules"]),
            {"土壤检测", "育苗", "植保", "水肥配方", "班次排程", "采收订单"},
        )
        self.assertEqual(self.sample["crop_batch"]["season"], "2026年秋茬")

    def test_expert_plan_carries_applicability(self):
        plan = self.sample["expert_plan_adapted"]
        self.assertTrue(plan["applicability"])
        self.assertIn("pH", plan["applicability"])
        self.assertEqual(self.value["guidance_rules"]["expert_plan"]["required_field"], "适用条件")

    def test_field_adjustment_carries_observation_basis(self):
        adj = self.sample["field_adjustment"]
        self.assertTrue(adj["observation_basis"])
        self.assertTrue(adj["action"])
        self.assertEqual(
            self.value["guidance_rules"]["field_adjustment"]["required_field"], "观察依据"
        )

    def test_six_reschedule_event_codes(self):
        codes = {e["code"] for e in self.value["reschedule_events"]}
        self.assertEqual(
            codes,
            {
                "disease",
                "equipment_downtime",
                "formula_correction",
                "seedling_transfer",
                "delayed_harvest",
                "cold_chain_change",
            },
        )
        for event in self.value["reschedule_events"]:
            self.assertTrue(event["cascade"])

    def test_sample_events_reference_known_codes_and_cascade(self):
        correction = self.sample["formula_correction"]
        downtime = self.sample["equipment_downtime"]
        self.assertEqual(correction["event"], "formula_correction")
        self.assertEqual(downtime["event"], "equipment_downtime")
        self.assertTrue(correction["recalculated_tasks"])
        self.assertTrue(downtime["cascade"])
        self.assertIn("v2", correction["unchanged"])

    def test_offline_record_lands_at_occurred_time(self):
        offline = self.sample["offline_operation"]
        occurred = parse_ts(offline["occurred_at"])
        synced = parse_ts(offline["synced_at"])
        # 田间发生在前、次日联网同步在后
        self.assertLess(occurred, synced)
        self.assertEqual(occurred.date().isoformat(), "2026-09-25")
        self.assertIn("occurred_at", self.value["offline_record"]["rule"])

    def test_resource_gaps_are_future_conflicts(self):
        gaps = self.sample["resource_gap"]
        self.assertGreaterEqual(len(gaps), 2)
        resources = {g["resource"] for g in gaps}
        self.assertEqual(resources, {"工人", "滴灌设备"})
        for gap in gaps:
            self.assertGreater(gap["gap"], 0)
            self.assertTrue(gap["conflicting_tasks"])
        self.assertGreaterEqual(self.value["resources"]["gap_lookahead_days"], 3)

    def test_harvest_lot_traces_back_to_greenhouse_inputs_operators_and_version(self):
        lot = self.sample["harvest_lot"]
        self.assertEqual(lot["greenhouse"], self.sample["greenhouse"])
        self.assertEqual(lot["crop_batch_id"], self.sample["crop_batch"]["id"])
        self.assertTrue(lot["input_lots"])
        self.assertTrue(lot["operators"])
        self.assertTrue(lot["operations"])
        # 装箱后能查回采用的技术版本
        self.assertEqual(lot["plan_version_executed"], self.sample["formula_correction"]["new_version"])
        chain = self.value["traceability"]["chain"]
        for node in ("装箱产品", "采收批次", "棚区", "田间操作及操作人", "农技方案版本"):
            self.assertIn(node, chain)

    def test_soil_test_feeds_plan_adaptation(self):
        # 外省基线方案必须逐棚适配：样例中土壤检测早于适配方案
        soil = parse_ts(self.sample["soil_test"]["sampled_on"])
        adapted = parse_ts(self.sample["expert_plan_adapted"]["adapted_on"])
        self.assertLessEqual(soil, adapted)
        self.assertIn("逐棚适配", self.sample["expert_plan_adapted"]["source"])


if __name__ == "__main__":
    unittest.main()
