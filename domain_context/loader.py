"""读取并检查共享领域资料。"""

import json
from pathlib import Path

REQUIRED = {
    "domain",
    "version",
    "sample_id",
    "record_types",
    "workflow_states",
    "facts",
    "planning",
    "guidance_rules",
    "reschedule_events",
    "offline_record",
    "resources",
    "traceability",
    "sample",
}

# 出现即需重算后续任务的六类事件
RESCHEDULE_EVENT_CODES = {
    "disease",
    "equipment_downtime",
    "formula_correction",
    "seedling_transfer",
    "delayed_harvest",
    "cold_chain_change",
}

PLANNING_MODULES = {"土壤检测", "育苗", "植保", "水肥配方", "班次排程", "采收订单"}


def load_domain(path: Path) -> dict:
    """返回字段完整且符合季次协同约定的领域资料。"""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not REQUIRED.issubset(value):
        raise ValueError("领域资料缺少必要字段")
    if value["version"] < 2 or len(value["record_types"]) < 6 or len(value["workflow_states"]) < 3:
        raise ValueError("领域资料内容不完整")

    planning = value["planning"]
    if planning.get("unit") != "作物季次":
        raise ValueError("排程必须以作物季次为单位")
    if not {"温室棚区", "作物批次"}.issubset(planning.get("organize_around", [])):
        raise ValueError("排程必须围绕棚区和作物批次组织")
    if not PLANNING_MODULES.issubset(planning.get("modules", [])):
        raise ValueError("季次模块不完整")

    rules = value["guidance_rules"]
    for key, field in (("expert_plan", "适用条件"), ("field_adjustment", "观察依据")):
        rule = rules.get(key, {})
        if rule.get("required_field") != field or not rule.get("requirement"):
            raise ValueError(f"指导规则缺少{field}约定")

    events = value["reschedule_events"]
    codes = {e.get("code") for e in events}
    if codes != RESCHEDULE_EVENT_CODES or any(not e.get("cascade") for e in events):
        raise ValueError("重算事件类型或级联说明不完整")

    offline = value["offline_record"]
    if not {"occurred_at", "synced_at"}.issubset(offline.get("fields", [])) or "occurred_at" not in offline.get(
        "rule", ""
    ):
        raise ValueError("离线记录必须区分发生时间与同步时间并按发生时间落位")

    resources = value["resources"]
    if not {"工人", "滴灌设备"}.issubset(resources.get("constrained_resources", [])):
        raise ValueError("受限资源必须包含工人和滴灌设备")
    if resources.get("gap_lookahead_days", 0) < 1:
        raise ValueError("资源缺口预测窗口无效")

    trace = value["traceability"]
    if trace.get("anchor") != "采收批次":
        raise ValueError("溯源必须以采收批次为锚点")
    chain = set(trace.get("chain", []))
    if not {"装箱产品", "棚区", "投入品批次（有机肥/生物制剂/肥料）", "田间操作及操作人", "农技方案版本"}.issubset(
        chain
    ):
        raise ValueError("溯源链不完整")
    versioning = trace.get("recipe_versioning", {})
    if not versioning.get("rule") or not versioning.get("execution_record"):
        raise ValueError("方案版本化约定不完整")

    return value
