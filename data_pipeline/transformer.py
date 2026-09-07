import pandas as pd
import json
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
from config import config
from database.connection import SessionLocal
from database.models import Jobs, RawRecords
from sqlalchemy import insert, func
from sqlalchemy.exc import IntegrityError

logger.add(
    config.LOG_FILE,
    format="{time} | {level} | {message}",
    level=config.LOG_LEVEL
)

class DataTransformer:
    """ETL清洗和转换模块"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def clean_and_validate(self, raw_jobs: List[Dict[str, Any]]) -> pd.DataFrame:
        """清洗和验证数据"""
        df = pd.DataFrame(raw_jobs)
        
        logger.info(f"原始数据行数: {len(df)}")
        
        # 1. 必要字段检查和补全
        required_fields = ['job_title', 'company', 'city']
        for field in required_fields:
            if field not in df.columns:
                df[field] = None
        
        # 2. 删除必要字段缺失的记录
        df_before = len(df)
        df = df[df['job_title'].notna() & (df['job_title'] != '')]
        df = df[df['company'].notna() & (df['company'] != '')]
        logger.info(f"删除缺失必要字段的记录: {df_before - len(df)} 条")
        
        # 3. 薪资字段处理
        if 'salary_min' not in df.columns:
            df['salary_min'] = None
        if 'salary_max' not in df.columns:
            df['salary_max'] = None
        
        df['salary_min'] = pd.to_numeric(df['salary_min'], errors='coerce')
        df['salary_max'] = pd.to_numeric(df['salary_max'], errors='coerce')
        
        # 4. 薪资范围验证（min不能大于max）
        invalid_salary = (df['salary_min'].notna() & df['salary_max'].notna() & 
                         (df['salary_min'] > df['salary_max']))
        if invalid_salary.any():
            logger.warning(f"发现 {invalid_salary.sum()} 条薪资范围异常的记录")
            # 交换错误的min和max
            df.loc[invalid_salary, ['salary_min', 'salary_max']] = \
                df.loc[invalid_salary, ['salary_max', 'salary_min']].values
        
        # 5. 技能字段处理
        if 'required_skills' not in df.columns:
            df['required_skills'] = None
        
        df['required_skills'] = df['required_skills'].apply(self._normalize_skills)
        
        # 6. 填充可选字段
        df['job_description'] = df.get('job_description', '').fillna('')
        df['city'] = df.get('city', '').fillna('未知')
        
        # 7. 计算数据质量评分
        df['data_quality_score'] = df.apply(self._calculate_quality_score, axis=1)
        
        # 8. 检测缺失字段
        df['missing_fields'] = df.apply(self._get_missing_fields, axis=1)
        
        logger.info(f"清洗后数据行数: {len(df)}")
        logger.info(f"平均数据质量评分: {df['data_quality_score'].mean():.2f}")
        
        return df
    
    def _normalize_skills(self, skills) -> str:
        """规范化技能字段"""
        if isinstance(skills, str):
            skills_list = [s.strip() for s in skills.split(',')]
        elif isinstance(skills, list):
            skills_list = [str(s).strip() for s in skills]
        else:
            skills_list = []
        
        return json.dumps(skills_list, ensure_ascii=False)
    
    def _calculate_quality_score(self, row) -> float:
        """计算数据质量评分 (0-100)"""
        score = 100.0
        
        # 缺失必要字段扣分
        if pd.isna(row['job_title']) or row['job_title'] == '':
            score -= 30
        if pd.isna(row['company']) or row['company'] == '':
            score -= 25
        if pd.isna(row['city']) or row['city'] == '':
            score -= 15
        
        # 缺失薪资信息扣分
        if pd.isna(row['salary_min']) or pd.isna(row['salary_max']):
            score -= 20
        
        # 薪资异常值检测
        if pd.notna(row['salary_min']) and pd.notna(row['salary_max']):
            if row['salary_min'] < 3000 or row['salary_max'] > 1000000:
                score -= 15
        
        # 缺失技能信息扣分
        if not row['required_skills'] or row['required_skills'] == '[]':
            score -= 10
        
        # 缺失职位描述扣分
        if not row['job_description'] or row['job_description'] == '':
            score -= 5
        
        return max(0, min(100, score))  # 保证分数在0-100之间
    
    def _get_missing_fields(self, row) -> str:
        """获取缺失字段列表"""
        missing = []
        fields = ['job_title', 'company', 'city', 'salary_min', 'salary_max', 'required_skills']
        
        for field in fields:
            if pd.isna(row[field]) or row[field] == '' or row[field] == '[]':
                missing.append(field)
        
        return json.dumps(missing, ensure_ascii=False)
    
    def insert_idempotent(self, log_id: int, cleaned_df: pd.DataFrame) -> Dict[str, Any]:
        """幂等导入：相同唯一键冲突时标记为重复而非插入
        
        Returns:
            {"inserted": 新插入数量, "duplicated": 重复数量, "failed": 失败数量}
        """
        try:
            inserted_count = 0
            duplicated_count = 0
            failed_count = 0
            
            for _, row in cleaned_df.iterrows():
                try:
                    # 检查是否已存在相同的唯一键
                    existing = self.db.query(Jobs).filter(
                        Jobs.log_id == log_id,
                        Jobs.job_title == row['job_title'],
                        Jobs.company == row['company']
                    ).first()
                    
                    if existing:
                        # 标记为重复
                        existing.is_duplicate = 1
                        duplicated_count += 1
                        logger.warning(
                            f"发现重复记录: {row['job_title']} @ {row['company']}"
                        )
                    else:
                        # 插入新记录
                        job = Jobs(
                            log_id=log_id,
                            job_title=row['job_title'],
                            company=row['company'],
                            city=row['city'],
                            salary_min=int(row['salary_min']) if pd.notna(row['salary_min']) else None,
                            salary_max=int(row['salary_max']) if pd.notna(row['salary_max']) else None,
                            required_skills=row['required_skills'],
                            job_description=row['job_description'],
                            data_quality_score=row['data_quality_score'],
                            missing_fields=row['missing_fields']
                        )
                        self.db.add(job)
                        inserted_count += 1
                
                except IntegrityError as e:
                    self.db.rollback()
                    failed_count += 1
                    logger.error(f"插入失败 (重复键): {row['job_title']} - {str(e)}")
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"插入失败: {row['job_title']} - {str(e)}")
            
            self.db.commit()
            
            result = {
                "inserted": inserted_count,
                "duplicated": duplicated_count,
                "failed": failed_count,
                "total": len(cleaned_df)
            }
            
            logger.info(f"幂等导入完成: {result}")
            return result
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"幂等导入出错: {str(e)}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == '__main__':
    # 测试
    sample_data = [
        {
            'job_title': 'Python开发工程师',
            'company': '字节跳动',
            'city': '北京',
            'salary_min': 25000,
            'salary_max': 45000,
            'required_skills': ['Python', 'FastAPI'],
        }
    ]
    
    transformer = DataTransformer()
    df_clean = transformer.clean_and_validate(sample_data)
    print(df_clean)
