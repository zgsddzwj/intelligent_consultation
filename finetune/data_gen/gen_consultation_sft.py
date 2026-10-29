"""问诊对话 SFT 数据生成（蒸馏 DeepSeek-V3，事实锚定项目 KG 与指南）。

流程：
1. 用意图模板填充生成问句池（与线上用户问法同分布）
2. 按实体命中构建 KG/指南上下文（模拟线上 RAG 拼接，与 consultation.py 的 user 模板一致）
3. 用项目原始 system prompt + DeepSeek-V3 生成规范回答（[来源] 标注/免责声明/风险提示）
4. 来源标注缺失的样本走一次修复重试（要求补 [来源N] 标注），修复失败才丢弃
5. 无上下文样本放宽来源要求（保留免责声明即可），教会在无检索结果时的得体应答
6. 多轮样本由教师一次生成完整对话 JSON，控制成本
"""
import argparse
import random
import sys
from typing import Dict, List, Optional, Tuple

from common import (
    DATA_DIR,
    build_context,
    build_question_pool,
    conversation,
    ensure_dirs,
    load_done_ids,
    merge_jsonl,
    write_jsonl,
)
from kg_seed import DISCLAIMER, SYSTEM_PROMPTS
from llm_client import LLMClient, extract_json, normalize_output

MULTI_TURN_INSTRUCTION = """你是医疗问诊对话数据构造助手。下面给出一份参考资料、一位患者的首问和该场景应遵循的医生助手人设。请构造一段自然的中文问诊对话，要求：

1. 对话共 {n_turns}轮：患者先问首问，之后每轮提出自然的追问（症状细节、检查、用药、生活管理、复诊等方向），不要重复首问
2. 医生每轮回答必须严格基于【参考资料】，资料中没有的信息要明确说"暂无明确指南支持"，禁止编造
3. 医生回答中引用参考资料的地方需要标注来源，格式如 [来源1]、[来源2]（对应参考资料中的知识条目）
4. 医生每轮回答不超过300字，专业但易懂
5. 对话最后一位医生的回答结尾必须加免责声明："{disclaimer}"
6. 严格输出JSON，格式如下，不要输出其他任何文字：
{{"turns": [{{"user": "患者发言", "assistant": "医生回答"}}, ...]}}

【医生助手人设】
{system_prompt}

【参考资料】
{context}

【患者首问】
{question}"""

SINGLE_REPAIR_INSTRUCTION = """请修改下面的医疗回答：在对应医学事实的句子后面补充 [来源1]、[来源2] 格式的来源标注（编号对应参考资料中的知识条目）。

要求：
1. 保持全部医学内容、建议和免责声明不变，不要新增医学事实
2. 不要改变回答结构，只补充来源标注
3. 直接输出修改后的完整回答，不要解释

【参考资料】
{context}

【原回答】
{answer}"""

MULTI_REPAIR_INSTRUCTION = """请修改下面的问诊对话JSON：在医生回答中对应医学事实的句子后补充 [来源1]、[来源2] 格式的来源标注。

要求：
1. 保持对话内容、轮次结构和免责声明不变，不要新增医学事实
2. 尽量让每一位医生的回答都带有来源标注
3. 严格输出JSON，格式：{{"turns": [{{"user": "患者发言", "assistant": "医生回答"}}, ...]}}，不要输出其他文字

【对话JSON】
{dialogue}"""


def build_single_turn_requests(items: List[Dict]) -> List[Dict]:
    """单轮样本：复刻 /chat/stream 的医疗咨询 Prompt 契约。

    流式接口无论规则意图如何，均使用 MEDICAL_CONSULTATION_SYSTEM 和
    format_medical_prompt。意图只用于覆盖问句分布，不能改变训练的消息形态。
    """
    requests = []
    spec = SYSTEM_PROMPTS["medical"]
    for it in items:
        # 线上 format_medical_prompt 在无检索结果时也会保留相同模板，仅 context 为空。
        user = spec["user_with_context"].format(
            context=it["context"], question=it["question"]
        )
        requests.append({
            "system": spec["system"],
            "user": user,
            "temperature": 0.7,
            "max_tokens": 1300,
            "_meta": {"question": it["question"], "intent": it["intent"], "spec": spec,
                      "user": user, "context": it["context"]},
        })
    return requests


