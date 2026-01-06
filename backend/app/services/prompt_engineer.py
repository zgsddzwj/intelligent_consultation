"""Prompt工程系统 - 版本管理、A/B测试和模板库"""
from typing import Dict, List, Any, Optional
import json
from app.services.redis_service import redis_service
from app.config import get_settings
from app.utils.logger import app_logger

settings = get_settings()


class PromptTemplate:
    """Prompt模板类"""
    
    def __init__(self, name: str, version: str, system_prompt: str,
                 user_prompt_template: str, few_shot_examples: List[Dict] = None,
                 output_format: Optional[str] = None, metadata: Dict = None):
        self.name = name
        self.version = version
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.few_shot_examples = few_shot_examples or []
        self.output_format = output_format
        self.metadata = metadata or {}
    
    def format(self, **kwargs) -> Dict[str, str]:
        """格式化Prompt"""
        user_prompt = self.user_prompt_template.format(**kwargs)
        
        # 添加few-shot示例
        if self.few_shot_examples:
            examples_text = "\n\n示例：\n"
            for i, example in enumerate(self.few_shot_examples, 1):
                examples_text += f"\n示例{i}:\n"
                examples_text += f"输入: {example.get('input', '')}\n"
                examples_text += f"输出: {example.get('output', '')}\n"
            user_prompt = examples_text + "\n\n" + user_prompt
        
        # 添加输出格式要求
        if self.output_format:
            user_prompt += f"\n\n输出格式要求：{self.output_format}"
        
        return {
            "system": self.system_prompt,
            "user": user_prompt
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "few_shot_examples": self.few_shot_examples,
            "output_format": self.output_format,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """从字典创建"""
        return cls(
            name=data["name"],
            version=data["version"],
            system_prompt=data["system_prompt"],
            user_prompt_template=data["user_prompt_template"],
            few_shot_examples=data.get("few_shot_examples", []),
            output_format=data.get("output_format"),
            metadata=data.get("metadata", {})
        )


class PromptEngineer:
    """Prompt工程管理器"""
    
    def __init__(self):
        self.templates: Dict[str, Dict[str, PromptTemplate]] = {}  # {name: {version: template}}
        self.current_versions: Dict[str, str] = {}  # {name: current_version}
        self.ab_test_configs: Dict[str, Dict] = {}  # A/B测试配置
        self._load_templates()
    
    def _load_templates(self):
        """加载模板"""
        # 从Redis或文件加载
        try:
            templates_data = redis_service.get_json("prompt_templates")
            if templates_data:
                for name, versions in templates_data.items():
                    self.templates[name] = {}
                    for version, template_data in versions.items():
                        self.templates[name][version] = PromptTemplate.from_dict(template_data)
                    # 设置当前版本
                    if versions:
                        self.current_versions[name] = max(versions.keys())
        except Exception as e:
            app_logger.warning(f"加载Prompt模板失败: {e}")
    
    def register_template(self, template: PromptTemplate, set_as_current: bool = True):
        """注册模板"""
        if template.name not in self.templates:
            self.templates[template.name] = {}
        
        self.templates[template.name][template.version] = template
        
        if set_as_current:
            self.current_versions[template.name] = template.version
        
        # 保存到Redis
        self._save_templates()
    
    def get_template(self, name: str, version: Optional[str] = None) -> Optional[PromptTemplate]:
        """获取模板"""
        if name not in self.templates:
            return None
        
        if version:
            return self.templates[name].get(version)
        else:
            # 返回当前版本
            current_version = self.current_versions.get(name)
            if current_version:
                return self.templates[name].get(current_version)
            # 如果没有当前版本，返回最新版本
            if self.templates[name]:
                return self.templates[name][max(self.templates[name].keys())]
        
        return None
    
    def format_prompt(self, name: str, version: Optional[str] = None, 
                     use_ab_test: bool = False, **kwargs) -> Optional[Dict[str, str]]:
        """格式化Prompt"""
        # A/B测试
        if use_ab_test and name in self.ab_test_configs:
            template = self._select_ab_test_template(name)
        else:
            template = self.get_template(name, version)
        
        if not template:
            return None
        
        return template.format(**kwargs)
    
    def _select_ab_test_template(self, name: str) -> Optional[PromptTemplate]:
        """选择A/B测试模板"""
        config = self.ab_test_configs.get(name)
        if not config:
            return self.get_template(name)
        
        import random
        variants = config.get("variants", [])
        if not variants:
            return self.get_template(name)
        
        # 根据权重选择
        weights = [v.get("weight", 1.0) for v in variants]
        selected = random.choices(variants, weights=weights)[0]
        
        return self.get_template(name, selected.get("version"))
    
    def setup_ab_test(self, name: str, variants: List[Dict[str, Any]], 
                     enabled: bool = True):
        """设置A/B测试"""
        self.ab_test_configs[name] = {
            "enabled": enabled,
            "variants": variants
        }
        app_logger.info(f"A/B测试已设置: {name}, 变体数: {len(variants)}")
    
    def _save_templates(self):
        """保存模板到Redis"""
        try:
            templates_data = {}
            for name, versions in self.templates.items():
                templates_data[name] = {
                    version: template.to_dict()
                    for version, template in versions.items()
                }
            redis_service.set_json("prompt_templates", templates_data, ttl=None)  # 永久存储
        except Exception as e:
            app_logger.warning(f"保存Prompt模板失败: {e}")
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板"""
        result = []
        for name, versions in self.templates.items():
            result.append({
                "name": name,
                "versions": list(versions.keys()),
                "current_version": self.current_versions.get(name),
                "ab_test_enabled": name in self.ab_test_configs
            })
        return result


# 全局实例
prompt_engineer = PromptEngineer()

