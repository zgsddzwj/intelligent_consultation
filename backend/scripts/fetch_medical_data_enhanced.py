"""增强版：从公开数据集获取医疗知识库数据"""
import requests
import json
import os
import csv
from pathlib import Path
from typing import List, Dict
from app.utils.logger import app_logger


def fetch_from_icd10_api():
    """从ICD-10 API获取疾病数据（示例）"""
    # 注意：这里使用公开的ICD-10数据源
    # 实际可以使用WHO的ICD-10 API或其他公开API
    
    # 示例：从GitHub上的公开ICD-10数据集获取
    icd10_url = "https://raw.githubusercontent.com/kamillamagna/ICD-10-CSV/master/codes.csv"
    
    try:
        response = requests.get(icd10_url, timeout=10)
        if response.status_code == 200:
            # 解析CSV数据
            lines = response.text.split('\n')
            diseases = []
            for line in lines[1:11]:  # 只取前10条作为示例
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        diseases.append({
                            "code": parts[0].strip(),
                            "name": parts[1].strip(),
                            "description": parts[2].strip() if len(parts) > 2 else ""
                        })
            return diseases
    except Exception as e:
        app_logger.warning(f"从ICD-10 API获取数据失败: {e}")
    
    return []


def fetch_from_pubmed_abstracts(keywords: List[str], max_results: int = 5):
    """从PubMed获取医学文献摘要（需要API key）"""
    # PubMed API使用示例
    # 实际使用时需要注册获取API key: https://www.ncbi.nlm.nih.gov/account/
    
    articles = []
    for keyword in keywords[:2]:  # 限制关键词数量
        try:
            # PubMed E-utilities API
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
            search_url = f"{base_url}esearch.fcgi"
            
            params = {
                "db": "pubmed",
                "term": keyword,
                "retmax": max_results,
                "retmode": "json"
            }
            
            # 注意：这里仅提供框架，实际需要处理API响应
            app_logger.info(f"搜索PubMed: {keyword} (需要配置API key)")
            
        except Exception as e:
            app_logger.warning(f"PubMed搜索失败: {e}")
    
    return articles


def fetch_chinese_medical_guidelines():
    """获取中文医疗指南（从公开资源）"""
    # 这里可以添加从中国知网、中华医学会等网站获取指南的逻辑
    # 注意：需要遵守网站的使用条款和版权
    
    guidelines = [
        {
            "title": "中国高血压防治指南2023",
            "source": "中华医学会心血管病学分会",
            "url": "https://www.cma.org.cn/art/2023/11/13/art_1_1.html",
            "description": "最新版中国高血压防治指南"
        },
        {
            "title": "中国2型糖尿病防治指南2020",
            "source": "中华医学会糖尿病学分会",
            "url": "https://www.cma.org.cn/art/2021/4/19/art_1_1.html",
            "description": "2型糖尿病诊疗指南"
        },
    ]
    
    return guidelines


