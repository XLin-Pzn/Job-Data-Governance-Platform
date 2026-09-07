from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database.connection import get_db, init_db
from api.queries import (
    get_jobs_filter,
    get_job_by_id,
    get_salary_by_city,
    get_skills_ranking,
    get_jobs_by_region,
    get_raw_record,
    get_import_log
)
from loguru import logger
import os

logger.add(
    "logs/api.log",
    format="{time} | {level} | {message}",
    level="INFO"
)

# 创建FastAPI应用
app = FastAPI(
    title="招聘岗位数据治理平台",
    description="全链路数据采集、ETL、入库、查询和可视化分析平台",
    version="1.0.0"
)

# 初始化数据库
@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    try:
        init_db()
        logger.info("✓ 数据库初始化成功")
    except Exception as e:
        logger.error(f"✗ 数据库初始化失败: {e}")

# 挂载静态文件
if os.path.exists('static'):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ========================
# 首页 & 文档
# ========================

@app.get("/", response_class=HTMLResponse)
async def root():
    """首页仪表板"""
    return open('templates/index.html', encoding='utf-8').read()

@app.get("/docs", include_in_schema=False)
async def custom_swagger():
    """自定义Swagger文档"""
    return FileResponse('templates/swagger.html')

# ========================
# 职位查询API
# ========================

@app.get("/api/jobs/filter")
async def filter_jobs(
    city: str = Query(None, description="工作地点"),
    min_salary: int = Query(None, description="最低薪资"),
    max_salary: int = Query(None, description="最高薪资"),
    skill: str = Query(None, description="所需技能"),
    page: int = Query(1, ge=1, description="分页页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    db: Session = Depends(get_db)
):
    """筛选职位 - 支持多维度过滤和分页"""
    try:
        result = get_jobs_filter(
            db=db,
            city=city,
            min_salary=min_salary,
            max_salary=max_salary,
            skill=skill,
            page=page,
            page_size=page_size
        )
        logger.info(f"✓ 职位筛选: city={city}, salary={min_salary}-{max_salary}, 返回 {len(result['items'])} 条记录")
        return result
    except Exception as e:
        logger.error(f"✗ 职位筛选失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_details(
    job_id: int,
    db: Session = Depends(get_db)
):
    """获取职位详情"""
    try:
        job = get_job_by_id(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="职位不存在")
        logger.info(f"✓ 获取职位详情: job_id={job_id}")
        return job
    except Exception as e:
        logger.error(f"✗ 获取职位详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# 数据分析API
# ========================

@app.get("/api/analytics/salary-by-city")
async def analytics_salary_by_city(
    db: Session = Depends(get_db)
):
    """分析1：按城市统计薪资水平（可追溯到职位列表）"""
    try:
        result = get_salary_by_city(db)
        logger.info(f"✓ 城市薪资分析: 返回 {len(result)} 个城市数据")
        return {"data": result, "chart_type": "bar"}
    except Exception as e:
        logger.error(f"✗ 城市薪资分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/skills-ranking")
async def analytics_skills_ranking(
    db: Session = Depends(get_db)
):
    """分析2：技能需求排行（可追溯到职位列表）"""
    try:
        result = get_skills_ranking(db)
        logger.info(f"✓ 技能排行分析: 返回 {len(result)} 个技能")
        return {"data": result, "chart_type": "bar"}
    except Exception as e:
        logger.error(f"✗ 技能排行分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/jobs-by-region")
async def analytics_jobs_by_region(
    db: Session = Depends(get_db)
):
    """分析3：地区职位分布（可追溯到职位列表）"""
    try:
        result = get_jobs_by_region(db)
        logger.info(f"✓ 地区分布分析: 返回 {len(result)} 个地区")
        return {"data": result, "chart_type": "pie"}
    except Exception as e:
        logger.error(f"✗ 地区分布分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# 数据追溯API
# ========================

@app.get("/api/raw/{raw_id}")
async def get_raw_data(
    raw_id: int,
    db: Session = Depends(get_db)
):
    """追溯原始记录 - 查看采集时的原始数据"""
    try:
        result = get_raw_record(db, raw_id)
        if not result:
            raise HTTPException(status_code=404, detail="原始记录不存在")
        logger.info(f"✓ 获取原始记录: raw_id={raw_id}")
        return result
    except Exception as e:
        logger.error(f"✗ 获取原始记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/import-log/{log_id}")
async def get_import_log_data(
    log_id: int,
    db: Session = Depends(get_db)
):
    """追溯采集日志 - 查看数据来源和采集时间"""
    try:
        result = get_import_log(db, log_id)
        if not result:
            raise HTTPException(status_code=404, detail="采集日志不存在")
        logger.info(f"✓ 获取采集日志: log_id={log_id}")
        return result
    except Exception as e:
        logger.error(f"✗ 获取采集日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# 统计API
# ========================

@app.get("/api/stats/overview")
async def get_stats_overview(
    db: Session = Depends(get_db)
):
    """获取数据概览统计"""
    try:
        from database.models import Jobs, ImportLog
        
        total_jobs = db.query(Jobs).count()
        total_imports = db.query(ImportLog).count()
        avg_quality = db.query(Jobs).filter(Jobs.data_quality_score > 0).count()
        
        if total_jobs > 0:
            avg_quality = db.query(Jobs.data_quality_score).filter(
                Jobs.data_quality_score > 0
            ).count() / total_jobs * 100
        
        logger.info(f"✓ 数据概览: 总职位数={total_jobs}, 总导入次数={total_imports}")
        return {
            "total_jobs": total_jobs,
            "total_imports": total_imports,
            "avg_quality_score": round(avg_quality, 2)
        }
    except Exception as e:
        logger.error(f"✗ 获取数据概览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# 健康检查
# ========================

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "Job Data Governance Platform"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
