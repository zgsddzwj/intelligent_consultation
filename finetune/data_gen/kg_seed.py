"""项目知识资产的结构化副本 —— 微调数据生成的事实锚点。

数据从以下项目源文件原样复制（若项目更新，请同步修改本文件）：
- backend/scripts/setup/init_knowledge_graph.py   知识图谱种子：科室/疾病/症状/药品/检查/关系
- backend/scripts/data/load_sample_data.py        两篇诊疗指南全文
- backend/scripts/ml/train_ml_models.py           意图模板库与医疗关键词词表
- backend/app/prompts/consultation.py             线上问诊 system/user prompt
- backend/app/prompts/knowledge.py                NER 输出契约

关键设计：SYSTEM_PROMPTS 中的 prompt 原文与线上完全一致，保证微调后模型
接回项目时（llm_service 拼接同样的 system prompt）训练分布 = 推理分布。
"""
import os
import re
from typing import Dict, List, Tuple

# ================================================================
# 知识图谱种子数据（来自 init_knowledge_graph.py）
# ================================================================

# (名称, 描述, 覆盖范围)
DEPARTMENTS: List[Tuple[str, str, str]] = [
    ("心内科", "心血管疾病诊疗", "高血压、冠心病、心律失常等"),
    ("内分泌科", "内分泌代谢疾病诊疗", "糖尿病、甲状腺疾病等"),
    ("传染科", "传染病诊疗", "乙肝、流感、肺炎等传染病"),
    ("神经内科", "神经系统疾病诊疗", "神经衰弱、植物神经紊乱、癫痫等"),
    ("肾内科", "肾脏疾病诊疗", "肾衰竭、尿毒症、肾炎等"),
    ("消化内科", "消化系统疾病诊疗", "胃炎、胃溃疡、肠炎等"),
    ("呼吸内科", "呼吸系统疾病诊疗", "哮喘、肺炎、支气管炎等"),
    ("肿瘤科", "肿瘤疾病诊疗", "各种良恶性肿瘤"),
    ("皮肤科", "皮肤疾病诊疗", "皮肤病、皮肤瘙痒等"),
    ("眼科", "眼部疾病诊疗", "红眼病、麦粒肿等"),
    ("耳鼻喉科", "耳鼻喉疾病诊疗", "鼻炎、咽炎等"),
    ("口腔科", "口腔疾病诊疗", "口腔疾病、鹅口疮等"),
    ("泌尿外科", "泌尿系统疾病诊疗", "尿道炎、阳痿等"),
    ("男科", "男性疾病诊疗", "阳痿、性功能障碍等"),
    ("产科", "产科疾病诊疗", "流产、早孕反应等"),
]

# (名称, ICD-10, 描述, 病因)
DISEASES: List[Tuple[str, str, str, str]] = [
    ("高血压", "I10", "高血压是一种常见的慢性疾病，以动脉血压持续升高为主要特征。", "原发性高血压病因不明，可能与遗传、环境因素有关。"),
    ("糖尿病", "E11", "糖尿病是一组以高血糖为特征的代谢性疾病。", "胰岛素分泌缺陷或其生物作用受损，或两者兼有引起。"),
    ("乙肝", "B16", "乙型病毒性肝炎，由乙型肝炎病毒引起的肝脏疾病。", "乙型肝炎病毒感染"),
    ("流感", "J11", "流行性感冒，由流感病毒引起的急性呼吸道传染病。", "流感病毒感染"),
    ("神经衰弱", "F48.0", "神经衰弱是一种神经症，主要表现为易疲劳、注意力不集中等。", "长期精神紧张、压力过大"),
    ("植物神经紊乱", "G90", "植物神经功能紊乱，自主神经系统功能失调。", "精神压力、内分泌失调等"),
    ("肾衰竭", "N18", "肾功能衰竭，肾脏功能严重受损。", "多种原因导致肾功能下降"),
    ("尿毒症", "N18.9", "尿毒症是慢性肾衰竭的终末期表现。", "慢性肾衰竭进展"),
    ("哮喘", "J45", "支气管哮喘，慢性气道炎症性疾病。", "遗传、环境因素等"),
    ("肺炎", "J18", "肺部感染性疾病。", "细菌、病毒等病原体感染"),
    ("肝硬化", "K74", "肝脏慢性进行性病变。", "病毒性肝炎、酒精性肝病等"),
    ("肝性脑病", "K72", "严重肝病引起的神经精神综合征。", "肝功能严重受损"),
    ("腹膜炎", "K65", "腹膜炎症性疾病。", "细菌感染、化学刺激等"),
]

