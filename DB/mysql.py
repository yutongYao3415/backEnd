from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise


DB_ORM_CONFIG = {
    "connections":{
        "monitordata":{
            "engine":'tortoise.backends.mysql',
            "credentials":
            {
                "host":"localhost",
                "port":"3306",
                "user":"root",
                "password":"18326554042",
                "database":"monitordata"
            }
        }
    },
    "apps":{
        "models":{
            "models":["models"],
            "default_connection":"monitordata"
        }
    },
    'use_tz':False,
}
def register_db(app:FastAPI):
    register_tortoise(
        app=app,
        config=DB_ORM_CONFIG,
        generate_schemas=False,
    )