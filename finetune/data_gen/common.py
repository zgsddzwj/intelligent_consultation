"""数据生成脚本共享工具：路径、JSONL 读写、ShareGPT 样本构造、KG 上下文构建。"""
import json
import random
from pathlib import Path
from typing import Dict, List, Optional

from kg_seed import (
    DISEASES,
    DRUGS,
    DURATIONS,
    EXAMINATIONS,
    GUIDELINES,
    INTENT_TEMPLATES,
    MEDICAL_KEYWORDS,
    RELATIONSHIPS,
    SYMPTOMS,
    entity_index,
    find_entities,
    guideline_for,
)

FINETUNE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FINETUNE_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = FINETUNE_DIR / "data"
EVAL_DATA_DIR = DATA_DIR / "eval"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "samples").mkdir(parents=True, exist_ok=True)
    EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[Dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def conversation(task: str, system: str, turns: List[tuple], id: Optional[str] = None) -> Dict:
    """构造 ShareGPT 格式样本。turns 为 [(user, assistant), ...]。

    id 为该样本的业务键（如首问原文），用于断点续跑去重；LLaMA-Factory 会忽略额外字段。
    """
    conv = []
    if system:
        conv.append({"from": "system", "value": system})
    for user, assistant in turns:
        conv.append({"from": "human", "value": user})
        conv.append({"from": "gpt", "value": assistant})
    row = {"conversations": conv, "task": task}
    if id is not None:
        row["id"] = id
    return row


def load_done_ids(path: Path) -> set:
    """读取已有产物的 id 集合，用于断点续跑时跳过已完成样本。"""
    if not path.exists():
        return set()
    return {r.get("id") for r in read_jsonl(path) if r.get("id")}


def merge_jsonl(path: Path, new_rows: List[Dict]) -> int:
    """把新样本追加到已有产物（存在则合并去重 id），返回总条数。"""
    existing = read_jsonl(path) if path.exists() else []
    seen = {r.get("id") for r in existing if r.get("id")}
    added = 0
    for row in new_rows:
        rid = row.get("id")
        if rid is not None and rid in seen:
            continue
        existing.append(row)
        if rid is not None:
            seen.add(rid)
        added += 1
    write_jsonl(path, existing)
    return len(existing)


# ================================================================
# KG 上下文构建：模拟线上 RAG 检索结果拼接（与 consultation.py 的 user 模板对接）
# ================================================================

def build_kg_context(entities: List[str]) -> str:
    """根据命中的实体生成知识图谱片段（事实锚点，教师模型必须基于它作答）。"""
    if not entities:
        return ""
    idx = entity_index()
    parts: List[str] = []
    seen = set()

    def rel_of(rel_type: str, src_type: str, src: str):
        out = []
        for s_type, s_name, rel, t_type, t_name, props in RELATIONSHIPS:
            if rel == rel_type and s_type == src_type and s_name == src:
                out.append((t_type, t_name, props))
        return out

    for name in entities:
        if name in seen:
            continue
        seen.add(name)
        info = idx.get(name)
        if not info:
            continue
        etype, record = info["type"], info["record"]
        if etype == "Disease":
            _, icd10, desc, etiology = record
            parts.append(f"[知识图谱] 疾病：{name}（ICD-10: {icd10}）。{desc} 病因：{etiology}")
            sym = [(t, p.get("frequency", "")) for t_type, t, p in rel_of("HAS_SYMPTOM", "Disease", name) if t_type == "Symptom"]
            comp = [(t, p.get("frequency", "")) for t_type, t, p in rel_of("HAS_SYMPTOM", "Disease", name) if t_type == "Disease"]
            if sym:
                parts.append(f"[知识图谱] {name}的常见症状：" + "、".join(f"{t}（{f}）" if f else t for t, f in sym))
            if comp:
                parts.append(f"[知识图谱] {name}可能发展为：" + "、".join(f"{t}（{f}）" if f else t for t, f in comp))
            drugs = [(t, p.get("dosage", "")) for t_type, t, p in rel_of("TREATED_BY", "Disease", name)]
            if drugs:
                parts.append(f"[知识图谱] {name}的治疗药物：" + "；".join(f"{t}（用法：{d}）" if d else t for t, d in drugs))
            exams = [t for t_type, t, p in rel_of("REQUIRES_EXAM", "Disease", name)]
            if exams:
                parts.append(f"[知识图谱] {name}建议检查：" + "、".join(exams))
        elif etype == "Symptom":
            _, severity, desc = record
            parts.append(f"[知识图谱] 症状：{name}（严重程度：{severity}）。{desc}")
            depts = [t for t_type, t, p in rel_of("BELONGS_TO", "Symptom", name)]
            if depts:
                parts.append(f"[知识图谱] {name}建议就诊科室：" + "、".join(depts))
            diseases = [s for s_type, s, rel, t_type, t, p in RELATIONSHIPS
                        if rel == "HAS_SYMPTOM" and t_type == "Symptom" and t == name and s_type == "Disease"]
            if diseases:
                parts.append(f"[知识图谱] 出现{name}的相关疾病：" + "、".join(diseases))
        elif etype == "Drug":
            _, generic, form, indication, contraindication = record
            parts.append(f"[知识图谱] 药物：{name}（通用名 {generic}，{form}）。适应症：{indication}。禁忌：{contraindication}")
            diseases = [s for s_type, s, rel, t_type, t, p in RELATIONSHIPS
                        if rel == "TREATED_BY" and t_type == "Drug" and t == name and s_type == "Disease"]
            if diseases:
                parts.append(f"[知识图谱] {name}可用于治疗：" + "、".join(diseases))
        elif etype == "Examination":
            _, type_name, ref_range, desc = record
            parts.append(f"[知识图谱] 检查：{name}（{type_name}）。参考范围：{ref_range}。{desc}")
        elif etype == "Department":
            _, desc, scope = record
            parts.append(f"[知识图谱] 科室：{name}（{desc}，诊疗范围：{scope}）")

    # 训练中的引用编号必须与线上 RAG 上下文协议一致：每个可引用片段都具有
    # 稳定的 [来源N: 标题] 头，答案中的 [来源N] 才可被验证。
    return "\n\n".join(
        f"[来源{i}: 项目知识图谱]\n{part}" for i, part in enumerate(parts, 1)
    )


def build_context(question: str, with_guideline: bool = True) -> str:
    """实体命中 → KG 片段 + （若命中高血压/糖尿病）指南全文，模拟线上 RAG 上下文。"""
    parts = []
    kg = build_kg_context(find_entities(question))
    if kg:
        parts.append(kg)
    if with_guideline:
        idx = entity_index()
        for disease in ("高血压", "糖尿病"):
            if disease in question:
                g = guideline_for(disease)
                if g:
                    source, text = g
                    next_source_id = kg.count("[来源") + 1
                    parts.append(f"[来源{next_source_id}: {source}]\n{text}")
                break
    return "\n".join(parts)


# ================================================================
# 问句池：意图模板填充（与 train_ml_models.py 同款逻辑，实体取自 KG + 词表并集）
# ================================================================

def fill_template(template: str, rng: random.Random) -> str:
    pool = {
        "symptom_pool": list(MEDICAL_KEYWORDS["symptoms"]) + [s for s, _, _ in SYMPTOMS],
        "disease_pool": list(MEDICAL_KEYWORDS["diseases"]) + [d for d, _, _, _ in DISEASES],
        "medication_pool": list(MEDICAL_KEYWORDS["medications"]) + [d for d, *_ in DRUGS],
        "examination_pool": list(MEDICAL_KEYWORDS["examinations"]) + [e for e, *_ in EXAMINATIONS],
        "lifestyle_pool": list(MEDICAL_KEYWORDS["lifestyle"]),
    }
    filled = template
    for key, values in (
        ("symptom", pool["symptom_pool"]),
        ("symptom2", pool["symptom_pool"]),
        ("disease", pool["disease_pool"]),
        ("disease2", pool["disease_pool"]),
        ("medication", pool["medication_pool"]),
        ("medication2", pool["medication_pool"]),
        ("examination", pool["examination_pool"]),
        ("lifestyle", pool["lifestyle_pool"]),
    ):
        filled = filled.replace("{" + key + "}", rng.choice(values))
    filled = filled.replace("{duration}", rng.choice(DURATIONS))
    return filled


def build_question_pool(rng: random.Random, exclude_general: bool = True) -> List[Dict]:
    """遍历意图模板生成去重问句池，每条带 {question, intent, task}。"""
    seen, pool = set(), []
    for intent, templates in INTENT_TEMPLATES.items():
        if exclude_general and intent == "general":
            continue
        # 每个模板生成多组填充，扩大池子
        for _ in range(40):
            for template in templates:
                q = fill_template(template, rng)
                if q in seen:
                    continue
                seen.add(q)
                pool.append({"question": q, "intent": intent})
    rng.shuffle(pool)
    return pool
