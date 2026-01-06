"""初始化知识图谱 - 增强版"""
from app.knowledge.graph.builder import KnowledgeGraphBuilder
from app.utils.logger import app_logger


def init_knowledge_graph():
    """初始化知识图谱数据"""
    builder = KnowledgeGraphBuilder()
    
    # 初始化模式（创建索引）
    builder.initialize_schema()
    
    app_logger.info("开始初始化知识图谱数据...")
    
    # ========== 创建科室 ==========
    departments = [
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
    
    for name, desc, scope in departments:
        try:
            builder.create_entity("Department", name, {
                "description": desc,
                "scope": scope
            })
        except Exception as e:
            app_logger.warning(f"科室 {name} 可能已存在: {e}")
    
    # ========== 创建疾病 ==========
    diseases = [
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
    
    for name, icd10, desc, etiology in diseases:
        try:
            builder.create_entity("Disease", name, {
                "icd10": icd10,
                "description": desc,
                "etiology": etiology
            })
        except Exception as e:
            app_logger.warning(f"疾病 {name} 可能已存在: {e}")
    
    # ========== 创建症状 ==========
    symptoms = [
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
    
    for name, severity, desc in symptoms:
        try:
            builder.create_entity("Symptom", name, {
                "severity": severity,
                "description": desc
            })
        except Exception as e:
            app_logger.warning(f"症状 {name} 可能已存在: {e}")
    
    # ========== 创建药物 ==========
    drugs = [
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
    
    for name, generic, form, indication, contraindication in drugs:
        try:
            builder.create_entity("Drug", name, {
                "generic_name": generic,
                "dosage_form": form,
                "indication": indication,
                "contraindication": contraindication
            })
        except Exception as e:
            app_logger.warning(f"药物 {name} 可能已存在: {e}")
    
    # ========== 创建检查 ==========
    examinations = [
        ("血压测量", "生命体征", "正常值: 收缩压<120mmHg, 舒张压<80mmHg", "测量动脉血压"),
        ("血糖检测", "实验室检查", "空腹血糖: 3.9-6.1mmol/L", "检测血液中葡萄糖含量"),
        ("乙肝表面抗原检测", "实验室检查", "阴性", "检测乙肝病毒感染"),
        ("肝功能检查", "实验室检查", "转氨酶正常范围", "检测肝功能指标"),
        ("血常规", "实验室检查", "各项指标正常范围", "检测血液成分"),
    ]
    
    for name, type_name, ref_range, desc in examinations:
        try:
            builder.create_entity("Examination", name, {
                "type": type_name,
                "reference_range": ref_range,
                "description": desc
            })
        except Exception as e:
            app_logger.warning(f"检查 {name} 可能已存在: {e}")
    
    # ========== 创建关系 ==========
    relationships = [
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
    
    for from_type, from_name, rel_type, to_type, to_name, props in relationships:
        try:
            builder.create_relationship(from_type, from_name, rel_type, to_type, to_name, props)
        except Exception as e:
            app_logger.warning(f"关系创建失败: {from_type}({from_name}) -[{rel_type}]-> {to_type}({to_name}): {e}")
    
    app_logger.info("知识图谱初始化完成！")


if __name__ == "__main__":
    init_knowledge_graph()