# (名称, 严重程度, 描述)
SYMPTOMS: List[Tuple[str, str, str]] = [
    ("头痛", "中等", "头部疼痛，可能由多种原因引起。"),
    ("头晕", "中等", "感觉头部眩晕或失去平衡。"),
    ("多饮", "低", "异常口渴，饮水量明显增加。"),
    ("转氨酶增高", "中等", "肝功能异常指标。"),
    ("浑身酸痛", "中等", "全身肌肉酸痛不适。"),
    ("怕冷", "低", "异常怕冷，体温调节异常。"),
    ("咽喉疼痛", "中等", "咽喉部疼痛不适。"),
    ("黄疸", "高", "皮肤、黏膜黄染。"),
    ("胸腔积液", "高", "胸腔内液体积聚。"),
    ("易疲乏", "中等", "容易疲劳，精力不足。"),
    ("神经衰弱", "中等", "神经功能衰弱表现。"),
    ("易激惹", "中等", "情绪易激动、易怒。"),
    ("阳痿", "中等", "男性勃起功能障碍。"),
    ("月经不调", "中等", "月经周期或量异常。"),
    ("便秘", "低", "排便困难或次数减少。"),
    ("下腹疼痛", "中等", "下腹部疼痛不适。"),
    ("皮肤瘙痒", "中等", "皮肤瘙痒不适。"),
    ("干咳", "中等", "无痰或少痰的咳嗽。"),
]

# (名称, 通用名, 剂型, 适应症, 禁忌)
DRUGS: List[Tuple[str, str, str, str, str]] = [
    ("硝苯地平", "Nifedipine", "片剂", "用于治疗高血压、心绞痛", "对本品过敏者禁用"),
    ("二甲双胍", "Metformin", "片剂", "用于2型糖尿病的治疗", "严重肾功能不全者禁用"),
    ("恩替卡韦分散片", "Entecavir", "片剂", "用于慢性乙型肝炎的治疗", "对本品过敏者禁用"),
    ("注射用盐酸精氨", "Arginine Hydrochloride", "注射剂", "用于肝性脑病的治疗", "严重肾功能不全者禁用"),
    ("碧云砂乙肝颗粒", "Biyunsha", "颗粒剂", "用于乙肝的辅助治疗", "对本品过敏者禁用"),
    ("复方感冒灵颗粒", "Compound Cold Granules", "颗粒剂", "用于感冒、流感的治疗", "对本品过敏者禁用"),
    ("金感胶囊", "Jinggan Capsule", "胶囊", "用于感冒、流感的治疗", "对本品过敏者禁用"),
    ("泻肝安神丸", "Xiegan Anshen Pills", "丸剂", "用于神经衰弱的治疗", "对本品过敏者禁用"),
    ("天麻胶囊", "Gastrodia Elata Capsules", "胶囊", "用于神经衰弱的治疗", "对本品过敏者禁用"),
    ("益脑胶囊", "Yinao Capsule", "胶囊", "用于神经衰弱的治疗", "对本品过敏者禁用"),
]

# (名称, 类型, 参考范围, 描述)
EXAMINATIONS: List[Tuple[str, str, str, str]] = [
    ("血压测量", "生命体征", "正常值: 收缩压<120mmHg, 舒张压<80mmHg", "测量动脉血压"),
    ("血糖检测", "实验室检查", "空腹血糖: 3.9-6.1mmol/L", "检测血液中葡萄糖含量"),
    ("乙肝表面抗原检测", "实验室检查", "阴性", "检测乙肝病毒感染"),
    ("肝功能检查", "实验室检查", "转氨酶正常范围", "检测肝功能指标"),
    ("血常规", "实验室检查", "各项指标正常范围", "检测血液成分"),
]

