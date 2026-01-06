"""数据库索引定义和创建"""
from sqlalchemy import Index, text
from app.database.session import engine
from app.utils.logger import app_logger


def create_indexes():
    """创建数据库索引"""
    indexes = [
        # 用户表索引
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
        
        # 咨询表索引
        "CREATE INDEX IF NOT EXISTS idx_consultations_user_id ON consultations(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_agent_type ON consultations(agent_type)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_created_at ON consultations(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_consultations_user_status ON consultations(user_id, status)",
        
        # 知识文档表索引
        "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source ON knowledge_documents(source)",
        "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_title ON knowledge_documents(title)",
        "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_created_at ON knowledge_documents(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_object_storage_key ON knowledge_documents(object_storage_key)",
        "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_storage_type ON knowledge_documents(storage_type)",
        
        # Agent日志表索引
        "CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_type ON agent_logs(agent_type)",
        "CREATE INDEX IF NOT EXISTS idx_agent_logs_consultation_id ON agent_logs(consultation_id)",
        "CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at)",
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                    app_logger.info(f"索引创建成功: {index_sql.split()[-1]}")
                except Exception as e:
                    app_logger.warning(f"索引创建失败: {index_sql}, 错误: {e}")
    except Exception as e:
        app_logger.error(f"创建索引时出错: {e}")


if __name__ == "__main__":
    create_indexes()

