"""缓存预热工具 - 系统启动时预加载热数据"""
import asyncio
from typing import List, Dict, Any
from app.services.cache_service import cache_service
from app.utils.logger import app_logger


class CacheWarmer:
    """缓存预热管理器"""
    
    @staticmethod
    async def warm_up_all():
        """预热所有关键数据"""
        app_logger.info("开始预热系统缓存...")
        
        tasks = [
            CacheWarmer.warm_up_common_queries(),
            CacheWarmer.warm_up_popular_entities(),
            CacheWarmer.warm_up_system_config(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        app_logger.info(f"✓ 缓存预热完成: {success_count}/{len(tasks)} 个预热任务成功")
    
    @staticmethod
    async def warm_up_common_queries():
        """预热常见查询结果"""
        try:
            # 预热常见症状列表
            common_symptoms = {
                "fever": {"name": "发烧", "severity": "high"},
                "cough": {"name": "咳嗽", "severity": "medium"},
                "headache": {"name": "头痛", "severity": "medium"},
                "nausea": {"name": "恶心", "severity": "low"},
            }
            
            cache_service.warm_up("symptoms", common_symptoms, ttl=86400)  # 24小时
            
            # 预热常见药物列表
            common_drugs = {
                "aspirin": {"name": "阿司匹林", "category": "pain_relief"},
                "ibuprofen": {"name": "布洛芬", "category": "pain_relief"},
                "paracetamol": {"name": "扑热息痛", "category": "fever_reduction"},
            }
            
            cache_service.warm_up("drugs", common_drugs, ttl=86400)
            
            app_logger.info("✓ 常见查询缓存预热完成")
            return True
        except Exception as e:
            app_logger.error(f"✗ 常见查询缓存预热失败: {e}")
            return False
    
    @staticmethod
    async def warm_up_popular_entities():
        """预热热门实体数据"""
        try:
            # 预热热门科室
            popular_departments = {
                "cardiology": {"name": "心内科", "desc": "心血管疾病诊疗"},
                "neurology": {"name": "神经科", "desc": "神经系统疾病诊疗"},
                "orthopedics": {"name": "骨科", "desc": "骨骼肌肉疾病诊疗"},
            }
            
            cache_service.warm_up("departments", popular_departments, ttl=604800)  # 7天
            
            app_logger.info("✓ 热门实体缓存预热完成")
            return True
        except Exception as e:
            app_logger.error(f"✗ 热门实体缓存预热失败: {e}")
            return False
    
    @staticmethod
    async def warm_up_system_config():
        """预热系统配置数据"""
        try:
            config_data = {
                "api_version": "v1",
                "features": {
                    "consultation": True,
                    "knowledge_graph": True,
                    "recommendations": True,
                },
                "limits": {
                    "max_consultation_length": 5000,
                    "max_daily_consultations": 100,
                }
            }
            
            cache_service.set("config", "system", config_data, l2_ttl=3600)
            
            app_logger.info("✓ 系统配置缓存预热完成")
            return True
        except Exception as e:
            app_logger.error(f"✗ 系统配置缓存预热失败: {e}")
            return False
    
    @staticmethod
    def schedule_periodic_warm_up(interval_seconds: int = 3600):
        """定期预热缓存"""
        async def periodic_task():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    app_logger.info(f"执行定期缓存预热 (间隔={interval_seconds}s)")
                    await CacheWarmer.warm_up_all()
                except Exception as e:
                    app_logger.error(f"定期预热任务失败: {e}")
        
        return periodic_task()


# 便捷函数
async def initialize_cache():
    """初始化缓存系统"""
    await CacheWarmer.warm_up_all()


def schedule_cache_warming():
    """启动定期缓存预热"""
    return CacheWarmer.schedule_periodic_warm_up(interval_seconds=3600)