def build_multi_turn_requests(items: List[Dict]) -> List[Dict]:
    requests = []
    spec = SYSTEM_PROMPTS["medical"]
    for it in items:
        context = it["context"] or "（无检索结果，回答需明确说明信息不足）"
        user = MULTI_TURN_INSTRUCTION.format(
            n_turns=3,
            disclaimer=DISCLAIMER,
            system_prompt=spec["system"],
            context=context,
            question=it["question"],
        )
        requests.append({
            "system": None,
            "user": user,
            "temperature": 0.8,
            "max_tokens": 2600,
            "_meta": {"question": it["question"], "intent": it["intent"], "spec": spec,
                      "context": it["context"]},
        })
    return requests


def finalize_single(req: Dict, answer: str) -> Tuple[Optional[Dict], bool]:
    """返回 (样本, 是否需要修复重试)。answer 为空时彻底丢弃。"""
    meta = req["_meta"]
    answer = normalize_output(answer or "")
    if not answer:
        return None, False
    has_context = bool(meta["context"])
    if has_context and "[来源" not in answer:
        return None, True  # 有上下文必须带来源标注，走修复
    if not has_context and "[来源" in answer:
        # 空 RAG 上下文不存在可验证的来源编号，不能把猜测的引用写入训练集。
        return None, False
    if DISCLAIMER not in answer:
        answer = answer.rstrip() + "\n\n" + DISCLAIMER
    row = conversation(
        task="consultation_single",
        system=meta["spec"]["system"],
        turns=[(meta["user"], answer)],
        id=meta["question"],
    )
    return row, False


