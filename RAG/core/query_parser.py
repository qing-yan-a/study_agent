import re
from datetime import date


def is_valid_date(year: int, month: int, day: int) -> bool:
    """校验年月日是否是真实存在的日期。"""
    try:
        date(year, month, day)
        return True
    except ValueError:
        return False


def extract_date_keywords(query: str, default_year: int = 2026) -> list[str]:
    """从用户 query 中提取日期，并扩展成用于关键词匹配的多种写法。"""
    keywords = []

    patterns = [
        r"(?<!\d)(?P<year>\d{4})[-/.年](?P<month>\d{1,2})[-/.月](?P<day>\d{1,2})日?(?!\d)",
        r"(?<!\d)(?P<month>\d{1,2})[-/.月](?P<day>\d{1,2})日?(?!\d)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, query):
            year = int(match.groupdict().get("year") or default_year)
            month = int(match.group("month"))
            day = int(match.group("day"))

            if not is_valid_date(year, month, day):
                continue

            keywords.extend(
                [
                    f"{year}-{month:02d}-{day:02d}",
                    f"{month:02d}-{day:02d}",
                    f"{month}.{day}",
                    f"{month}月{day}日",
                ]
            )

    return list(dict.fromkeys(keywords))
