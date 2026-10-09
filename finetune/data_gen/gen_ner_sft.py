"""医疗 NER SFT 数据生成 —— 标签由 KG 程序化构造（零标注噪声），教师模型仅负责改写句子。

- user 侧直接使用 app/prompts/knowledge.py 的 NER_USER 原模板
- assistant 侧为对齐线上契约的扁平 JSON（diseases/symptoms/drugs/examinations/departments）
- 约 50% 句子经教师模型改写以增加多样性，改写后校验实体未被篡改，校验失败则回退原句
- 含少量无实体样本，教会模型输出全空数组
"""
import argparse
import json
import random
import sys
from typing import Dict, List, Tuple

from common import (
    DATA_DIR,
    conversation,
    ensure_dirs,
    load_done_ids,
    merge_jsonl,
)
from kg_seed import NER_KEYS, NER_SYSTEM, NER_USER_TEMPLATE
from llm_client import LLMClient, normalize_output

# (句子模板, 实体槽位) —— 槽位: d=疾病 s=症状 m=药品 e=检查 p=科室
SENTENCE_TEMPLATES: List[Tuple[str, List[str]]] = [
    ("我最近总是{s1}，还伴有{s2}，是不是{d1}？", ["s1", "s2", "d1"]),
    ("确诊{d1}两年了，一直在吃{m1}，最近{s1}加重了", ["d1", "m1", "s1"]),
    ("医生给我开了{m1}，说{d1}患者还要定期做{e1}", ["m1", "d1", "e1"]),
    ("体检的时候{s1}偏高，医生建议我去查一下{e1}和{e2}", ["s1", "e1", "e2"]),
    ("{s1}持续一周了，想去医院看看应该挂{p1}还是{p2}？", ["s1", "p1", "p2"]),
    ("家里老人有{d1}，最近{s1}还{s2}，需要调整{m1}的剂量吗", ["d1", "s1", "s2", "m1"]),
    ("怀孕三个月了，{s1}得厉害，能吃{m1}吗？", ["s1", "m1"]),
    ("请问{e1}检查前需要注意什么？听说{d1}的人做这项检查有风险", ["e1", "d1"]),
    ("我{d1}病史五年，最近出现{s1}和{s2}，会不会是并发症", ["d1", "s1", "s2"]),
    ("吃了{m1}之后有点{s1}，需要停药吗？", ["m1", "s1"]),
    ("小孩{d1}刚好，又开始{s1}了，要不要去查个{e1}", ["d1", "s1", "e1"]),
    ("帮我看看这个报告：{e1}结果显示异常，医生说可能是{d1}", ["e1", "d1"]),
    ("{s1}和{s2}一起出现是什么原因？需要做{e1}吗", ["s1", "s2", "e1"]),
    ("长期服用{m1}对{d1}患者有什么副作用？", ["m1", "d1"]),
    ("最近{s1}、{s2}，去{p1}看了说没事，要不要换个{p2}看看", ["s1", "s2", "p1", "p2"]),
    ("{d1}和{d2}在症状上怎么区分？都会引起{s1}吗", ["d1", "d2", "s1"]),
    ("做了{e1}和{e2}，结果都正常，但{s1}还是没好转", ["e1", "e2", "s1"]),
    ("朋友推荐我买{m1}调理{d1}，靠谱吗？", ["m1", "d1"]),
    ("{s1}反复发作，医生建议做{e1}确认是不是{d1}", ["s1", "e1", "d1"]),
    ("想咨询一下，{d1}患者日常可以做{e1}这类检查来监测吗？", ["d1", "e1"]),
    ("最近总是{s1}，晚上还{s2}，去医院该挂什么科", ["s1", "s2"]),
    ("听说{m1}和{m2}不能一起吃，我{d1}正在吃{m1}，还能用{m2}吗", ["m1", "m2", "d1"]),
    ("复查{d1}需要空腹吗？之前查过{e1}", ["d1", "e1"]),
    ("{s1}快两个月了，网上查说可能是{d1}，也可能只是{d2}", ["s1", "d1", "d2"]),
    ("{d1}手术出院后{s1}又出现了，需要马上回医院吗", ["d1", "s1"]),
]

NO_ENTITY_SENTENCES = [
    "你好，我想咨询一下挂号流程",
    "今天去医院停车好难，有推荐的出行方式吗",
    "你们这个平台的客服工作时间是什么时候",
    "帮我推荐一家附近好吃的餐厅",
    "医生你好，打扰了",
    "昨天的天气真不错，很适合散步",
    "请问周末也开诊吗",
    "我想修改一下个人资料的手机号",
]

PARAPHRASE_INSTRUCTION = """请把下面的句子改写成表达同样意思、但措辞更口语自然的中文医疗咨询句子。

要求：
1. 必须保留原句中的所有医疗名词，一字不差（如疾病名、症状名、药名、检查名、科室名）
2. 不要引入新的疾病、症状、药品、检查或科室名称
3. 长度与原句相近，只输出改写后的句子，不要解释

原句：{sentence}"""


