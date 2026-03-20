from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import date, datetime

class ResponseBase(BaseModel):
    """统一响应格式"""
    success: bool = True
    message: Optional[str] = "Success"
    data: Any = None

# 测点相关
class PointSchema(BaseModel):
    """测点数据模式 - 用于API响应"""
    id: int
    SensorCode: str = Field(..., description="测点编号")
    SensorTypeName: str = Field(..., description="测点类型")
    MaxTime: Optional[date] = Field(None, description="最后观测时间")
    SiteName: Optional[str] = Field(None, description="工程部位")

# 数据记录相关
class RecordSchema(BaseModel):
    """渗压数据记录模式 - 用于API响应"""
    id: int
    pointId: int = Field(..., alias="point_id", description="关联测点ID")
    time: datetime = Field(..., description="观测时间")
    obsTemp: Optional[float] = Field(None, alias="obs_temp", description="观测温度")
    modulus: Optional[float] = Field(None, description="模数")
    calcTemp: Optional[float] = Field(None, alias="calc_temp", description="计算温度")
    pressure: Optional[float] = Field(None, description="渗压")
    waterLevel: Optional[float] = Field(None, alias="water_level", description="水位高程")
    
    class Config:
        allow_population_by_field_name = True

class ChartSeriesItem(BaseModel):
    """图表数据项"""
    type: str
    name: str
    color: Optional[str]
