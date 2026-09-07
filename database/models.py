from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey, UniqueConstraint, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from datetime import datetime
import enum

class ImportLog(Base):
    """采集日志表 - 记录每次数据导入的信息"""
    __tablename__ = 'import_log'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(500), nullable=True, comment='数据源URL')
    import_time = Column(DateTime, default=datetime.now, comment='导入时间')
    batch_id = Column(String(50), unique=True, nullable=False, comment='批次ID - 同一批数据的唯一标识')
    status = Column(
        Enum('success', 'partial', 'failed', name='import_status'),
        default='success',
        comment='导入状态'
    )
    record_count = Column(Integer, default=0, comment='成功导入记录数')
    raw_summary = Column(JSON, nullable=True, comment='原始响应摘要（前100条）')
    failure_reason = Column(Text, nullable=True, comment='失败原因')
    
    # 关系
    raw_records = relationship('RawRecords', back_populates='import_log', cascade='all, delete-orphan')
    jobs = relationship('Jobs', back_populates='import_log')
    
    # 索引
    __table_args__ = (
        Index('idx_batch_id', 'batch_id'),
        Index('idx_import_time', 'import_time'),
        {'comment': '采集日志表'}
    )
    
    def __repr__(self):
        return f"<ImportLog(log_id={self.log_id}, batch_id={self.batch_id}, status={self.status})>"

class RawRecords(Base):
    """原始记录表 - 保存完整的原始数据"""
    __tablename__ = 'raw_records'
    
    raw_id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey('import_log.log_id', ondelete='CASCADE'), nullable=False)
    original_data = Column(JSON, nullable=False, comment='完整原始数据JSON')
    extracted_at = Column(DateTime, default=datetime.now, comment='提取时间')
    
    # 关系
    import_log = relationship('ImportLog', back_populates='raw_records')
    jobs = relationship('Jobs', back_populates='raw_record')
    
    # 索引
    __table_args__ = (
        Index('idx_log_id', 'log_id'),
        {'comment': '原始记录表'}
    )
    
    def __repr__(self):
        return f"<RawRecords(raw_id={self.raw_id}, log_id={self.log_id})>"

class Jobs(Base):
    """规范化岗位表 - 清洗后的业务数据"""
    __tablename__ = 'jobs'
    
    job_id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey('import_log.log_id', ondelete='CASCADE'), nullable=False, comment='所属导入批次')
    raw_id = Column(Integer, ForeignKey('raw_records.raw_id', ondelete='SET NULL'), nullable=True, comment='原始记录ID')
    
    # 核心字段
    job_title = Column(String(100), nullable=False, comment='职位名称')
    company = Column(String(100), nullable=True, comment='公司名称')
    city = Column(String(50), nullable=True, comment='工作地点')
    salary_min = Column(Integer, nullable=True, comment='最低薪资')
    salary_max = Column(Integer, nullable=True, comment='最高薪资')
    required_skills = Column(JSON, nullable=True, comment='所需技能JSON数组')
    job_description = Column(Text, nullable=True, comment='职位描述')
    
    # 数据质量字段
    is_duplicate = Column(Integer, default=0, comment='是否重复记录 (0-否, 1-是)')
    data_quality_score = Column(Float, default=100.0, comment='数据质量评分 (0-100)')
    missing_fields = Column(JSON, nullable=True, comment='缺失字段列表')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    # 关系
    import_log = relationship('ImportLog', back_populates='jobs')
    raw_record = relationship('RawRecords', back_populates='jobs')
    
    # 约束与索引
    __table_args__ = (
        # 唯一键：同一批次内相同的职位和公司视为重复
        UniqueConstraint('log_id', 'job_title', 'company', name='uq_log_title_company'),
        # 业务查询索引
        Index('idx_city', 'city'),
        Index('idx_salary_range', 'salary_min', 'salary_max'),
        Index('idx_log_id', 'log_id'),
        Index('idx_raw_id', 'raw_id'),
        Index('idx_is_duplicate', 'is_duplicate'),
        Index('idx_data_quality', 'data_quality_score'),
        Index('idx_created_at', 'created_at'),
        {'comment': '规范化岗位表', 'charset': 'utf8mb4'}
    )
    
    def __repr__(self):
        return f"<Jobs(job_id={self.job_id}, title={self.job_title}, city={self.city})>"