def finalize_multi(req: Dict, raw: str) -> Tuple[Optional[Dict], bool, Optional[str]]:
    """返回 (样本, 是否需要修复, 修复用的对话JSON原文)。"""
    meta = req["_meta"]
    raw = raw or ""
    data = extract_json(raw if raw.strip().startswith("{") else normalize_output(raw))
    if not data or not isinstance(data.get("turns"), list):
        return None, False, None
    turns, cited = [], 0
    for t in data["turns"]:
        user, assistant = str(t.get("user", "")).strip(), str(t.get("assistant", "")).strip()
        if not user or not assistant:
            return None, False, None
        cited += "[来源" in assistant
        turns.append((user, assistant))
    if len(turns) < 2:
        return None, False, None
    if cited < max(1, len(turns) // 2):
        return None, True, raw  # 标注不足，走修复
    # 对齐线上多轮形态：只有每轮最新消息带 RAG 上下文，历史消息是裸问题。
    # 训练样本把上下文放进第一轮 user（教师作答时同样可见该上下文），后续轮为裸追问
    if meta["context"]:
        turns[0] = (meta["spec"]["user_with_context"].format(
            context=meta["context"], question=turns[0][0]), turns[0][1])
    user_turns = list(turns)
    if DISCLAIMER not in user_turns[-1][1]:
        user_turns[-1] = (user_turns[-1][0], user_turns[-1][1].rstrip() + "\n\n" + DISCLAIMER)
    row = conversation(
        task="consultation_multi",
        system=meta["spec"]["system"],
        turns=user_turns,
        id=meta["question"],
    )
    return row, False, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-single", type=int, default=1200, help="单轮样本数")
    parser.add_argument("--n-multi", type=int, default=600, help="多轮对话数")
    parser.add_argument("--dry-run", action="store_true", help="小规模试跑并写入 data/samples/")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=None, help="教师模型（默认取 TEACHER_MODEL 或 backend/.env 的 SILICONFLOW_MODEL）")
    parser.add_argument("--base-url", default=None, help="教师端点（默认取 TEACHER_BASE_URL 或 SILICONFLOW_BASE_URL）")
    parser.add_argument("--api-key", default=None, help="教师 Key（默认取 TEACHER_API_KEY 或 SILICONFLOW_API_KEY）")
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    n_single, n_multi = (20, 10) if args.dry_run else (args.n_single, args.n_multi)
    out_dir = DATA_DIR / ("samples" if args.dry_run else ".")
    single_path = out_dir / "sft_consultation_single.jsonl"
    multi_path = out_dir / "sft_consultation_multi.jsonl"
    ensure_dirs()
    rng = random.Random(args.seed)

    pool = build_question_pool(rng)
    print(f"问句池：{len(pool)} 条去重问句")

    # 断点续跑：跳过已完成样本
    done_single = set() if args.dry_run else load_done_ids(single_path)
    done_multi = set() if args.dry_run else load_done_ids(multi_path)
    if done_single or done_multi:
        print(f"断点续跑：已有单轮 {len(done_single)} 条、多轮 {len(done_multi)} 组，自动跳过")

    # ---- 单轮：10% 走无上下文场景 ----
    # n_* 表示目标总量而不是本次增量；中断后重跑只补齐缺口，避免额外 API 花费。
    remaining_single = max(0, n_single - len(done_single))
    single_items = [it for it in pool if it["question"] not in done_single][:remaining_single]
    no_ctx_n = 2 if args.dry_run else max(1, int(n_single * 0.1))
    for i, it in enumerate(single_items):
        it["context"] = "" if i < no_ctx_n else build_context(it["question"])

    # ---- 多轮：必须有 KG 上下文锚定（防止教师在空资料上编造引用），
    #      偏好可追问的任务（诊断/用药/健康管理）----
    prefer = [it for it in pool if it["intent"] in ("diagnosis", "medication", "health_management")]
    candidates = prefer + [it for it in pool if it not in prefer]
    multi_items = []
    remaining_multi = max(0, n_multi - len(done_multi))
    for it in candidates:
        if len(multi_items) >= remaining_multi:
            break
        if it["question"] in done_multi:
            continue
        ctx = build_context(it["question"])
        if ctx:
            it["context"] = ctx
            multi_items.append(it)
    if len(multi_items) < remaining_multi:
        print(f"  [警告] 有 KG 上下文的问句不足：{len(multi_items)}/{remaining_multi}，按实际数量生成")

    if not single_items and not multi_items:
        print("目标样本已齐全，无需调用教师模型。")
        return 0

    client = LLMClient(model=args.model, base_url=args.base_url, api_key=args.api_key,
                       max_workers=args.workers)
    print(f"教师模型：{client.model} @ {client.base_url}")

    # ================ 单轮 ================
    print(f"[1/2] 生成单轮样本 {len(single_items)} 条 ...")
    reqs = build_single_turn_requests(single_items)
    answers = client.chat_many(reqs, desc="单轮")
    single_rows, repair_jobs = [], []  # repair_jobs: [(req, 原回答)]
    for req, ans in zip(reqs, answers):
        row, need_repair = finalize_single(req, ans or "")
        if row:
            single_rows.append(row)
        elif need_repair:
            repair_jobs.append((req, normalize_output(ans)))
    if repair_jobs:
        print(f"  修复重试 {len(repair_jobs)} 条（补来源标注）...")
        repairs = client.chat_many([
            {"user": SINGLE_REPAIR_INSTRUCTION.format(
                context=req["_meta"]["context"] or "（无参考资料）", answer=original),
             "temperature": 0.3, "max_tokens": 1300}
            for req, original in repair_jobs
        ], desc="单轮修复")
        for (req, _), rep in zip(repair_jobs, repairs):
            if not rep:
                continue
            rep = normalize_output(rep)
            if "[来源" not in rep:
                continue
            if DISCLAIMER not in rep:
                rep = rep.rstrip() + "\n\n" + DISCLAIMER
            single_rows.append(conversation(
                task="consultation_single",
                system=req["_meta"]["spec"]["system"],
                turns=[(req["_meta"]["user"], rep)],
                id=req["_meta"]["question"],
            ))

    # ================ 多轮 ================
    print(f"[2/2] 生成多轮对话 {len(multi_items)} 组 ...")
    reqs_m = build_multi_turn_requests(multi_items)
    answers_m = client.chat_many(reqs_m, desc="多轮")
    multi_rows, m_repair_jobs = [], []  # m_repair_jobs: [(req, 对话JSON原文)]
    for req, ans in zip(reqs_m, answers_m):
        row, need_repair, raw = finalize_multi(req, ans or "")
        if row:
            multi_rows.append(row)
        elif need_repair and raw:
            m_repair_jobs.append((req, raw))
    if m_repair_jobs:
        print(f"  修复重试 {len(m_repair_jobs)} 组（补来源标注）...")
        repairs = client.chat_many([
            {"user": MULTI_REPAIR_INSTRUCTION.format(dialogue=raw),
             "temperature": 0.2, "max_tokens": 2600}
            for _, raw in m_repair_jobs
        ], desc="多轮修复")
        for (req, _), rep in zip(m_repair_jobs, repairs):
            row, _, _ = finalize_multi(req, rep or "")
            if row:
                multi_rows.append(row)

    total_single = merge_jsonl(single_path, single_rows)
    total_multi = merge_jsonl(multi_path, multi_rows)
    print(f"完成：本轮单轮 {len(single_rows)} 条，累计 {total_single} 条 → {single_path}")
    print(f"完成：本轮多轮 {len(multi_rows)} 组，累计 {total_multi} 组 → {multi_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
