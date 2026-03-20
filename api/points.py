"""
测点数据管理接口
包含测点列表、详情、数据记录查询、图表数据等功能
"""

import json
import io
import pandas as pd
from typing import List
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from models import SeepageDataRecord, MeasuringPoint
from schemas import ResponseBase

# 创建路由器，设置前缀
router = APIRouter()


# ==================== 测点管理接口 ====================

@router.get("/measuring-points", response_model=ResponseBase)
async def get_points(
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(20, ge=1, le=100, description="每页数量"),
    siteName: str = Query(None, description="工程部位过滤"),
    sensorTypeName: str = Query(None, description="测点类型过滤"),
    sensorCode: str = Query(None, description="测点编号模糊查询")
):
    """
    获取测点列表（分页）
    
    参数说明：
    - page: 页码，从1开始
    - pageSize: 每页显示数量，最大100
    - siteName: 可选，按工程部位筛选
    - sensorTypeName: 可选，按测点类型筛选
    - sensorCode: 可选，按测点编号模糊查询
    
    返回：
    - list: 测点数据列表
    - total: 总记录数
    - page: 当前页码
    - pageSize: 每页数量
    - totalPages: 总页数
    """
    # 构建基础查询
    query = MeasuringPoint.all()
    
    # 应用过滤条件
    if siteName:
        query = query.filter(SiteName=siteName)
    if sensorTypeName:
        query = query.filter(SensorTypeName=sensorTypeName)
    if sensorCode:
        query = query.filter(SensorCode__icontains=sensorCode)
    
    # 获取总数
    total = await query.count()
    
    # 分页查询并按最后观测时间降序排序
    list_data = await query.limit(pageSize).offset((page - 1) * pageSize).order_by("-MaxTime")
    
    # 计算总页数
    total_pages = (total + pageSize - 1) // pageSize
    
    return {
        "success": True,
        "data": {
            "list": list_data,
            "total": total,
            "page": page,
            "pageSize": pageSize,
            "totalPages": total_pages
        }
    }


@router.get("/measuring-points/{id}", response_model=ResponseBase)
async def get_point_detail(id: int):
    """
    获取测点详细信息
    
    参数说明：
    - id: 测点ID
    
    返回：
    - point: 测点基本信息
    - stats: 统计信息（总记录数、最新记录）
    """
    # 查询测点基本信息
    point = await MeasuringPoint.get_or_none(id=id)
    if not point:
        return {"success": False, "message": "未找到该测点"}
    
    # 查询该测点的最新一条数据记录
    last_record = await SeepageDataRecord.filter(
        point_id=id
    ).order_by("-time").first()
    
    # 统计该测点的总记录数
    total_count = await SeepageDataRecord.filter(point_id=id).count()
    
    return {
        "success": True,
        "data": {
            "point": point,
            "stats": {
                "totalRecords": total_count,
                "lastRecord": last_record
            }
        }
    }


# ==================== 数据记录查询接口 ====================

@router.get("/monitoring-data", response_model=ResponseBase)
async def get_monitoring_data(
    pointId: int = Query(..., description="测点ID"),
    startDate: str = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    endDate: str = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(50, ge=1, le=200, description="每页数量"),
    sortBy: str = Query("time", description="排序字段"),
    sortOrder: str = Query("desc", description="排序方向：asc升序/desc降序")
):
    """
    获取测点的监测数据记录（分页）
    
    参数说明：
    - pointId: 必填，测点ID
    - startDate: 可选，查询起始日期
    - endDate: 可选，查询结束日期
    - page: 页码
    - pageSize: 每页数量
    - sortBy: 排序字段（默认按时间排序）
    - sortOrder: 排序方向（默认降序）
    
    返回：
    - list: 数据记录列表
    - total: 总记录数
    - page: 当前页码
    - pageSize: 每页数量
    """
    # 构建查询
    query = SeepageDataRecord.filter(point_id=pointId)
    
    # 应用日期范围过滤
    if startDate:
        query = query.filter(time__gte=startDate)
    if endDate:
        query = query.filter(time__lte=endDate)
    
    # 确定排序方式
    order = f"-{sortBy}" if sortOrder == "desc" else sortBy
    
    # 获取总数
    total = await query.count()
    
    # 分页查询
    list_data = await query.order_by(order).limit(pageSize).offset((page - 1) * pageSize)
    
    return {
        "success": True,
        "data": {
            "list": list_data,
            "total": total,
            "page": page,
            "pageSize": pageSize
        }
    }


# ==================== 图表数据接口 ====================

@router.get("/monitoring-data/chart")
async def get_chart_data(
    pointId: int = Query(..., description="测点ID"),
    startDate: str = Query(..., description="开始日期"),
    endDate: str = Query(..., description="结束日期"),
    series: str = Query(..., description="图表系列配置（JSON字符串）")
):
    """
    获取图表数据（监测过程线）
    
    参数说明：
    - pointId: 测点ID
    - startDate: 开始日期
    - endDate: 结束日期
    - series: 图表系列配置，JSON格式字符串
      示例：[{"type":"pressure","name":"渗压","color":"#ff0000"}]
    
    返回：
    - chartTitle: 图表标题
    - xAxis: X轴数据（日期）
    - series: 图表系列数据
    """
    # 解析图表系列配置
    series_config = json.loads(series)
    
    # 查询指定时间范围内的数据，按时间升序排序
    records = await SeepageDataRecord.filter(
        point_id=pointId,
        time__range=[startDate, endDate]
    ).order_by("time")
    
    # 字段映射：前端字段名 -> 数据库字段名
    field_map = {
        "calcTemp": "calc_temp",
        "obsTemp": "obs_temp",
        "pressure": "pressure",
        "waterLevel": "water_level"
    }
    
    # 构建图表系列数据
    chart_series = []
    for s in series_config:
        db_field = field_map.get(s['type'])
        if db_field:
            chart_series.append({
                "name": s['name'],
                "type": s['type'],
                "color": s.get('color'),
                "data": [getattr(r, db_field) for r in records]
            })
    
    return {
        "success": True,
        "data": {
            "chartTitle": "监测过程线",
            "xAxis": [r.time.strftime("%Y-%m-%d") for r in records],
            "series": chart_series
        }
    }


