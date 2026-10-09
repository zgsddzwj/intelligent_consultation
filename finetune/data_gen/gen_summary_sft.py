"""指南摘要/患者教育 SFT 数据生成。

把两篇诊疗指南切成章节，构造三种任务（要点总结 / 通俗解释 / 注意事项清单），
由教师模型生成回答。任务人设为轻量编辑人设（线上无对应生产任务）。
"""
import argparse
import sys
from typing import Dict, List

from common import DATA_DIR, conversation, ensure_dirs, load_done_ids, merge_jsonl
from kg_seed import GUIDELINES, SUMMARY_SYSTEM, split_guideline_sections
from llm_client import LLMClient, normalize_output

TASKS = [
    {
        "name": "summary",
        "user": "请总结以下医学指南片段的要点：\n\n{content}\n\n请用简洁的条目列出核心要点，并标注来源为该指南。",
    },
    {
        "name": "patient_edu",
        "user": "请把以下医学内容改写成患者能听懂的通俗解释，避免专业术语，语气友好：\n\n{content}",
    },
    {
        "name": "checklist",
        "user": "基于以下指南内容，为患者列出日常注意事项清单（用「-」开头的条目列表）：\n\n{content}",
    },
]

# 同一单元+任务重复出现时追加的风格变体，保证 prompt 不重复并增加多样性
STYLE_VARIANTS = [
    "",
    "\n\n（请面向没有医学背景的普通患者作答）",
    "\n\n（请尽量简明扼要，控制在5条以内）",
    "\n\n（请面向需要长期自我管理的慢性病患者）",
    "\n\n（请用温和鼓励的语气）",
    "\n\n（请补充说明每条要点对患者日常生活的实际影响）",
    "\n\n（请面向中老年患者，注意可读性）",
    "\n\n（请突出最容易做错或忽略的地方）",
    "\n\n（请用更口语化的表达）",
    "\n\n（请同时说明不遵守这些要点的常见后果）",
]


def build_units() -> List[Dict]:
    """指南 → 单元（全文 / 章节），附来源标注。"""
    sources = {
        "高血压诊疗指南.txt": "《中国高血压防治指南2023》",
        "糖尿病管理指南.txt": "《中国2型糖尿病防治指南2020》",
    }
    units = []
    for filename, text in GUIDELINES.items():
        source = sources[filename]
        sections = split_guideline_sections(text)
        # 全文做一个单元（任务限定为总结）
        units.append({"content": text, "source": source, "section": "全文",
                      "allowed_tasks": ["summary"]})
        for title, body in sections:
            if len(body) < 60:  # 过短章节并入全文即可
                continue
            units.append({"content": body, "source": source, "section": title,
                          "allowed_tasks": ["summary", "patient_edu", "checklist"]})
    return units


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=300, help="样本总数")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    n = 15 if args.dry_run else args.n
    out_dir = DATA_DIR / ("samples" if args.dry_run else ".")
    out_path = out_dir / "sft_summary.jsonl"
    ensure_dirs()

    units = build_units()
    # 枚举 (单元, 任务) 组合并轮转分配；重复轮次追加风格变体避免 prompt 重复
    unit_tasks = [(unit, task) for unit in units for task in TASKS
                  if task["name"] in unit["allowed_tasks"]]
    # 断点续跑：id = 完整 user prompt，跳过已完成组合
    done = set() if args.dry_run else load_done_ids(out_path)
    requests, metas = [], []
    for k in range(n):
        unit, task = unit_tasks[k % len(unit_tasks)]
        variant = STYLE_VARIANTS[(k // len(unit_tasks)) % len(STYLE_VARIANTS)]
        user = task["user"].format(content=unit["content"]) + variant
        if user in done:
            continue
        requests.append({"system": SUMMARY_SYSTEM, "user": user, "temperature": 0.6, "max_tokens": 1000})
        metas.append({"task": task["name"], "unit": unit})
    if done:
        print(f"断点续跑：已有 {len(done)} 条，本轮新增 {len(requests)} 条")

    client = LLMClient(model=args.model, base_url=args.base_url, api_key=args.api_key,
                       max_workers=args.workers)
    print(f"教师模型生成 {len(requests)} 条（单元 {len(units)} 个、组合 {len(unit_tasks)} 种）...")
    outs = client.chat_many(requests, desc="摘要")

    rows = []
    for req, meta, out in zip(requests, metas, outs):
        if not out:
            continue
        answer = normalize_output(out)
        if len(answer) < 30:
            continue
        answer = answer.rstrip() + f"\n\n[来源] {meta['unit']['source']}"
        rows.append(conversation(f"summary_{meta['task']}", SUMMARY_SYSTEM,
                                 [(req["user"], answer)], id=req["user"]))

    total = merge_jsonl(out_path, rows)
    print(f"完成：本轮 {len(rows)} 条，累计 {total} 条 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