def make_sentence(rng: random.Random) -> Tuple[str, Dict[str, List[str]]]:
    """随机模板填充 → (句子, 标签)。标签为构造时已知的真实实体。"""
    template, slots = SENTENCE_TEMPLATES[rng.randrange(len(SENTENCE_TEMPLATES))]
    from kg_seed import DEPARTMENTS, DISEASES, DRUGS, EXAMINATIONS, SYMPTOMS

    pools = {
        "d": [d for d, *_ in DISEASES],
        "s": [s for s, *_ in SYMPTOMS],
        "m": [m for m, *_ in DRUGS],
        "e": [e for e, *_ in EXAMINATIONS],
        "p": [p for p, *_ in DEPARTMENTS],
    }
    labels: Dict[str, List[str]] = {k: [] for k in NER_KEYS}
    used = set()
    kwargs = {}
    for slot in slots:
        kind, idx = slot[:-1], slot[-1]
        entity = rng.choice(pools[kind])
        while entity in used:  # 避免同槽位重复实体（如 medication 和 medication2）
            entity = rng.choice(pools[kind])
        used.add(entity)
        kwargs[slot] = entity
        key = {"d": "diseases", "s": "symptoms", "m": "drugs", "e": "examinations", "p": "departments"}[kind]
        if entity not in labels[key]:
            labels[key].append(entity)
    return template.format(**kwargs), labels


def empty_labels() -> Dict[str, List[str]]:
    return {k: [] for k in NER_KEYS}


def labels_json(labels: Dict[str, List[str]]) -> str:
    return json.dumps(labels, ensure_ascii=False, indent=2)


def all_planted_present(sentence: str, labels: Dict[str, List[str]]) -> bool:
    """改写守卫：所有植入实体必须原样出现在改写句中。"""
    return all(entity in sentence for values in labels.values() for entity in values)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=800, help="样本总数")
    parser.add_argument("--paraphrase-ratio", type=float, default=0.5, help="教师改写比例")
    parser.add_argument("--no-entity-ratio", type=float, default=0.08, help="无实体样本比例")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    n = 30 if args.dry_run else args.n
    out_dir = DATA_DIR / ("samples" if args.dry_run else ".")
    out_path = out_dir / "sft_ner.jsonl"
    ensure_dirs()
    rng = random.Random(args.seed)

    rows, sentences, label_list = [], [], []
    n_no_entity = int(n * args.no_entity_ratio)
    n_para = int((n - n_no_entity) * args.paraphrase_ratio)

    # 断点续跑：跳过已完成的句子（id = 原始句子）
    done = set() if args.dry_run else load_done_ids(out_path)
    if done:
        print(f"断点续跑：已有 {len(done)} 条，自动跳过")

    # 1) 程序化构造句子与标签（零标注成本，事实即标签）
    seen = set(done)
    while len(sentences) < n - n_no_entity:
        sentence, labels = make_sentence(rng)
        if sentence in seen:
            continue
        seen.add(sentence)
        sentences.append(sentence)
        label_list.append(labels)

    # 2) 无实体样本（同样跳过已完成）
    no_entity = [s for s in NO_ENTITY_SENTENCES if s not in done]
    while len(no_entity) < n_no_entity:
        no_entity.append(rng.choice(NO_ENTITY_SENTENCES))
    no_entity = no_entity[:n_no_entity]

    # 3) 教师改写（只改句子，不改标签；改写失败回退原句）
    para_idx = list(range(len(sentences)))[:n_para]
    client = None
    if para_idx:
        client = LLMClient(model=args.model, base_url=args.base_url, api_key=args.api_key,
                           max_workers=args.workers)
        print(f"教师模型改写 {len(para_idx)} 句 ...")
        reqs = [{"user": PARAPHRASE_INSTRUCTION.format(sentence=sentences[i]), "temperature": 0.8, "max_tokens": 300}
                for i in para_idx]
        outs = client.chat_many(reqs, desc="改写")
        for i, out in zip(para_idx, outs):
            if out:
                new_sentence = normalize_output(out).strip().strip('"')
                if all_planted_present(new_sentence, label_list[i]):
                    sentences[i] = new_sentence

    # 4) 组装：user = 线上 NER_USER 原模板，assistant = 契约 JSON
    for sentence, labels in zip(sentences, label_list):
        rows.append(conversation("ner", NER_SYSTEM,
                                 [(NER_USER_TEMPLATE.format(query=sentence), labels_json(labels))],
                                 id=sentence))
    for sentence in no_entity:
        rows.append(conversation("ner", NER_SYSTEM,
                                 [(NER_USER_TEMPLATE.format(query=sentence), labels_json(empty_labels()))],
                                 id=sentence))

    rng.shuffle(rows)
    total = merge_jsonl(out_path, rows)
    print(f"完成：本轮 {len(rows)} 条，累计 {total} 条 → {out_path}（其中改写 {n_para} 条、无实体 {n_no_entity} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
