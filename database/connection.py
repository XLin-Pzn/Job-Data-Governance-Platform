from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import config
from loguru import logger

# 创建数据库引擎
engine = create_engine(
    config.DATABASE_URL,
    echo=config.API_DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True  # 连接前检查连接是否有效
)

# 创建会话工厂
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# 创建基类
Base = declarative_base()

def get_db():
    """获取数据库会话（用于FastAPI依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
