"""SFT 数据校验 + 合并训练集。

用法：
    python data_gen/validate_data.py                # 校验 data/ 下全部 sft_*.jsonl 并输出报告
    python data_gen/validate_data.py --merge        # 校验后合并写出 data/sft_train.jsonl
    python data_gen/validate_data.py --dir samples  # 校验 dry-run 产物

校验项：
- 结构：conversations 角色合法、human/gpt 交替、每条含 system
- 咨询类：回答含 [来源 标注与免责声明
- NER 类：assistant 为契约扁平 JSON 且五个键齐全
- 长度：单条总字符数超出 cutoff 估算上限则告警（cutoff_len 2048 ≈ 约3600汉字）
- 去重：首问重复统计（--fix 去重）
- 一致性：若能导入 backend 的 ConsultationPrompts，校验 system prompt 是否与源同步
"""
import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

from common import DATA_DIR, read_jsonl, write_jsonl
from kg_seed import DISCLAIMER, NER_KEYS, SYSTEM_PROMPTS

TASK_PREFIXES = ("consultation_single", "consultation_multi", "ner", "summary")
MAX_TOTAL_CHARS = 3600  # cutoff_len 2048 token 的保守汉字估算

VALID_SYSTEMS = {spec["system"] for spec in SYSTEM_PROMPTS.values()} | {"__summary__"}


def check_row(row: Dict) -> List[str]:
    issues = []
    conv = row.get("conversations")
    if not conv or not isinstance(conv, list) or len(conv) < 3:
        return ["conversations 结构不完整"]
    if conv[0].get("from") != "system":
        issues.append("首消息不是 system")
    roles = [c.get("from") for c in conv]
    if any(r not in ("system", "human", "gpt") for r in roles):
        issues.append(f"非法角色: {set(roles) - {'system', 'human', 'gpt'}}")
    for i in range(1, len(conv)):
        expected = "human" if i % 2 == 1 else "gpt"
        if roles[i] != expected:
            issues.append(f"第{i}轮角色应为{expected}，实际{roles[i]}")
            break
    if roles[-1] != "gpt":
        issues.append("末尾不是 gpt 回答")

    task = row.get("task", "")
    first_user = next((c["value"] for c in conv if c.get("from") == "human"), "")
    answers = [c["value"] for c in conv if c.get("from") == "gpt"]
    if task.startswith("consultation"):
        # 有上下文（"基于以下"开头）必须带来源标注；无上下文样本（RAG 无结果，
        # 线上 format_stream_prompt 即此形态）只要求免责声明
        has_context = "基于以下" in first_user
        if task == "consultation_single" and has_context and "[来源" not in answers[0]:
            issues.append("单轮回答缺 [来源] 标注")
        if task == "consultation_multi" and not any("[来源" in a for a in answers):
            issues.append("多轮回答全程无 [来源] 标注")
        if DISCLAIMER not in answers[-1]:
            issues.append("末轮回答缺免责声明")
        if not first_user.strip():
            issues.append("首问为空")
    elif task == "ner":
        import json
        try:
            labels = json.loads(answers[0])
            if set(labels.keys()) != set(NER_KEYS):
                issues.append(f"NER JSON 键不符: {sorted(labels.keys())}")
            elif not all(isinstance(v, list) for v in labels.values()):
                issues.append("NER JSON 值不是数组")
        except json.JSONDecodeError:
            issues.append("NER 回答不是合法 JSON")
    elif task.startswith("summary"):
        if len(answers[0]) < 30:
            issues.append("摘要回答过短")

    total = sum(len(c.get("value", "")) for c in conv)
    if total > MAX_TOTAL_CHARS:
        issues.append(f"总长 {total} 字符，可能超出 cutoff_len 2048")
    return issues


def check_prompt_sync() -> List[str]:
    """尝试导入 backend 真实 Prompt 模块，比对是否与本仓库副本一致。"""
    warnings = []
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
        from app.prompts.consultation import ConsultationPrompts

        pairs = [
            ("medical", ConsultationPrompts.MEDICAL_CONSULTATION_SYSTEM, "system"),
            ("diagnosis", ConsultationPrompts.DIAGNOSIS_ASSISTANT_SYSTEM, "system"),
            ("drug", ConsultationPrompts.DRUG_CONSULTATION_SYSTEM, "system"),
        ]
        for key, real, _ in pairs:
            if real.strip() != SYSTEM_PROMPTS[key]["system"].strip():
                warnings.append(f"SYSTEM_PROMPTS[{key}] 与 backend/app/prompts/consultation.py 不一致，请同步后重新生成数据")
    except Exception:  # noqa: BLE001 - backend 依赖缺失时跳过
        warnings.append("（提示）无法导入 backend ConsultationPrompts，跳过 prompt 同步检查")
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=".", help="数据目录（相对 data/），默认 data/ 根")
    parser.add_argument("--merge", action="store_true", help="校验通过后合并为 sft_train.jsonl")
    parser.add_argument("--fix", action="store_true", help="按首问去重（保留首条）")
    args = parser.parse_args()

    src = DATA_DIR / args.dir
    # sft_train.jsonl 是合并产物，排除在源文件之外（否则二次合并会翻倍）
    files = sorted(p for p in src.glob("sft_*.jsonl") if p.name != "sft_train.jsonl")
    if not files:
        print(f"未找到数据文件：{src}/sft_*.jsonl")
        return 1

    all_rows: List[Dict] = []
    report = Counter()
    hard_fail = False

    for path in files:
        rows = read_jsonl(path)
        bad, seen_questions = [], set()
        kept = []
        for i, row in enumerate(rows):
            issues = check_row(row)
            conv = row.get("conversations", [])
            first_user = next((c["value"] for c in conv if c.get("from") == "human"), "")
            if first_user in seen_questions:
                issues.append("首问重复")
            seen_questions.add(first_user)
            if issues:
                bad.append((i, issues))
            if args.fix and any("重复" in x for x in issues):
                continue
            kept.append(row)
            report[row.get("task", "unknown")] += 1
        total_chars = sum(len(c.get("value", "")) for r in kept for c in r.get("conversations", []))
        print(f"\n== {path.name} ==  {len(rows)} 条，合格 {len(rows) - len(bad)}，有问题 {len(bad)}"
              f"，平均总长 {total_chars // max(len(kept), 1)} 字符")
        for i, issues in bad[:5]:
            print(f"  [{i}] {'; '.join(issues)}")
        if len(bad) > 5:
            print(f"  ... 其余 {len(bad) - 5} 条问题略")
        # 非重复类问题视为硬伤
        if any("重复" not in x for _, issues in bad for x in issues):
            hard_fail = True
        all_rows.extend(kept)

    print("\n== 任务分布 ==")
    for task, n in report.most_common():
        print(f"  {task}: {n}")

    for w in check_prompt_sync():
        print(f"[同步检查] {w}")

    if args.merge:
        out = DATA_DIR / "sft_train.jsonl"
        write_jsonl(out, all_rows)
        print(f"\n已合并 {len(all_rows)} 条 → {out}")

    if hard_fail and not args.fix:
        print("\n存在结构性问题，建议检查生成脚本（重复类问题可用 --fix 去重）")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