# (源类型, 源名称, 关系, 目标类型, 目标名称, 属性)
RELATIONSHIPS: List[Tuple[str, str, str, str, str, Dict]] = [
    # 疾病-症状关系
    ("Disease", "高血压", "HAS_SYMPTOM", "Symptom", "头痛", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "高血压", "HAS_SYMPTOM", "Symptom", "头晕", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "糖尿病", "HAS_SYMPTOM", "Symptom", "多饮", {"frequency": "常见", "severity": "低"}),
    ("Disease", "乙肝", "HAS_SYMPTOM", "Symptom", "转氨酶增高", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "乙肝", "HAS_SYMPTOM", "Symptom", "黄疸", {"frequency": "常见", "severity": "高"}),
    ("Disease", "流感", "HAS_SYMPTOM", "Symptom", "浑身酸痛", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "流感", "HAS_SYMPTOM", "Symptom", "怕冷", {"frequency": "常见", "severity": "低"}),
    ("Disease", "流感", "HAS_SYMPTOM", "Symptom", "咽喉疼痛", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "神经衰弱", "HAS_SYMPTOM", "Symptom", "易疲乏", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "神经衰弱", "HAS_SYMPTOM", "Symptom", "易激惹", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "植物神经紊乱", "HAS_SYMPTOM", "Symptom", "易疲乏", {"frequency": "常见", "severity": "中等"}),
    ("Disease", "植物神经紊乱", "HAS_SYMPTOM", "Symptom", "阳痿", {"frequency": "常见", "severity": "中等"}),
    # 疾病-并发症关系
    ("Disease", "乙肝", "HAS_SYMPTOM", "Disease", "肝硬化", {"frequency": "常见", "severity": "高"}),
    ("Disease", "乙肝", "HAS_SYMPTOM", "Disease", "肝性脑病", {"frequency": "少见", "severity": "高"}),
    ("Disease", "乙肝", "HAS_SYMPTOM", "Disease", "腹膜炎", {"frequency": "少见", "severity": "高"}),
    ("Disease", "流感", "HAS_SYMPTOM", "Disease", "肺炎", {"frequency": "常见", "severity": "高"}),
    ("Disease", "流感", "HAS_SYMPTOM", "Symptom", "胸腔积液", {"frequency": "少见", "severity": "高"}),
    ("Disease", "神经衰弱", "HAS_SYMPTOM", "Symptom", "易激惹", {"frequency": "常见", "severity": "中等"}),
    # 疾病-药物关系
    ("Disease", "高血压", "TREATED_BY", "Drug", "硝苯地平", {"effectiveness": "高", "dosage": "10-20mg, 每日2-3次"}),
    ("Disease", "糖尿病", "TREATED_BY", "Drug", "二甲双胍", {"effectiveness": "高", "dosage": "500-2000mg, 每日2-3次"}),
    ("Disease", "肝硬化", "TREATED_BY", "Drug", "恩替卡韦分散片", {"effectiveness": "高", "dosage": "0.5mg, 每日1次"}),
    ("Disease", "肝性脑病", "TREATED_BY", "Drug", "注射用盐酸精氨", {"effectiveness": "中", "dosage": "遵医嘱"}),
    ("Disease", "乙肝", "TREATED_BY", "Drug", "碧云砂乙肝颗粒", {"effectiveness": "中", "dosage": "遵医嘱"}),
    ("Disease", "流感", "TREATED_BY", "Drug", "复方感冒灵颗粒", {"effectiveness": "中", "dosage": "遵医嘱"}),
    ("Disease", "流感", "TREATED_BY", "Drug", "金感胶囊", {"effectiveness": "中", "dosage": "遵医嘱"}),
    ("Disease", "神经衰弱", "TREATED_BY", "Drug", "泻肝安神丸", {"effectiveness": "中", "dosage": "遵医嘱"}),
    ("Disease", "神经衰弱", "TREATED_BY", "Drug", "天麻胶囊", {"effectiveness": "中", "dosage": "遵医嘱"}),
    ("Disease", "神经衰弱", "TREATED_BY", "Drug", "益脑胶囊", {"effectiveness": "中", "dosage": "遵医嘱"}),
    # 疾病-检查关系
    ("Disease", "高血压", "REQUIRES_EXAM", "Examination", "血压测量", {"necessity": "必需", "priority": "高"}),
    ("Disease", "糖尿病", "REQUIRES_EXAM", "Examination", "血糖检测", {"necessity": "必需", "priority": "高"}),
    ("Disease", "乙肝", "REQUIRES_EXAM", "Examination", "乙肝表面抗原检测", {"necessity": "必需", "priority": "高"}),
    ("Disease", "乙肝", "REQUIRES_EXAM", "Examination", "肝功能检查", {"necessity": "必需", "priority": "高"}),
    # 症状-科室关系
    ("Symptom", "头痛", "BELONGS_TO", "Department", "心内科", {}),
    ("Symptom", "头晕", "BELONGS_TO", "Department", "心内科", {}),
    ("Symptom", "多饮", "BELONGS_TO", "Department", "内分泌科", {}),
    ("Symptom", "转氨酶增高", "BELONGS_TO", "Department", "传染科", {}),
    ("Symptom", "黄疸", "BELONGS_TO", "Department", "传染科", {}),
    ("Symptom", "浑身酸痛", "BELONGS_TO", "Department", "传染科", {}),
    ("Symptom", "易疲乏", "BELONGS_TO", "Department", "神经内科", {}),
    ("Symptom", "易激惹", "BELONGS_TO", "Department", "神经内科", {}),
    ("Symptom", "阳痿", "BELONGS_TO", "Department", "男科", {}),
    ("Symptom", "阳痿", "BELONGS_TO", "Department", "泌尿外科", {}),
    ("Symptom", "皮肤瘙痒", "BELONGS_TO", "Department", "皮肤科", {}),
    ("Symptom", "干咳", "BELONGS_TO", "Department", "呼吸内科", {}),
]

