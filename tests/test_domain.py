import json
import tempfile
import unittest
from pathlib import Path
from domain_context.loader import load_domain

FIXTURE = Path("fixtures/domain.json")

# 设计文档约定的六类触发重算事件
EXPECTED_EVENTS = {"病害发生", "设备停机", "配方更正", "跨棚调苗", "延迟采收", "冷链能力变化"}
# v2 新增的组织与协同记录类型
EXPECTED_NEW_RECORDS = {"作物批次", "育苗批次", "水肥配方", "植保记录", "班次计划", "采收订单", "冷链能力", "溯源档案"}
# v1 已公开的流程状态，顺序与取值不得变化
V1_STATES = ["待定植", "生长中", "需干预", "待采收", "已采收", "已交付"]

class DomainFixtureTest(unittest.TestCase):
    def test_fixture_is_complete(self):
        value = load_domain(FIXTURE)
        self.assertEqual(value["domain"], "plateau-greenhouse-plan")
        self.assertGreaterEqual(len(value["facts"]), 2)

    def test_v1_contract_stays_compatible(self):
        value = load_domain(FIXTURE)
        self.assertEqual(value["sample_id"], "092201-013")
        self.assertEqual(value["workflow_states"][: len(V1_STATES)], V1_STATES)
        for record_type in ("温室棚区", "作物季次", "土壤检测", "农技方案", "田间操作", "采收批次"):
            self.assertIn(record_type, value["record_types"])

    def test_v2_records_and_events_cover_scenario(self):
        value = load_domain(FIXTURE)
        self.assertGreaterEqual(value["version"], 2)
        self.assertTrue(EXPECTED_NEW_RECORDS.issubset(value["record_types"]))
        self.assertEqual(set(value["domain_events"]), EXPECTED_EVENTS)

    def test_sample_keeps_advice_and_traceability_hints(self):
        sample = load_domain(FIXTURE)["sample"]
        self.assertIn("advice_condition", sample)
        self.assertIn("field_adjustment_basis", sample)
        self.assertIn("traceability", sample)

    def test_v2_without_events_is_rejected(self):
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del value["domain_events"]
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "domain.json"
            broken.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_domain(broken)

if __name__ == "__main__":
    unittest.main()
