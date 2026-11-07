"""Real system clock/date and live networked weather context for KurisuAgent."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
import re
import time
from typing import Any, Dict, Optional, Tuple
import urllib.parse
import urllib.request

_WEEKDAYS_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

_WMO_WEATHER_CN: Dict[int, str] = {
    0: "晴朗",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴天",
    45: "有雾",
    48: "雾凇",
    51: "小雨",
    53: "小雨",
    55: "小雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "强雷阵雨伴冰雹",
}

# Built-in coordinates for major Chinese and international cities to avoid an extra geocoding roundtrip
CITY_COORDS: Dict[str, Tuple[float, float, str]] = {
    "北京": (39.9042, 116.4074, "Asia/Shanghai"),
    "上海": (31.2304, 121.4737, "Asia/Shanghai"),
    "广州": (23.1291, 113.2644, "Asia/Shanghai"),
    "深圳": (22.5431, 114.0579, "Asia/Shanghai"),
    "杭州": (30.2741, 120.1551, "Asia/Shanghai"),
    "南京": (32.0603, 118.7969, "Asia/Shanghai"),
    "成都": (30.5728, 104.0668, "Asia/Shanghai"),
    "重庆": (29.5630, 106.5516, "Asia/Shanghai"),
    "武汉": (30.5928, 114.3055, "Asia/Shanghai"),
    "西安": (34.3416, 108.9398, "Asia/Shanghai"),
    "天津": (39.0842, 117.2009, "Asia/Shanghai"),
    "苏州": (31.2989, 120.5853, "Asia/Shanghai"),
    "长沙": (28.2282, 112.9388, "Asia/Shanghai"),
    "郑州": (34.7466, 113.6253, "Asia/Shanghai"),
    "青岛": (36.0671, 120.3826, "Asia/Shanghai"),
    "沈阳": (41.8057, 123.4315, "Asia/Shanghai"),
    "大连": (38.9140, 121.6147, "Asia/Shanghai"),
    "厦门": (24.4798, 118.0894, "Asia/Shanghai"),
    "福州": (26.0745, 119.2965, "Asia/Shanghai"),
    "济南": (36.6512, 117.1201, "Asia/Shanghai"),
    "合肥": (31.8206, 117.2272, "Asia/Shanghai"),
    "昆明": (25.0389, 102.7183, "Asia/Shanghai"),
    "哈尔滨": (45.8038, 126.5349, "Asia/Shanghai"),
    "长春": (43.8171, 125.3235, "Asia/Shanghai"),
    "石家庄": (38.0428, 114.5149, "Asia/Shanghai"),
    "太原": (37.8706, 112.5489, "Asia/Shanghai"),
    "南昌": (28.6820, 115.8579, "Asia/Shanghai"),
    "南宁": (22.8170, 108.3665, "Asia/Shanghai"),
    "贵阳": (26.6470, 106.6302, "Asia/Shanghai"),
    "兰州": (36.0611, 103.8343, "Asia/Shanghai"),
    "银川": (38.4872, 106.2309, "Asia/Shanghai"),
    "西宁": (36.6171, 101.7782, "Asia/Shanghai"),
    "乌鲁木齐": (43.8256, 87.6168, "Asia/Shanghai"),
    "拉萨": (29.6525, 91.1721, "Asia/Shanghai"),
    "海口": (20.0440, 110.1999, "Asia/Shanghai"),
    "三亚": (18.2528, 109.5119, "Asia/Shanghai"),
    "呼和浩特": (40.8426, 111.7492, "Asia/Shanghai"),
    "珠海": (22.2710, 113.5767, "Asia/Shanghai"),
    "佛山": (23.0215, 113.1214, "Asia/Shanghai"),
    "东莞": (23.0207, 113.7518, "Asia/Shanghai"),
    "无锡": (31.4912, 120.3119, "Asia/Shanghai"),
    "宁波": (29.8683, 121.5440, "Asia/Shanghai"),
    "温州": (27.9943, 120.6994, "Asia/Shanghai"),
    "常州": (31.8112, 119.9741, "Asia/Shanghai"),
    "徐州": (34.2044, 117.2858, "Asia/Shanghai"),
    "烟台": (37.4638, 121.4479, "Asia/Shanghai"),
    "潍坊": (36.7069, 119.1618, "Asia/Shanghai"),
    "洛阳": (34.6197, 112.4540, "Asia/Shanghai"),
    "保定": (38.8740, 115.4646, "Asia/Shanghai"),
    "唐山": (39.6309, 118.1802, "Asia/Shanghai"),
    "香港": (22.3193, 114.1694, "Asia/Hong_Kong"),
    "澳门": (22.1987, 113.5439, "Asia/Macau"),
    "台北": (25.0330, 121.5654, "Asia/Taipei"),
    "东京": (35.6762, 139.6503, "Asia/Tokyo"),
    "秋叶原": (35.6984, 139.7731, "Asia/Tokyo"),
    "大阪": (34.6937, 135.5023, "Asia/Tokyo"),
    "京都": (35.0116, 135.7681, "Asia/Tokyo"),
    "纽约": (40.7128, -74.0060, "America/New_York"),
    "伦敦": (51.5074, -0.1278, "Europe/London"),
    "巴黎": (48.8566, 2.3522, "Europe/Paris"),
}

_TIME_QUERY_RE = re.compile(
    r"(?:几点|时间|几号|日期|星期几|周几|礼拜几|今天.*(?:几号|星期|周|礼拜|日期)|明天.*(?:几号|星期|周|礼拜|日期)|现在.*点)"
)
_WEATHER_QUERY_RE = re.compile(
    r"(?:天气|气温|多少度|温度|下雨|下雪|刮风|晴天|阴天|多云|冷不冷|热不热|气象|天气预报)"
)
_NON_CITY_WORDS = frozenset({
    "今天", "明天", "后天", "现在", "目前", "当前", "外面", "室外", "窗外", "这里", "那边",
    "请问", "帮我", "查一下", "查询", "看看", "告诉我", "红莉栖", "牧濑红莉栖", "克里斯",
    "克里斯蒂娜", "助手", "今天外面", "明天外面", "现在外面",
})


def system_clock_snapshot(now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return traceable local system clock, timezone, today's date, and tomorrow's date."""
    dt = (now or datetime.now().astimezone())
    if dt.tzinfo is None:
        dt = dt.astimezone()
    tomorrow = dt + timedelta(days=1)
    utc_offset = dt.strftime("%z")
    if len(utc_offset) == 5:
        tz_label = f"UTC{utc_offset[:3]}:{utc_offset[3:]}"
    else:
        tz_label = str(dt.tzinfo or "Local")
    return {
        "iso": dt.isoformat(timespec="seconds"),
        "date": dt.strftime("%Y-%m-%d"),
        "date_cn": f"{dt.year}年{dt.month}月{dt.day}日",
        "time": dt.strftime("%H:%M:%S"),
        "time_cn": f"{dt.hour}点{dt.minute:02d}分",
        "hour": dt.hour,
        "minute": dt.minute,
        "weekday_cn": _WEEKDAYS_CN[dt.weekday()],
        "tomorrow_date": tomorrow.strftime("%Y-%m-%d"),
        "tomorrow_date_cn": f"{tomorrow.year}年{tomorrow.month}月{tomorrow.day}日",
        "tomorrow_weekday_cn": _WEEKDAYS_CN[tomorrow.weekday()],
        "timezone": tz_label,
    }