# ================================================================
# 诊疗指南全文（来自 load_sample_data.py）
# ================================================================

GUIDELINES: Dict[str, str] = {
    "高血压诊疗指南.txt": """高血压诊疗指南

一、定义
高血压是指收缩压≥140mmHg和/或舒张压≥90mmHg。

二、诊断标准
1. 在未使用降压药物的情况下，非同日3次测量诊室血压，收缩压≥140mmHg和/或舒张压≥90mmHg。
2. 患者既往有高血压史，目前正在使用降压药物，血压虽然低于140/90mmHg，仍应诊断为高血压。

三、治疗原则
1. 生活方式干预：低盐饮食、适量运动、控制体重、戒烟限酒。
2. 药物治疗：根据患者情况选择合适的降压药物，如ACEI、ARB、CCB等。
3. 目标血压：一般患者<140/90mmHg，合并糖尿病或慢性肾脏病患者<130/80mmHg。

四、常用药物
1. 钙通道阻滞剂（CCB）：如硝苯地平、氨氯地平等。
2. 血管紧张素转换酶抑制剂（ACEI）：如卡托普利、依那普利等。
3. 血管紧张素II受体拮抗剂（ARB）：如氯沙坦、缬沙坦等。

五、注意事项
1. 定期监测血压。
2. 遵医嘱服药，不可自行停药。
3. 注意药物不良反应。
4. 定期复查，评估治疗效果。

来源：《中国高血压防治指南2023》""",
    "糖尿病管理指南.txt": """糖尿病管理指南

一、定义
糖尿病是一组以高血糖为特征的代谢性疾病，是由于胰岛素分泌缺陷或其生物作用受损，或两者兼有引起。

二、诊断标准
1. 空腹血糖≥7.0mmol/L。
2. 随机血糖≥11.1mmol/L。
3. 糖化血红蛋白（HbA1c）≥6.5%。

三、治疗目标
1. 血糖控制：空腹血糖4.4-7.0mmol/L，餐后2小时血糖<10.0mmol/L。
2. 糖化血红蛋白：<7.0%。
3. 血压：<130/80mmHg。
4. 血脂：LDL-C<2.6mmol/L。

四、治疗方案
1. 生活方式干预：饮食控制、运动锻炼、体重管理。
2. 药物治疗：
   - 一线药物：二甲双胍
   - 二线药物：磺脲类、DPP-4抑制剂、GLP-1受体激动剂等
   - 胰岛素治疗：适用于1型糖尿病或2型糖尿病血糖控制不佳者

五、监测指标
1. 血糖监测：每日监测空腹和餐后血糖。
2. 糖化血红蛋白：每3个月检测一次。
3. 并发症筛查：定期检查眼底、肾功能、神经病变等。

六、注意事项
1. 严格遵医嘱用药。
2. 注意低血糖反应。
3. 定期复查，调整治疗方案。
4. 预防并发症。

来源：《中国2型糖尿病防治指南2020》""",
}

