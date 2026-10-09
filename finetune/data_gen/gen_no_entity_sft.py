"""补充 NER 无实体样本 —— 教师生成多样化"不含医疗实体"的句子，标签为全空数组。

背景：模板式无实体句只有 8 个，去重后训练集里空标签样本过少，
模型可能学不到"没有实体就输出空数组"的行为。本脚本用教师批量生成
日常/平台类句子（明确禁止出现疾病/症状/药品/检查/科室词汇），并做
实体词黑名单校验，确保空标签零噪声。

用法：python data_gen/gen_no_entity_sft.py --n 60
"""
import argparse
import sys
from typing import List

from common import DATA_DIR, conversation, load_done_ids, merge_jsonl
from kg_seed import NER_KEYS, NER_SYSTEM, NER_USER_TEMPLATE
from llm_client import LLMClient, normalize_output

from gen_ner_sft import empty_labels, labels_json

INSTRUCTION = """请写 {n} 个中文句子，场景是用户在智能问诊平台上的日常闲聊或平台使用问题。

严格要求：
1. 每个句子都不能包含任何疾病名、症状名、药品名、检查项目名或科室名（连"头疼""胃"这类词都不要出现）
2. 主题示例：平台操作（注册/挂号流程/修改资料/客服时间）、日常闲聊（天气/运动心情/做饭/出行）、系统功能咨询（历史记录/隐私/费用）等
3. 每句 8~30 字，语气自然多样（有的礼貌、有的随意、有的着急）
4. 严格输出JSON：{{"sentences": ["句子1", "句子2", ...]}}，不要输出其他文字"""

# 黑名单：KG 实体 + 常见医疗词表，命中即拒收（保证空标签零噪声）
from kg_seed import DEPARTMENTS, DISEASES, DRUGS, EXAMINATIONS, MEDICAL_KEYWORDS, SYMPTOMS  # noqa: E402

BLACKLIST = (
    [d for d, *_ in DISEASES] + [s for s, *_ in SYMPTOMS] + [m for m, *_ in DRUGS]
    + [e for e, *_ in EXAMINATIONS] + [p for p, *_ in DEPARTMENTS]
    + MEDICAL_KEYWORDS["symptoms"] + MEDICAL_KEYWORDS["diseases"]
    + MEDICAL_KEYWORDS["medications"] + MEDICAL_KEYWORDS["examinations"]
)


def is_clean(sentence: str) -> bool:
    return not any(w in sentence for w in BLACKLIST)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=60, help="目标补充条数")
    parser.add_argument("--batches", type=int, default=6, help="教师调用次数（每次约 n/batches 句）")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    out_path = DATA_DIR / "sft_ner.jsonl"
    done = load_done_ids(out_path)
    client = LLMClient(model=args.model, base_url=args.base_url, api_key=args.api_key, max_workers=3)

    per_batch = args.n // args.batches + 1
    requests = [{"user": INSTRUCTION.format(n=per_batch), "temperature": 0.9, "max_tokens": 1500}
                for _ in range(args.batches)]
    outs = client.chat_many(requests, desc="无实体句")

    from llm_client import extract_json

    rows, clean_n = [], 0
    for out in outs:
        if not out:
            continue
        data = extract_json(out) or {}
        for s in data.get("sentences", []):
            sentence = normalize_output(str(s)).strip()
            if not sentence or sentence in done or not is_clean(sentence):
                continue
            done.add(sentence)
            rows.append(conversation("ner", NER_SYSTEM,
                                     [(NER_USER_TEMPLATE.format(query=sentence),
                                       labels_json(empty_labels()))],
                                     id=sentence))
            clean_n += 1
            if clean_n >= args.n:
                break
        if clean_n >= args.n:
            break

    total = merge_jsonl(out_path, rows)
    print(f"补充无实体样本 {len(rows)} 条，累计 {total} 条 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
