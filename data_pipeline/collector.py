import asyncio
import httpx
import json
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any, Optional
from loguru import logger
from config import config
from database.connection import SessionLocal
from database.models import ImportLog, RawRecords
from sqlalchemy import insert

class JobCollector:
    """数据采集模块 - 从API或文件读取岗位数据"""
    
    def __init__(self):
        self.batch_id = str(uuid4())
        self.timeout = config.COLLECTOR_TIMEOUT
        self.max_retries = config.COLLECTOR_MAX_RETRIES
        self.rate_limit = config.COLLECTOR_RATE_LIMIT
        self.concurrent_limit = config.COLLECTOR_CONCURRENT_LIMIT
        self.session = None
        logger.add(
            config.LOG_FILE,
            format="{time} | {level} | {message}",
            level=config.LOG_LEVEL
        )
    
    async def __aenter__(self):
        """异步上下文管理器"""
        self.session = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=self.concurrent_limit)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """关闭连接"""
        if self.session:
            await self.session.aclose()
    
    async def fetch_with_retry(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """带重试的HTTP请求"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"获取数据 (尝试 {attempt + 1}/{self.max_retries}): {url}")
                response = await self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                logger.info(f"成功获取数据: {url}")
                return data
            
            except httpx.TimeoutException as e:
                logger.warning(f"超时 (尝试 {attempt + 1}): {url} - {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            
            except httpx.HTTPError as e:
                logger.error(f"HTTP错误: {url} - {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {url} - {str(e)}")
                return None
            
            except Exception as e:
                logger.error(f"未知错误: {url} - {str(e)}")
                return None
        
        logger.error(f"在{self.max_retries}次尝试后仍未成功: {url}")
        return None
    
    async def fetch_jobs_from_api(self, url: str) -> List[Dict[str, Any]]:
        """从API获取岗位数据"""
        if not self.session:
            raise RuntimeError("未初始化session，请使用async with语句")
        
        data = await self.fetch_with_retry(url)
        
        if data is None:
            logger.error(f"无法获取数据: {url}")
            return []
        
        # 支持不同API响应格式
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            jobs = data.get('data', [])
            return jobs if isinstance(jobs, list) else []
        elif isinstance(data, dict) and 'jobs' in data:
            jobs = data.get('jobs', [])
            return jobs if isinstance(jobs, list) else []
        else:
            return [data] if isinstance(data, dict) else []
    
    async def fetch_jobs_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """并发获取多个URL的数据"""
        if not self.session:
            raise RuntimeError("未初始化session，请使用async with语句")
        
        sem = asyncio.Semaphore(self.rate_limit)
        
        async def fetch_with_semaphore(url):
            async with sem:
                return await self.fetch_jobs_from_api(url)
        
        results = await asyncio.gather(
            *[fetch_with_semaphore(url) for url in urls],
            return_exceptions=True
        )
        
        all_jobs = []
        for result in results:
            if isinstance(result, list):
                all_jobs.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"批量获取出错: {result}")
        
        logger.info(f"共获取 {len(all_jobs)} 条岗位数据")
        return all_jobs
    
    def load_sample_jobs(self) -> List[Dict[str, Any]]:
        """加载样本数据（用于测试）"""
        sample_jobs = [
            {
                'job_title': 'Python开发工程师',
                'company': '字节跳动',
                'city': '北京',
                'salary_min': 25000,
                'salary_max': 45000,
                'required_skills': ['Python', 'FastAPI', 'MySQL'],
                'job_description': '负责后端服务开发'
            },
            {
                'job_title': 'Java开发工程师',
                'company': '阿里巴巴',
                'city': '杭州',
                'salary_min': 28000,
                'salary_max': 50000,
                'required_skills': ['Java', 'Spring Boot', 'MongoDB'],
                'job_description': '负责分布式系统开发'
            },
            {
                'job_title': '数据分析师',
                'company': '腾讯',
                'city': '深圳',
                'salary_min': 20000,
                'salary_max': 35000,
                'required_skills': ['SQL', 'Python', 'Tableau'],
                'job_description': '负责数据分析和挖掘'
            },
            {
                'job_title': '前端开发工程师',
                'company': '京东',
                'city': '上海',
                'salary_min': 22000,
                'salary_max': 40000,
                'required_skills': ['React', 'Vue', 'JavaScript'],
                'job_description': '负责Web应用开发'
            },
            {
                'job_title': '运维工程师',
                'company': '滴滴',
                'city': '成都',
                'salary_min': 20000,
                'salary_max': 32000,
                'required_skills': ['Linux', 'Docker', 'Kubernetes'],
                'job_description': '负责系统运维和监控'
            },
        ]
        logger.info(f"加载 {len(sample_jobs)} 条样本数据")
        return sample_jobs
    
    def save_to_db(
        self,
        jobs_data: List[Dict[str, Any]],
        source_url: str = "sample_data",
        status: str = "success"
    ) -> int:
        """保存采集日志和原始记录到数据库"""
        db = SessionLocal()
        try:
            # 1. 记录采集日志
            import_log = ImportLog(
                source_url=source_url,
                batch_id=self.batch_id,
                import_time=datetime.now(),
                status=status,
                record_count=len(jobs_data),
                raw_summary=json.dumps(jobs_data[:100], ensure_ascii=False)  # 前100条摘要
            )
            db.add(import_log)
            db.flush()  # 获取log_id
            log_id = import_log.log_id
            
            # 2. 保存原始记录
            for job_data in jobs_data:
                raw_record = RawRecords(
                    log_id=log_id,
                    original_data=json.dumps(job_data, ensure_ascii=False),
                    extracted_at=datetime.now()
                )
                db.add(raw_record)
            
            db.commit()
            logger.info(f"成功保存采集日志 (log_id={log_id}) 和 {len(jobs_data)} 条原始记录")
            return log_id
        
        except Exception as e:
            db.rollback()
            logger.error(f"保存到数据库失败: {str(e)}")
            raise
        
        finally:
            db.close()


# 使用示例
async def main():
    async with JobCollector() as collector:
        # 方式1: 加载样本数据
        jobs = collector.load_sample_jobs()
        log_id = collector.save_to_db(jobs, source_url="sample_data")
        print(f"样本数据导入成功，batch_id: {collector.batch_id}, log_id: {log_id}")
        
        # 方式2: 从API获取数据（示例）
        # urls = ['https://api.example.com/jobs']
        # jobs = await collector.fetch_jobs_batch(urls)
        # log_id = collector.save_to_db(jobs, source_url=urls[0])

if __name__ == '__main__':
    asyncio.run(main())