# ================================================================
# 意图模板与关键词词表（来自 train_ml_models.py，"general"为系统使用类问题，
# 属于客服 Agent 职责，问诊对话生成时排除）
# ================================================================

MEDICAL_KEYWORDS = {
    "symptoms": ["头痛", "头晕", "发热", "咳嗽", "腹痛", "恶心", "呕吐", "胸闷", "气短",
                 "乏力", "失眠", "食欲不振", "体重下降", "水肿", "皮疹"],
    "diseases": ["高血压", "糖尿病", "心脏病", "感冒", "肺炎", "胃炎", "肝炎", "肾炎",
                 "关节炎", "哮喘", "癌症", "中风", "抑郁症", "焦虑症"],
    "medications": ["阿司匹林", "胰岛素", "降压药", "抗生素", "止痛药", "维生素", "中药",
                    "降压片", "降糖药", "消炎药"],
    "examinations": ["血常规", "尿常规", "CT", "MRI", "B超", "心电图", "X光", "胃镜",
                     "肝功能", "肾功能", "血脂", "血糖"],
    "lifestyle": ["饮食", "运动", "睡眠", "戒烟", "限酒", "减压", "作息", "锻炼"],
}

DURATIONS = ["3天", "一周", "半个月", "一个月", "两个月"]

INTENT_TEMPLATES = {
    "diagnosis": [
        "我{symptom}，可能是什么病？",
        "{symptom}已经{duration}了，需要看什么科？",
        "最近总是{symptom}，请问怎么回事？",
        "医生，我{symptom}，这是不是{disease}的症状？",
        "{symptom}严重吗？需要做哪些检查？",
        "我家人{symptom}，应该怎么办？",
        "请问{symptom}可能是什么原因引起的？",
        "持续{symptom}，是否需要立即就医？",
        "儿童{symptom}怎么处理？",
        "老年人{symptom}需要注意什么？",
    ],
    "medication": [
        "{disease}应该吃什么药？",
        "{medication}有什么副作用？",
        "{disease}能吃{medication}吗？",
        "{medication}的用法用量是什么？",
        "吃了{medication}后{symptom}更严重了怎么办？",
        "孕妇可以吃{medication}吗？",
        "{disease}的最佳药物治疗方案是什么？",
        "{medication}和{medication2}能一起吃吗？",
        "{medication}需要吃多久？",
        "{medication}漏服了怎么办？",
    ],
    "examination": [
        "{disease}需要做什么检查？",
        "{examination}检查前需要注意什么？",
        "{examination}多少钱？医保能报销吗？",
        "{examination}结果怎么看？",
        "怀疑{disease}应该先做哪个检查？",
        "{examination}有辐射吗？对身体有害吗？",
        "做{examination}需要空腹吗？",
        "{examination}检查大概多长时间？",
        "{examination}能查出{disease}吗？",
        "哪些人不能做{examination}？",
    ],
    "health_management": [
        "{disease}患者平时要注意什么？",
        "如何通过{lifestyle}改善{disease}？",
        "{disease}的日常护理方法？",
        "得了{disease}还能运动吗？",
        "{disease}患者饮食上有什么禁忌？",
        "如何制定{disease}康复计划？",
        "慢性病患者如何自我管理？",
        "{disease}复诊频率应该是多少？",
        "如何监测{disease}的病情变化？",
        "{disease}患者的心理调节方法？",
    ],
    "symptom_inquiry": [
        "{disease}的早期症状有哪些？",
        "{disease}和{disease2}症状有什么区别？",
        "{symptom}是{disease}的典型表现吗？",
        "{disease}发展到后期会有什么症状？",
        "出现什么症状要警惕{disease}？",
        "{symptom}伴随{symptom2}说明什么？",
        "{disease}的并发症有哪些症状？",
        "如何区分普通{symptom}和{disease}？",
        "{disease}急性发作时有什么症状？",
        "哪些症状表明{disease}在好转？",
    ],
    "disease_info": [
        "什么是{disease}？",
        "{disease}是怎么引起的？",
        "{disease}会传染吗？",
        "{disease}的高发人群是哪些？",
        "{disease}的发病率是多少？",
        "{disease}能治愈吗？",
        "{disease}如果不治疗会怎样？",
        "{disease}的最新治疗方法有哪些？",
        "{disease}和遗传有关系吗？",
        "关于{disease}的常见误区？",
    ],
    "prevention": [
        "如何预防{disease}？",
        "什么人群容易得{disease}？",
        "{disease}的一级预防措施？",
        "日常生活中如何避免{disease}？",
        "{disease}的筛查建议？",
        "疫苗能预防{disease}吗？",
        "{lifestyle}对预防{disease}有帮助吗？",
        "季节性{disease}如何预防？",
        "家族有{disease}史如何预防？",
        "{disease}的高危因素有哪些？",
    ],
    "general": [
        "你好，我想了解一下这个系统",
        "你们医院有哪些科室？",
        "如何使用在线问诊功能？",
        "医生资质怎么样？",
        "咨询费用是多少？",
        "就诊流程是怎样的？",
        "如何查看历史记录？",
        "隐私保护政策是什么？",
        "客服联系方式？",
        "系统使用帮助？",
    ],
}