def format_clock_prompt_section(clock: Dict[str, Any]) -> str:
    return (
        "【当前真实系统时间与日期（已由本机系统时钟实时提供，询问现在几点、今天/明天几号或星期几时必须直接据此回答，严禁说无法查看时间）】：\n"
        f"- 当前本地时间：{clock['date_cn']}（{clock['weekday_cn']}）{clock['time_cn']}（{clock['date']} {clock['time']}，时区 {clock['timezone']}）\n"
        f"- 明天日期：{clock['tomorrow_date_cn']}（{clock['tomorrow_weekday_cn']}，{clock['tomorrow_date']}）"
    )


def is_time_or_date_query(text: str) -> bool:
    return bool(_TIME_QUERY_RE.search(text or ""))


def is_weather_query(text: str) -> bool:
    return bool(_WEATHER_QUERY_RE.search(text or ""))


def extract_weather_city(text: str) -> Optional[str]:
    """Extract an explicit city name from a weather query, or None if no city is specified."""
    if not text:
        return None
    cleaned = text.strip()
    for city in sorted(CITY_COORDS.keys(), key=len, reverse=True):
        if city in cleaned:
            return city
    # Match patterns like "查询杭州天气", "哈尔滨今天天气", "西安市明天多少度"
    patterns = (
        r"(?:查询|查一下|看看|请问|告诉我)?\s*([\u4e00-\u9fa5]{2,5}?)(?:市|地区)?(?:今天|明天|后天|现在|目前|当前)?的?(?:天气|气温|温度|多少度|下雨|下雪)",
        r"(?:今天|明天|后天|现在)\s*([\u4e00-\u9fa5]{2,5}?)(?:市|地区)?的?(?:天气|气温|温度|多少度)",
    )
    for pat in patterns:
        m = re.search(pat, cleaned)
        if m:
            candidate = m.group(1).strip()
            for prefix in ("请问", "查询", "看看", "帮我查", "告诉我", "今天", "明天", "现在"):
                if candidate.startswith(prefix) and len(candidate) > len(prefix) + 1:
                    candidate = candidate[len(prefix):]
            if candidate and candidate not in _NON_CITY_WORDS and len(candidate) >= 2:
                return candidate
    return None