# ==================== 数据统计接口 ====================

@router.get("/monitoring-data/status")
async def get_data_status(pointId: int = Query(None, description="测点ID，不传则统计全部")):
    """
    获取数据状态统计信息
    
    参数说明：
    - pointId: 可选，指定测点ID，不传则统计所有测点的数据
    
    返回：
    - totalRecords: 总记录数
    """
    # 构建查询
    query = SeepageDataRecord.all()
    
    # 如果指定了测点ID，则过滤
    if pointId:
        query = query.filter(point_id=pointId)
    
    # 统计总数
    total_count = await query.count()
    
    return {
        "success": True,
        "data": {
            "totalRecords": total_count
        }
    }


# ==================== 字典接口 ====================

@router.get("/dictionaries/{category}")
async def get_dicts(category: str):
    """
    获取字典数据（用于下拉选项）
    
    参数说明：
    - category: 字典类型
      - sensor-types: 测点类型
      - site-names: 工程部位
    
    返回：
    - 字典列表，每个项包含 value 和 label
    """
    # 映射分类到数据库字段
    field_map = {
        "sensor-types": "SensorTypeName",
        "site-names": "SiteName"
    }
    
    # 验证分类是否有效
    if category not in field_map:
        raise HTTPException(status_code=404, detail="无效的字典类型")
    
    # 获取不重复的字段值
    field_name = field_map[category]
    values = await MeasuringPoint.all().distinct().values_list(field_name, flat=True)
    
    # 转换为字典格式
    return {
        "success": True,
        "data": [
            {"value": v, "label": v} 
            for v in values 
            if v  # 过滤空值
        ]
    }


# ==================== 数据管理接口 ====================

@router.post("/monitoring-data")
async def add_record(data: dict):
    """
    添加数据记录
    
    参数说明：
    - data: 数据记录对象，包含字段：
      - point_id: 测点ID（必填）
      - time: 观测时间（必填）
      - obs_temp: 观测温度（可选）
      - modulus: 模数（可选）
      - calc_temp: 计算温度（可选）
      - pressure: 渗压（可选）
      - water_level: 水位高程（可选）
    
    返回：
    - 新创建记录的ID
    """
    new_rec = await SeepageDataRecord.create(**data)
    return {
        "success": True,
        "data": {"id": new_rec.id},
        "message": "添加成功"
    }


@router.put("/monitoring-data/{id}")
async def update_record(id: int, data: dict):
    """
    更新数据记录
    
    参数说明：
    - id: 记录ID
    - data: 要更新的字段对象
    
    返回：
    - 成功消息
    """
    await SeepageDataRecord.filter(id=id).update(**data)
    return {"success": True, "message": "更新成功"}


@router.delete("/monitoring-data/{id}")
async def delete_record(id: int):
    """
    删除单条数据记录
    
    参数说明：
    - id: 记录ID
    
    返回：
    - 成功消息
    """
    await SeepageDataRecord.filter(id=id).delete()
    return {"success": True, "message": "删除成功"}


@router.delete("/monitoring-data/batch")
async def batch_delete(ids: List[int]):
    """
    批量删除数据记录
    
    参数说明：
    - ids: 记录ID列表
    
    返回：
    - 成功消息
    """
    await SeepageDataRecord.filter(id__in=ids).delete()
    return {"success": True, "message": f"成功删除 {len(ids)} 条记录"}


# ==================== 数据导入导出接口 ====================

@router.get("/monitoring-data/export")
async def export_data(
    pointId: int = Query(..., description="测点ID"),
    startDate: str = Query(None, description="开始日期"),
    endDate: str = Query(None, description="结束日期")
):
    """
    导出数据记录为Excel文件
    
    参数说明：
    - pointId: 测点ID
    - startDate: 可选，开始日期
    - endDate: 可选，结束日期
    
    返回：
    - Excel文件流，可直接下载
    """
    # 构建查询
    query = SeepageDataRecord.filter(point_id=pointId)
    
    # 应用日期过滤
    if startDate:
        query = query.filter(time__gte=startDate)
    if endDate:
        query = query.filter(time__lte=endDate)
    
    # 获取数据
    records = await query.values()
    
    # 转换为DataFrame
    df = pd.DataFrame(records)
    
    # 创建Excel输出流
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='监测数据')
    
    # 定位到流的开头
    output.seek(0)
    
    # 返回文件流
    return StreamingResponse(
        output,
        media_type="application/vnd.ms-excel",
        headers={
            "Content-Disposition": "attachment; filename=monitoring_data.xlsx"
        }
    )


@router.post("/monitoring-data/import")
async def import_data(file: UploadFile = File(...)):
    """
    导入Excel数据文件
    
    参数说明：
    - file: 上传的Excel文件
    
    返回：
    - 导入结果统计
    """
    # 读取文件内容
    contents = await file.read()
    
    # 使用pandas读取Excel
    df = pd.read_excel(io.BytesIO(contents))
    
    # TODO: 这里应该实现实际的导入逻辑
    # 示例：将DataFrame中的数据批量插入数据库
    # for _, row in df.iterrows():
    #     await SeepageDataRecord.create(**row.to_dict())
    
    return {
        "success": True,
        "data": {
            "successCount": len(df),
            "message": f"成功导入 {len(df)} 条记录（模拟数据）"
        }
    }