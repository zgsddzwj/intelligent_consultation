"""数据库索引定义和管理

提供数据库索引的创建、验证和管理功能。
索引策略：
- 常用查询字段：单列索引
- 联合查询条件：复合索引
- 外键关联：外键索引
- 时间范围查询：时间字段索引

Usage:
    from app.database.indexes import create_indexes, verify_indexes
    
    # 创建所有索引
    create_indexes()
    
    # 验证索引状态
    status = verify_indexes()
"""
from typing import List, Dict, Tuple
from sqlalchemy import Index, text
from app.database.session import engine
from app.utils.logger import app_logger


# 索引定义列表：(SQL语句, 表名, 描述)
INDEX_DEFINITIONS: List[Tuple[str, str, str]] = [
    # ========== 用户表索引 ==========
    ("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)", 
     "users", "用户名唯一查询"),
    ("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)", 
     "users", "邮箱登录查询"),
    ("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)", 
     "users", "按角色筛选"),
    ("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)", 
     "users", "注册时间排序"),
    
    # ========== 咨询表索引 ==========
    ("CREATE INDEX IF NOT EXISTS idx_consultations_user_id ON consultations(user_id)", 
     "consultations", "用户咨询历史"),
    ("CREATE INDEX IF NOT EXISTS idx_consultations_agent_type ON consultations(agent_type)", 
     "consultations", "Agent类型筛选"),
    ("CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status)", 
     "consultations", "状态筛选"),
    ("CREATE INDEX IF NOT EXISTS idx_consultations_created_at ON consultations(created_at)", 
     "consultations", "时间排序"),
    ("CREATE INDEX IF NOT EXISTS idx_consultations_user_status ON consultations(user_id, status)", 
     "consultations", "用户+状态联合查询"),
    
    # ========== 知识文档表索引 ==========
    ("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source ON knowledge_documents(source)", 
     "knowledge_documents", "来源筛选"),
    ("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_title ON knowledge_documents(title)", 
     "knowledge_documents", "标题搜索"),
    ("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_created_at ON knowledge_documents(created_at)", 
     "knowledge_documents", "时间排序"),
    ("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_object_storage_key ON knowledge_documents(object_storage_key)", 
     "knowledge_documents", "对象存储键查找"),
    ("CREATE INDEX IF NOT EXISTS idx_knowledge_documents_storage_type ON knowledge_documents(storage_type)", 
     "knowledge_documents", "存储类型筛选"),
    
    # ========== Agent日志表索引 ==========
    ("CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_type ON agent_logs(agent_type)", 
     "agent_logs", "Agent类型统计"),
    ("CREATE INDEX IF NOT EXISTS idx_agent_logs_consultation_id ON agent_logs(consultation_id)", 
     "agent_logs", "关联咨询记录"),
    ("CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at)", 
     "agent_logs", "日志时间排序"),
]


def create_indexes() -> Dict[str, any]:
    """创建所有数据库索引
    
    按顺序执行所有预定义的索引创建SQL，
    单个索引失败不会影响其他索引的创建。
    
    Returns:
        执行结果字典：
        - success_count: 成功数量
        - failed_count: 失败数量
        - details: 详细结果列表
    """
    result = {
        "success_count": 0,
        "failed_count": 0,
        "details": []
    }
    
    try:
        with engine.connect() as conn:
            for index_sql, table_name, description in INDEX_DEFINITIONS:
                index_name = index_sql.split()[-1]  # 提取索引名
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    
                    result["success_count"] += 1
                    result["details"].append({
                        "index": index_name,
                        "table": table_name,
                        "status": "success",
                        "description": description
                    })
                    
                    app_logger.debug(f"索引创建成功: {index_name} ({table_name})")
                    
                except Exception as e:
                    result["failed_count"] += 1
                    result["details"].append({
                        "index": index_name,
                        "table": table_name,
                        "status": "failed",
                        "error": str(e),
                        "description": description
                    })
                    app_logger.warning(f"索引创建失败: {index_name} - {e}")
        
        app_logger.info(
            f"索引创建完成: 成功 {result['success_count']} 个, "
            f"失败 {result['failed_count']} 个"
        )
        
    except Exception as e:
        app_logger.error(f"数据库连接错误，无法创建索引: {e}")
        raise
    
    return result


def verify_indexes() -> Dict[str, List[str]]:
    """验证已存在的索引
    
    Returns:
        以表名为键的已存在索引名称列表
    """
    existing_indexes = {}
    
    try:
        with engine.connect() as conn:
            # PostgreSQL 查询索引的SQL
            sql = """
                SELECT tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """
            result = conn.execute(text(sql))
            
            for row in result:
                table_name = row[0]
                index_name = row[1]
                
                if table_name not in existing_indexes:
                    existing_indexes[table_name] = []
                existing_indexes[table_name].append(index_name)
        
        app_logger.info(f"索引验证完成，发现 {len(existing_indexes)} 张表的索引")
        
    except Exception as e:
        app_logger.error(f"验证索引时出错: {e}")
    
    return existing_indexes


def drop_index(index_name: str) -> bool:
    """删除指定索引
    
    Args:
        index_name: 要删除的索引名称
        
    Returns:
        是否删除成功
    """
    try:
        with engine.connect() as conn:
            sql = f"DROP INDEX IF EXISTS {index_name}"
            conn.execute(text(sql))
            conn.commit()
            app_logger.info(f"索引已删除: {index_name}")
            return True
    except Exception as e:
        app_logger.error(f"删除索引失败: {index_name} - {e}")
        return False


if __name__ == "__main__":
    # 直接运行时执行索引创建
    print("开始创建数据库索引...")
    result = create_indexes()
    print(f"\n完成！成功: {result['success_count']}, 失败: {result['failed_count']}")

