import os
from .tool_registry import tool
from datetime import date as Date
from datetime import timedelta
from typing import Any

import requests


AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

def get_amap_key() -> str:
    """从环境变量中读取高德 API Key。"""
    amap_key = os.getenv("GDMAP_KEY")

    if not amap_key:
        raise RuntimeError("Missing GDMAP_KEY in .env.")

    return amap_key


def normalize_date(value: str) -> str:
    """把模型容易输出的 today/tomorrow 转成天气 API 使用的 YYYY-MM-DD 日期。"""
    today = Date.today()

    if value == "today":
        return today.isoformat()

    if value == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    return value


def resolve_city_code(location: str) -> str:
    """当前直接把城市名传给高德；后续可替换为地理编码 API 获取 adcode。"""
    return location


def weather_suggests_umbrella(day_weather: str, night_weather: str) -> bool:
    """根据高德返回的白天/夜间天气文本，粗略判断是否建议带伞。"""
    text = f"{day_weather}{night_weather}"
    return any(keyword in text for keyword in ["\u96e8", "\u96ea", "\u96f7", "\u9635\u96e8"])

@tool(
    name="get_weather",
    description="查询指定地点在指定日期的天气预报。",
    input_schema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "城市或地点名称，例如：上海、北京、杭州。"
            },
            "date": {
                "type": "string",
                "description": "查询日期，today、tomorrow 或 YYYY-MM-DD。"
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "温度单位。中国用户默认使用 celsius。"
            }
        },
        "required": ["location", "date"],
        "additionalProperties": False
    },
    risk="low",
)
def get_weather(location: str, date: str, unit: str = "celsius") -> dict[str, Any]:
    """查询高德天气预报，并返回 Agent 更容易理解的结构化天气数据。"""
    target_date = normalize_date(date)

    params = {
        "key": get_amap_key(),
        "city": resolve_city_code(location),
        "extensions": "all",
        "output": "JSON"
    }

    response = requests.get(AMAP_WEATHER_URL, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if data.get("status") != "1":
        raise RuntimeError(data.get("info", "Amap weather API call failed."))

    forecasts = data.get("forecasts") or []

    if not forecasts:
        raise RuntimeError("Amap weather API returned no forecast data.")

    casts = forecasts[0].get("casts") or []

    if not casts:
        raise RuntimeError("Amap weather API returned no casts data.")

    matched_cast = None

    for item in casts:
        if item.get("date") == target_date:
            matched_cast = item
            break

    if matched_cast is None:
        available_dates = [item.get("date") for item in casts]
        raise ValueError(
            f"Date is outside Amap forecast range: {target_date}. "
            f"Available dates: {available_dates}"
        )

    day_weather = matched_cast.get("dayweather", "")
    night_weather = matched_cast.get("nightweather", "")

    return {
        "location": location,
        "adcode": forecasts[0].get("adcode"),
        "province": forecasts[0].get("province"),
        "city": forecasts[0].get("city"),
        "date": matched_cast.get("date"),
        "week": matched_cast.get("week"),
        "unit": unit,
        "day_weather": day_weather,
        "night_weather": night_weather,
        "temperature_min": matched_cast.get("nighttemp"),
        "temperature_max": matched_cast.get("daytemp"),
        "day_wind": matched_cast.get("daywind"),
        "night_wind": matched_cast.get("nightwind"),
        "day_power": matched_cast.get("daypower"),
        "night_power": matched_cast.get("nightpower"),
        "should_bring_umbrella": weather_suggests_umbrella(day_weather, night_weather),
        "source": "amap"
    }

#0524及以后已经通过工具注册可以直接调用get_weather，不需要run_tool了
def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """校验工具参数，并根据工具名分发到对应的本地函数。"""
    if name != "get_weather":
        raise ValueError(f"Unknown tool: {name}")

    location = arguments.get("location")
    date = arguments.get("date")
    unit = arguments.get("unit", "celsius")

    if not isinstance(location, str) or not location.strip():
        raise ValueError("get_weather.location must be a non-empty string.")

    if not isinstance(date, str) or not date.strip():
        raise ValueError("get_weather.date must be a non-empty string.")

    if unit not in ["celsius", "fahrenheit"]:
        raise ValueError("get_weather.unit must be celsius or fahrenheit.")

    return get_weather(location=location, date=date, unit=unit)
