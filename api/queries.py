from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from database.models import Jobs, ImportLog, RawRecords
from typing import List, Dict, Any, Optional
import json
from loguru import logger

# ========================
# 职位查询
# ========================

def get_jobs_filter(
    db: Session,
    city: Optional[str] = None,
    min_salary: Optional[int] = None,
    max_salary: Optional[int] = None,
    skill: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    筛选职位 - 支持多维度过滤
    返回格式: {"items": [...], "total": 100, "page": 1, "page_size": 20}
    """
    query = db.query(Jobs).filter(Jobs.is_duplicate == 0)  # 排除重复记录
    
    # 应用过滤条件
    if city:
        query = query.filter(Jobs.city == city)
    
    if min_salary:
        query = query.filter(Jobs.salary_min >= min_salary)
    
    if max_salary:
        query = query.filter(Jobs.salary_max <= max_salary)
    
    if skill:
        # 技能在JSON数组中
        query = query.filter(Jobs.required_skills.like(f'%{skill}%'))
    
    # 计算总数
    total = query.count()
    
    # 分页
    skip = (page - 1) * page_size
    jobs = query.offset(skip).limit(page_size).all()
    
    # 格式化结果
    items = [
        {
            "job_id": job.job_id,
            "title": job.job_title,
            "company": job.company,
            "city": job.city,
            "salary_range": f"{job.salary_min or '未知'}-{job.salary_max or '未知'}",
            "skills": json.loads(job.required_skills or '[]'),
            "quality_score": job.data_quality_score,
            "trace_url": f"/api/raw/{job.raw_id}",  # 追溯链接
            "log_url": f"/api/import-log/{job.log_id}"  # 数据来源链接
        }
        for job in jobs
    ]
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }

def get_job_by_id(db: Session, job_id: int) -> Optional[Dict[str, Any]]:
    """获取单个职位详情"""
    job = db.query(Jobs).filter(Jobs.job_id == job_id).first()
    
    if not job:
        return None
    
    # 获取原始记录和采集日志
    raw_record = db.query(RawRecords).filter(RawRecords.raw_id == job.raw_id).first()
    import_log = db.query(ImportLog).filter(ImportLog.log_id == job.log_id).first()
    
    return {
        "job_id": job.job_id,
        "title": job.job_title,
        "company": job.company,
        "city": job.city,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "skills": json.loads(job.required_skills or '[]'),
        "description": job.job_description,
        "quality_score": job.data_quality_score,
        "missing_fields": json.loads(job.missing_fields or '[]'),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        # 追溯信息
        "raw_record": json.loads(raw_record.original_data) if raw_record else None,
        "import_log": {
            "log_id": import_log.log_id,
            "source_url": import_log.source_url,
            "import_time": import_log.import_time.isoformat() if import_log.import_time else None,
            "batch_id": import_log.batch_id
        } if import_log else None
    }

# ========================
# 数据分析查询
# ========================

def get_salary_by_city(db: Session) -> List[Dict[str, Any]]:
    """
    按城市统计薪资水平
    返回: [{"city": "北京", "avg_salary": 35000, "count": 50, "drill_url": "..."}]
    """
    results = db.query(
        Jobs.city,
        func.avg((Jobs.salary_max + Jobs.salary_min) / 2).label("avg_salary"),
        func.count().label("count")
    ).filter(
        Jobs.is_duplicate == 0,
        Jobs.salary_min.isnot(None),
        Jobs.salary_max.isnot(None)
    ).group_by(Jobs.city).order_by(desc("avg_salary")).all()
    
    return [
        {
            "city": r.city or "未知",
            "avg_salary": round(float(r.avg_salary), 0) if r.avg_salary else 0,
            "count": r.count,
            "drill_url": f"/api/jobs/filter?city={r.city}"  # 钻取链接
        }
        for r in results
    ]

def get_skills_ranking(db: Session) -> List[Dict[str, Any]]:
    """
    技能需求排行 - 统计出现频率最高的技能
    返回: [{"skill": "Python", "count": 150, "drill_url": "..."}]
    """
    jobs = db.query(Jobs.required_skills).filter(
        Jobs.is_duplicate == 0,
        Jobs.required_skills.isnot(None)
    ).all()
    
    skill_counter = {}
    for job_tuple in jobs:
        skills = json.loads(job_tuple[0] or '[]')
        for skill in skills:
            skill = skill.strip()
            skill_counter[skill] = skill_counter.get(skill, 0) + 1
    
    # 排序并返回前20个
    sorted_skills = sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return [
        {
            "skill": skill,
            "count": count,
            "drill_url": f"/api/jobs/filter?skill={skill}"  # 钻取链接
        }
        for skill, count in sorted_skills
    ]

def get_jobs_by_region(db: Session) -> List[Dict[str, Any]]:
    """
    地区职位分布 - 按城市统计职位数量
    返回: [{"region": "北京", "count": 120, "drill_url": "..."}]
    """
    results = db.query(
        Jobs.city,
        func.count().label("count")
    ).filter(Jobs.is_duplicate == 0).group_by(Jobs.city).order_by(
        desc("count")
    ).all()
    
    return [
        {
            "region": r.city or "未知",
            "count": r.count,
            "drill_url": f"/api/jobs/filter?city={r.city}"  # 钻取链接
        }
        for r in results
    ]

# ========================
# 数据追溯
# ========================

def get_raw_record(db: Session, raw_id: int) -> Optional[Dict[str, Any]]:
    """
    获取原始记录 - 显示采集时的完整原始数据
    """
    record = db.query(RawRecords).filter(RawRecords.raw_id == raw_id).first()
    
    if not record:
        return None
    
    return {
        "raw_id": record.raw_id,
        "log_id": record.log_id,
        "original_data": json.loads(record.original_data),
        "extracted_at": record.extracted_at.isoformat() if record.extracted_at else None
    }

def get_import_log(db: Session, log_id: int) -> Optional[Dict[str, Any]]:
    """
    获取采集日志 - 显示数据来源和导入时的详细信息
    """
    log = db.query(ImportLog).filter(ImportLog.log_id == log_id).first()
    
    if not log:
        return None
    
    return {
        "log_id": log.log_id,
        "source_url": log.source_url,
        "batch_id": log.batch_id,
        "import_time": log.import_time.isoformat() if log.import_time else None,
        "status": log.status,
        "record_count": log.record_count,
        "raw_summary": json.loads(log.raw_summary or '[]')[:5],  # 前5条摘要
        "failure_reason": log.failure_reason
    }
