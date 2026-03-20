from tortoise import fields, models

class MeasuringPoint(models.Model):
    id = fields.IntField(pk=True)
    SensorCode = fields.CharField(max_length=50, description="测点编号")
    SensorTypeName = fields.CharField(max_length=50, description="测点类型")
    MaxTime = fields.DateField(null=True, description="最后观测时间")
    SiteName = fields.CharField(max_length=100, null=True, description="工程部位")

    class Meta:
        table = "measuring-points"

class SeepageDataRecord(models.Model):
    id = fields.IntField(pk=True)
    # 建立外键关联
    point = fields.ForeignKeyField('models.MeasuringPoint', related_name='records', on_delete=fields.CASCADE)
    time = fields.DatetimeField(description="观测时间")
    obs_temp = fields.FloatField(null=True, description="观测温度")
    modulus = fields.FloatField(null=True, description="模数")
    calc_temp = fields.FloatField(null=True, description="计算温度")
    pressure = fields.FloatField(null=True, description="渗压")
    water_level = fields.FloatField(null=True, description="水位高程")

    class Meta:
        table = "seepage_data_records"
        ordering = ["-time"]