# ================================================================
# 线上 Prompt 原文（来自 app/prompts/consultation.py —— 与线上保持一致是本方案的关键）
# ================================================================

DISCLAIMER = (
    "【免责声明】本回答由 AI 生成，仅供参考，不能替代专业医生的诊断与治疗建议。"
    "如有不适或紧急情况，请立即就医或拨打急救电话。"
)

SYSTEM_PROMPTS = {
    "medical": {
        "system": """你是一位专业的AI医疗助手。你的职责是：
1. 基于提供的医疗文献和知识图谱信息，为用户提供准确的医疗咨询
2. 所有回答必须标注数据来源，格式：[来源1]、[来源2]等
3. 对于不确定的信息，明确说明"暂无明确指南支持"
4. 禁止编造医疗建议或诊断
5. 对于高风险场景（如紧急病症、手术方案、药物剂量调整），必须提示用户前往医院就诊
6. 使用专业但易懂的语言，避免过度技术化
7. 在回答结尾逐字添加免责声明："【免责声明】本回答由 AI 生成，仅供参考，不能替代专业医生的诊断与治疗建议。如有不适或紧急情况，请立即就医或拨打急救电话。"
""",
        "user_with_context": """基于以下医疗信息，回答用户的问题：

{context}

用户问题：{question}

请提供专业、准确的回答，并标注信息来源。如果信息不足，请明确说明。""",
    },
    "diagnosis": {
        "system": """你是一位专业的诊断辅助AI。基于患者的症状描述和医疗知识，提供可能的诊断建议。

工作原则：
1. 仅提供辅助参考，最终诊断需要医生确认
2. 按可能性从高到低列出可能的疾病方向
3. 建议有助于明确诊断的检查项目
4. 识别需要警惕的危险信号（red flags）
5. 明确建议就医的紧急程度和科室

注意：这仅是辅助参考，最终诊断需要医生确认。""",
        "user_with_context": """基于以下医疗知识和患者症状，提供诊断辅助建议：

参考资料：
{context}

患者症状描述：{question}

请提供可能的诊断方向、建议检查项目，并标注信息来源。
注意：这仅是辅助参考，最终诊断需要医生确认。""",
    },
    "drug": {
        "system": """你是一位专业的用药咨询AI。基于药物信息和知识图谱，回答用药相关问题。

工作原则：
1. 安全优先：任何用药建议必须以安全为首要考虑
2. 提供药物的一般信息、适应症、禁忌症、注意事项
3. 主动提醒药物相互作用和潜在副作用
4. 不提供具体的个体化剂量建议（除非是通用指南中的标准剂量）
5. 强调个体化用药的重要性，建议咨询医生或药师

注意：具体用药方案需要医生根据患者情况制定。""",
        "user_with_context": """基于以下药物信息和医疗知识，回答用户的用药问题：

参考资料：
{context}

用户问题：{question}

请提供专业、准确的用药建议，并标注信息来源。
注意：具体用药方案需要医生根据患者情况制定。""",
    },
    "stream": {
        "system": """你是一位专业的AI医疗助手。基于提供的医疗信息，为用户提供准确的医疗咨询。
所有回答必须标注信息来源，对于不确定的信息明确说明，禁止编造医疗建议。
在回答结尾逐字添加免责声明："【免责声明】本回答由 AI 生成，仅供参考，不能替代专业医生的诊断与治疗建议。如有不适或紧急情况，请立即就医或拨打急救电话。"。""",
        "user_with_context": """基于以下医疗知识：

{context}

用户问题：{question}

请提供专业、准确的回答，并标注信息来源。""",
        "user_no_context": """用户问题：{question}

请提供专业、准确的回答。""",
    },
}

