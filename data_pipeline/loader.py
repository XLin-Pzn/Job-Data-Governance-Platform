from typing import List, Dict, Any
from loguru import logger
from config import config
from data_pipeline.collector import JobCollector
from data_pipeline.transformer import DataTransformer
import asyncio

logger.add(
    config.LOG_FILE,
    format="{time} | {level} | {message}",
    level=config.LOG_LEVEL
)

class DataLoader:
    """数据加载模块 - 整合采集和ETL流程"""
    
    def __init__(self):
        self.collector = None
        self.transformer = DataTransformer()
    
    async def load_from_sample(self) -> Dict[str, Any]:
        """从样本数据加载"""
        try:
            logger.info("="*50)
            logger.info("开始加载样本数据")
            logger.info("="*50)
            
            async with JobCollector() as collector:
                # 1. 采集数据
                jobs = collector.load_sample_jobs()
                logger.info(f"✓ 采集完成: {len(jobs)} 条数据")
                
                # 2. 保存原始记录
                log_id = collector.save_to_db(
                    jobs,
                    source_url="sample_data",
                    status="success"
                )
                logger.info(f"✓ 原始记录保存: log_id={log_id}")
                
                # 3. ETL清洗
                df_clean = self.transformer.clean_and_validate(jobs)
                logger.info(f"✓ 数据清洗完成: {len(df_clean)} 条有效数据")
                
                # 4. 幂等导入
                result = self.transformer.insert_idempotent(log_id, df_clean)
                logger.info(f"✓ 幂等导入完成: {result}")
                
                logger.info("="*50)
                logger.info("样本数据加载成功!")
                logger.info("="*50)
                
                return {
                    "status": "success",
                    "batch_id": collector.batch_id,
                    "log_id": log_id,
                    "import_result": result
                }
        
        except Exception as e:
            logger.error(f"加载失败: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    async def load_from_api(self, urls: List[str]) -> Dict[str, Any]:
        """从API加载数据"""
        try:
            logger.info("="*50)
            logger.info(f"开始从API加载数据: {urls}")
            logger.info("="*50)
            
            async with JobCollector() as collector:
                # 1. 采集数据
                jobs = await collector.fetch_jobs_batch(urls)
                if not jobs:
                    logger.warning("未获取到任何数据")
                    return {"status": "failed", "error": "No data retrieved"}
                
                logger.info(f"✓ 采集完成: {len(jobs)} 条数据")
                
                # 2. 保存原始记录
                log_id = collector.save_to_db(
                    jobs,
                    source_url=urls[0],
                    status="success"
                )
                logger.info(f"✓ 原始记录保存: log_id={log_id}")
                
                # 3. ETL清洗
                df_clean = self.transformer.clean_and_validate(jobs)
                logger.info(f"✓ 数据清洗完成: {len(df_clean)} 条有效数据")
                
                # 4. 幂等导入
                result = self.transformer.insert_idempotent(log_id, df_clean)
                logger.info(f"✓ 幂等导入完成: {result}")
                
                logger.info("="*50)
                logger.info("API数据加载成功!")
                logger.info("="*50)
                
                return {
                    "status": "success",
                    "batch_id": collector.batch_id,
                    "log_id": log_id,
                    "import_result": result
                }
        
        except Exception as e:
            logger.error(f"加载失败: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def close(self):
        """关闭资源"""
        if self.transformer:
            self.transformer.close()


if __name__ == '__main__':
    # 测试
    loader = DataLoader()
    result = asyncio.run(loader.load_from_sample())
    print(result)
    loader.close()
