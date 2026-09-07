import os
from dotenv import load_dotenv
from pathlib import Path

# 加载环境变量
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """基础配置"""
    
    # 数据库配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'job_governance')
    
    # 构建数据库URL
    DATABASE_URL = f"mysql+mysql-connector-python://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # API配置
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 8000))
    API_DEBUG = os.getenv('API_DEBUG', 'True') == 'True'
    
    # 数据采集配置
    COLLECTOR_TIMEOUT = int(os.getenv('DATACOLLECTOR_TIMEOUT', 10))
    COLLECTOR_MAX_RETRIES = int(os.getenv('DATACOLLECTOR_MAX_RETRIES', 3))
    COLLECTOR_RATE_LIMIT = int(os.getenv('DATACOLLECTOR_RATE_LIMIT', 5))
    COLLECTOR_CONCURRENT_LIMIT = int(os.getenv('DATACOLLECTOR_CONCURRENT_LIMIT', 10))
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)

config = Config()