# 意图 → 任务模板映射（general 为客服类，不参与问诊模型训练）
INTENT_TO_TASK = {
    "diagnosis": "diagnosis",
    "medication": "drug",
    "symptom_inquiry": "medical",
    "disease_info": "medical",
    "examination": "medical",
    "health_management": "medical",
    "prevention": "medical",
}

# ================================================================
# NER 契约（来自 app/prompts/knowledge.py）
# ================================================================

NER_SYSTEM = "你是一个专业的医疗实体识别助手，擅长从医疗相关文本中准确提取实体。"

NER_USER_TEMPLATE = """请从以下医疗咨询问题中提取所有医疗相关实体，并按类型分类。

问题：{query}

请以JSON格式返回，格式如下：
{{
    "diseases": ["疾病名称1", "疾病名称2"],
    "symptoms": ["症状名称1", "症状名称2"],
    "drugs": ["药物名称1", "药物名称2"],
    "examinations": ["检查项目1", "检查项目2"],
    "departments": ["科室名称1", "科室名称2"]
}}

要求：
1. 只提取明确提到的实体，不要推测
2. 实体名称要完整准确
3. 如果某个类型没有实体，返回空数组
4. 只返回JSON，不要其他文字

JSON:"""

NER_KEYS = ["diseases", "symptoms", "drugs", "examinations", "departments"]

# ================================================================
# 摘要任务 system prompt（非线上任务，训练用轻量人设）
# ================================================================

SUMMARY_SYSTEM = "你是一名严谨的医疗内容编辑。基于提供的医学指南内容完成任务，忠实原文，不添加指南中没有的信息，不编造医学事实。"


def entity_index() -> Dict[str, Dict]:
    """构建实体名 → {type, record} 索引（含药物通用名，按长度降序便于匹配）。"""
    index: Dict[str, Dict] = {}
    for name, desc, scope in DEPARTMENTS:
        index[name] = {"type": "Department", "record": (name, desc, scope)}
    for name, icd10, desc, etiology in DISEASES:
        index[name] = {"type": "Disease", "record": (name, icd10, desc, etiology)}
    for name, severity, desc in SYMPTOMS:
        index[name] = {"type": "Symptom", "record": (name, severity, desc)}
    for name, generic, form, indication, contraindication in DRUGS:
        index[name] = {"type": "Drug", "record": (name, generic, form, indication, contraindication)}
    for name, type_name, ref_range, desc in EXAMINATIONS:
        index[name] = {"type": "Examination", "record": (name, type_name, ref_range, desc)}
    return index


def find_entities(text: str) -> List[str]:
    """在文本中匹配 KG 实体名（子串匹配，长名优先避免误切）。"""
    names = sorted(entity_index().keys(), key=len, reverse=True)
    return [n for n in names if n in text]


def guideline_for(disease: str) -> Tuple[str, str] | None:
    """疾病名 → (指南来源标注, 指南全文)；仅高血压/糖尿病有指南。"""
    mapping = {"高血压": "《中国高血压防治指南2023》", "糖尿病": "《中国2型糖尿病防治指南2020》"}
    if disease in mapping:
        key = f"{disease}诊疗指南.txt" if disease == "高血压" else f"{disease}管理指南.txt"
        return mapping[disease], GUIDELINES[key]
    return None


def split_guideline_sections(text: str) -> List[Tuple[str, str]]:
    """把指南文本切成 (章节标题, 章节正文) 列表；首段为 (文件名, 标题段)。"""
    pattern = re.compile(r"^[一二三四五六七八九十]+、.*$", re.M)
    matches = list(pattern.finditer(text))
    if not matches:
        return [("全文", text)]
    sections = []
    header = text[: matches[0].start()].strip()
    if header:
        sections.append(("概述", header))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].strip()
        title = m.group(0).strip()
        sections.append((title, body))
    return sections