def fetch_live_weather(
    city: str,
    timeout: float = 4.0,
    opener: Any = None,
) -> Dict[str, Any]:
    """Fetch real-time and 2-day forecast weather for city via Open-Meteo."""
    started = time.perf_counter()
    if opener is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    city_clean = city.removesuffix("市").strip()
    coords = CITY_COORDS.get(city_clean) or CITY_COORDS.get(city)
    resolved_name = city_clean
    if coords is not None:
        lat, lon, tz = coords
    else:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?"
            + urllib.parse.urlencode(
                {"name": city_clean, "count": 1, "language": "zh", "format": "json"}
            )
        )
        req = urllib.request.Request(geo_url, headers={"User-Agent": "KurisuPro/1.0"})
        with opener.open(req, timeout=timeout) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))
        results = geo_data.get("results") or []
        if not results:
            raise ValueError(f"未找到城市「{city}」的地理坐标")
        first = results[0]
        lat = float(first["latitude"])
        lon = float(first["longitude"])
        tz = first.get("timezone") or "Asia/Shanghai"
        resolved_name = first.get("name") or city_clean

    forecast_url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": tz,
                "forecast_days": 2,
            }
        )
    )
    req = urllib.request.Request(forecast_url, headers={"User-Agent": "KurisuPro/1.0"})
    with opener.open(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current") or {}
    daily = data.get("daily") or {}
    cur_code = int(current.get("weather_code", 0))
    cur_desc = _WMO_WEATHER_CN.get(cur_code, "多云")
    cur_temp = round(float(current.get("temperature_2m", 0.0)))
    humidity = int(round(float(current.get("relative_humidity_2m", 0))))
    wind_kmh = round(float(current.get("wind_speed_10m", 0.0)))
    observed_at = str(current.get("time") or "")

    daily_dates = daily.get("time") or []
    daily_codes = daily.get("weather_code") or []
    daily_max = daily.get("temperature_2m_max") or []
    daily_min = daily.get("temperature_2m_min") or []

    today_max = round(float(daily_max[0])) if len(daily_max) >= 1 else cur_temp
    today_min = round(float(daily_min[0])) if len(daily_min) >= 1 else cur_temp
    today_desc = _WMO_WEATHER_CN.get(int(daily_codes[0]), cur_desc) if len(daily_codes) >= 1 else cur_desc

    tomorrow_date = str(daily_dates[1]) if len(daily_dates) >= 2 else ""
    tomorrow_desc = _WMO_WEATHER_CN.get(int(daily_codes[1]), "多云") if len(daily_codes) >= 2 else today_desc
    tomorrow_max = round(float(daily_max[1])) if len(daily_max) >= 2 else today_max
    tomorrow_min = round(float(daily_min[1])) if len(daily_min) >= 2 else today_min

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "status": "ok",
        "provider": "open-meteo",
        "city": resolved_name,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "observed_at": observed_at,
        "temperature_c": cur_temp,
        "weather_desc": cur_desc,
        "humidity_pct": humidity,
        "wind_kmh": wind_kmh,
        "today_desc": today_desc,
        "today_max_c": today_max,
        "today_min_c": today_min,
        "tomorrow_date": tomorrow_date,
        "tomorrow_desc": tomorrow_desc,
        "tomorrow_max_c": tomorrow_max,
        "tomorrow_min_c": tomorrow_min,
        "elapsed_ms": elapsed_ms,
    }


def format_weather_prompt_section(weather: Dict[str, Any]) -> str:
    if weather.get("status") == "ok":
        return (
            "【实时联网天气查询结果（已由 Open-Meteo 实时联网获取，请直接根据以下实测与预报数值回答，使用整数度数，不要编造其他数值）】：\n"
            f"- 城市：{weather['city']}（观测时间：{weather['observed_at']}）\n"
            f"- 当前实况：{weather['weather_desc']}，当前气温 {weather['temperature_c']}度，今天最高 {weather['today_max_c']}度、最低 {weather['today_min_c']}度，相对湿度 {weather['humidity_pct']}%\n"
            f"- 明天预报（{weather['tomorrow_date']}）：{weather['tomorrow_desc']}，最高 {weather['tomorrow_max_c']}度、最低 {weather['tomorrow_min_c']}度"
        )
    if weather.get("status") == "missing_city":
        return (
            "【天气查询提示】：用户询问了天气，但未指明具体城市名称，且设备没有室外气象传感器。"
            "请简短说明你无法直接看到窗外天气，如果告诉我具体城市名称（如北京、上海），我可以帮你联网查询实时天气；严禁猜测晴雨或温度。"
        )
    return (
        f"【实时联网天气查询失败】：尝试联网查询「{weather.get('city', '目标城市')}」天气时失败（原因：{weather.get('error', '网络请求异常')}）。"
        "请如实告知用户当前联网天气查询失败，暂时无法获取实时天气数据，严禁凭空猜测晴雨或温度。"
    )
