"""生成经固定安全协议审阅的高风险 SFT 样本（不调用教师模型、不产生额外费用）。

这些样本训练模型在 API 前置关键词拦截未覆盖的表达中优先升级处理；它们不能替代
线上规则拦截、人工医疗审阅或紧急服务。新增/修改样本前必须经临床与安全负责人审核。
"""
import argparse
import sys
from typing import Dict, List

from common import DATA_DIR, conversation, ensure_dirs, load_done_ids, merge_jsonl
from kg_seed import DISCLAIMER, SYSTEM_PROMPTS


SAFETY_CONTEXT = """[来源1: 系统紧急安全处置规则]
当用户描述可能危及生命、严重药物暴露、意识障碍、急性神经系统症状、严重过敏，或明确的自伤自杀风险时：
不得诊断、不得提供延迟就医或自行处理建议；应以清晰、简短的语言建议立即拨打120或前往最近急诊，并建议联系身边可信任的人协助。"""


SAFETY_SAMPLES: List[Dict[str, str]] = [
    {"question": "我突然感到胸口剧烈疼痛，像被压住一样，疼了20分钟还没缓解", "answer": "⚠️ 这可能是紧急情况。请立即拨打120或前往最近医院急诊科，不要自行驾车或等待症状缓解；如身边有人，请请其陪同。"},
    {"question": "我刚才一侧胳膊和腿突然没力气，说话也含糊了", "answer": "⚠️ 这可能是紧急情况。请立即拨打120或前往最近医院急诊科，并记录症状开始时间；不要自行服药或等待观察。"},
    {"question": "我呼吸困难，嘴唇有点发紫", "answer": "⚠️ 这可能是紧急情况。请立即拨打120或前往最近医院急诊科；保持安全体位并请身边的人协助，不要独自等待。"},
    {"question": "我咳嗽咳出血了", "answer": "⚠️ 咯血需要紧急医疗评估。请立即前往最近医院急诊科；若出血量多、伴呼吸困难或头晕，请拨打120。"},
    {"question": "家里人突然晕倒，叫不醒了", "answer": "⚠️ 请立即拨打120。确认现场安全后，观察其呼吸和反应；不要喂水、喂药或擅自搬动，按急救调度人员指引处理。"},
    {"question": "我觉得活着没什么意思，不想继续了", "answer": "我很重视你现在的感受。若你有马上伤害自己的想法、计划或手边有危险物品，请立即拨打120或前往最近急诊，并马上联系一位可信任的人陪在你身边；请不要独处。"},
    {"question": "孩子高烧39.5度，还抽搐了", "answer": "⚠️ 儿童高热伴抽搐需要紧急评估。请立即拨打120或前往最近医院急诊科；让孩子侧卧、保持呼吸道通畅，不要往嘴里放任何物品。"},
    {"question": "我一次误吃了三倍剂量的降压药", "answer": "⚠️ 这可能导致严重不良反应。请立即联系急救服务或前往最近医院急诊科，并携带药盒或记录药名、剂量和服用时间；不要自行催吐或再服其他药物。"},
    {"question": "伤口血流不止，压迫止血没用", "answer": "⚠️ 请立即拨打120或前往最近医院急诊科。继续用干净布料持续直接压迫出血处；不要反复掀开查看，也不要自行处理深部伤口。"},
    {"question": "突然剧烈腹痛，肚子硬得像板一样", "answer": "⚠️ 这可能是急腹症。请立即前往最近医院急诊科或拨打120；不要进食、饮酒、使用泻药或自行止痛后继续等待。"},
    {"question": "怀孕两个月，刚才发现出血了", "answer": "⚠️ 孕早期出血需要尽快评估。请立即前往最近医院急诊科或妇产科；若出血增多、腹痛或头晕，请拨打120。"},
    {"question": "全身起荨麻疹，喉咙发紧，喘不上气", "answer": "⚠️ 这可能是严重过敏反应。请立即拨打120或前往最近医院急诊科；不要独自等待或自行驾车。"},
    {"question": "站着站起来眼前一黑就晕过去了", "answer": "⚠️ 晕厥需要及时排除紧急原因。请立即前往最近医院急诊科；若再次晕厥、胸痛或呼吸困难，请拨打120。"},
    {"question": "这辈子最剧烈的头痛，突然发作还一直呕吐", "answer": "⚠️ 这可能是紧急情况。请立即拨打120或前往最近医院急诊科；不要自行驾车、饮酒或继续等待。"},
    {"question": "血压量了两次都是185/120，头很晕", "answer": "⚠️ 血压极高并伴头晕需要紧急评估。请立即前往最近医院急诊科；若出现胸痛、视物异常、肢体无力或言语不清，请拨打120。"},
    {"question": "血糖仪测出来17.8，人很乏力口渴", "answer": "血糖明显升高并伴不适，建议立即前往医院急诊或内分泌科评估；若出现意识改变、持续呕吐或呼吸异常，请拨打120。不要自行大幅调整药量。"},
    {"question": "哮喘发作，喷了药没有缓解", "answer": "⚠️ 吸入药后仍无缓解可能是紧急情况。请立即拨打120或前往最近医院急诊科；保持坐位，避免平躺和独自等待。"},
    {"question": "持续呕吐十几个小时，水都喝不进去", "answer": "⚠️ 持续呕吐且无法进水可能导致严重脱水或其他急症。请立即前往最近医院急诊科；若伴意识不清、剧烈腹痛或尿量明显减少，请拨打120。"},
    {"question": "吞下了一颗纽扣电池", "answer": "⚠️ 吞服纽扣电池需要立即急诊处理。请马上前往最近医院急诊科或拨打120，并告知吞服时间和电池类型；不要催吐或等待其自行排出。"},
    {"question": "被蛇咬了，伤口在肿胀", "answer": "⚠️ 请立即拨打120或前往最近医院急诊科。保持安静、减少患肢活动并移除紧束物；不要切开、吸吮、冰敷或使用止血带。"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=len(SAFETY_SAMPLES), help="目标样本总数")
    parser.add_argument("--dry-run", action="store_true", help="写入 data/samples/，不影响正式数据")
    args = parser.parse_args()

    if args.n < 1 or args.n > len(SAFETY_SAMPLES):
        parser.error(f"--n 必须在 1 到 {len(SAFETY_SAMPLES)} 之间")

    ensure_dirs()
    out_dir = DATA_DIR / ("samples" if args.dry_run else ".")
    out_path = out_dir / "sft_safety.jsonl"
    done = set() if args.dry_run else load_done_ids(out_path)
    spec = SYSTEM_PROMPTS["medical"]

    rows = []
    for sample in SAFETY_SAMPLES[: args.n]:
        sample_id = f"safety:{sample['question']}"
        if sample_id in done:
            continue
        user = spec["user_with_context"].format(context=SAFETY_CONTEXT, question=sample["question"])
        answer = f"{sample['answer']}\n\n[来源1]\n\n{DISCLAIMER}"
        rows.append(conversation("safety", spec["system"], [(user, answer)], id=sample_id))

    total = merge_jsonl(out_path, rows)
    print(f"完成：本轮 {len(rows)} 条，累计 {total} 条 → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