def create_sample_medical_knowledge():
    """创建示例医疗知识数据（基于公开信息）"""
    data_dir = Path("./data/knowledge_graph")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建更丰富的疾病数据
    diseases = [
        {
            "code": "I10",
            "name": "高血压",
            "description": "原发性高血压，以动脉血压持续升高为主要特征",
            "category": "循环系统疾病",
            "symptoms": ["头痛", "头晕", "心悸", "胸闷"],
            "treatments": ["硝苯地平", "卡托普利", "氯沙坦"],
            "examinations": ["血压测量", "心电图", "血常规"]
        },
        {
            "code": "E11",
            "name": "2型糖尿病",
            "description": "非胰岛素依赖型糖尿病",
            "category": "内分泌疾病",
            "symptoms": ["多饮", "多尿", "多食", "体重下降"],
            "treatments": ["二甲双胍", "格列齐特", "胰岛素"],
            "examinations": ["血糖检测", "糖化血红蛋白", "尿常规"]
        },
        {
            "code": "B16",
            "name": "急性乙型肝炎",
            "description": "乙型病毒性肝炎",
            "category": "传染病",
            "symptoms": ["乏力", "食欲不振", "黄疸", "转氨酶增高"],
            "treatments": ["恩替卡韦", "替诺福韦", "干扰素"],
            "examinations": ["乙肝五项", "肝功能检查", "HBV-DNA"]
        },
        {
            "code": "J11",
            "name": "流行性感冒",
            "description": "流感病毒感染引起的急性呼吸道传染病",
            "category": "呼吸系统疾病",
            "symptoms": ["发热", "咳嗽", "咽痛", "全身酸痛"],
            "treatments": ["奥司他韦", "复方感冒灵", "对症治疗"],
            "examinations": ["血常规", "流感病毒检测"]
        },
        {
            "code": "F48.0",
            "name": "神经衰弱",
            "description": "神经症性障碍，主要表现为易疲劳、注意力不集中",
            "category": "精神障碍",
            "symptoms": ["易疲乏", "失眠", "注意力不集中", "易激惹"],
            "treatments": ["心理治疗", "药物治疗", "生活方式调整"],
            "examinations": ["心理评估", "神经系统检查"]
        },
    ]
    
    # 保存到JSON
    with open(data_dir / "diseases_enhanced.json", "w", encoding="utf-8") as f:
        json.dump(diseases, f, ensure_ascii=False, indent=2)
    
    app_logger.info(f"已创建 {len(diseases)} 条疾病数据")
    
    # 创建药物数据
    drugs = [
        {
            "name": "硝苯地平",
            "generic_name": "Nifedipine",
            "category": "钙通道阻滞剂",
            "indication": "高血压、心绞痛",
            "dosage": "10-20mg, 每日2-3次",
            "contraindication": "对本品过敏者、严重低血压患者禁用",
            "side_effects": ["头痛", "面部潮红", "心悸"]
        },
        {
            "name": "二甲双胍",
            "generic_name": "Metformin",
            "category": "双胍类降糖药",
            "indication": "2型糖尿病",
            "dosage": "500-2000mg, 每日2-3次",
            "contraindication": "严重肾功能不全、严重肝功能不全禁用",
            "side_effects": ["胃肠道反应", "乳酸酸中毒（罕见）"]
        },
        {
            "name": "恩替卡韦",
            "generic_name": "Entecavir",
            "category": "核苷类抗病毒药",
            "indication": "慢性乙型肝炎",
            "dosage": "0.5mg, 每日1次",
            "contraindication": "对本品过敏者禁用",
            "side_effects": ["头痛", "疲劳", "眩晕"]
        },
    ]
    
    with open(data_dir / "drugs_enhanced.json", "w", encoding="utf-8") as f:
        json.dump(drugs, f, ensure_ascii=False, indent=2)
    
    app_logger.info(f"已创建 {len(drugs)} 条药物数据")
    
    return diseases, drugs


def download_medical_documents_from_urls():
    """从URL下载医疗文档（示例）"""
    # 注意：实际使用时需要遵守网站的使用条款
    # 这里仅提供框架
    
    guidelines = fetch_chinese_medical_guidelines()
    docs_dir = Path("./data/documents/guidelines")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    for guideline in guidelines:
        file_path = docs_dir / f"{guideline['title']}.txt"
        if not file_path.exists():
            # 创建示例内容（实际应该从URL下载）
            content = f"""
标题: {guideline['title']}
来源: {guideline['source']}
URL: {guideline['url']}
描述: {guideline['description']}

（实际内容需要从源网站下载或通过API获取）
注意：请遵守相关网站的使用条款和版权规定。
"""
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            app_logger.info(f"创建指南文件: {file_path.name}")


if __name__ == "__main__":
    app_logger.info("开始获取增强版医疗知识库数据...")
    
    # 创建示例数据
    create_sample_medical_knowledge()
    
    # 下载文档
    download_medical_documents_from_urls()
    
    # 尝试从API获取（可选）
    try:
        icd10_data = fetch_from_icd10_api()
        if icd10_data:
            data_dir = Path("./data/knowledge_graph")
            with open(data_dir / "icd10_from_api.json", "w", encoding="utf-8") as f:
                json.dump(icd10_data, f, ensure_ascii=False, indent=2)
            app_logger.info(f"从API获取了 {len(icd10_data)} 条ICD-10数据")
    except Exception as e:
        app_logger.warning(f"从API获取数据失败: {e}")
    
    app_logger.info("医疗知识库数据获取完成")

