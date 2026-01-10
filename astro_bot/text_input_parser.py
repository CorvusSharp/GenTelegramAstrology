import re
from typing import Any


def _clean(s: str) -> str:
    s = s.replace("\u00A0", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_text_input(raw_text: str) -> dict[str, Any]:
    """Парсит текстовый ввод (как из сообщения пользователя) в структуру client_data.

    Цель: получить имена, базовые метаданные (дата/время/город/UTC) и минимум знаки планет.
    Дома/градусы сохраняем как строки, но основной пайплайн опирается на знаки.

    Возвращаемый формат совместим с остальным проектом:
    {
      "client_1": {"name":..., "gender":..., "sun":..., ...},
      "client_2": {...},
      "aspects": [],
      "source_text": "...",
      "status": "TEXT_INPUT"
    }
    """
    text = raw_text.strip()

    client_1: dict[str, Any] = {"name": "Partner 1"}
    client_2: dict[str, Any] = {"name": "Partner 2"}

    # Имена
    m = re.search(r"Вы:\s*([^\n]+?)\s+Родил", text, re.IGNORECASE)
    if m:
        client_1["name"] = _clean(m.group(1))

    m = re.search(r"Партн[её]р\)\s*:\s*([^\n]+?)\s+День", text, re.IGNORECASE)
    if m:
        client_2["name"] = _clean(m.group(1))

    # Пол
    m = re.search(r"Пол:\s*(Женский|Мужской)", text, re.IGNORECASE)
    if m:
        client_1["gender"] = _clean(m.group(1))

    m = re.search(r"Партн[её]р\).*?Пол:\s*(Женский|Мужской)", text, re.IGNORECASE | re.DOTALL)
    if m:
        client_2["gender"] = _clean(m.group(1))

    # Блоки планет: ищем строки вида "Солнце d Близнецы 02°16'42""
    planet_map = {
        "Солнце": "sun",
        "Луна": "moon",
        "Меркурий": "mercury",
        "Венера": "venus",
        "Марс": "mars",
        "Юпитер": "jupiter",
        "Сатурн": "saturn",
        "Уран": "uranus",
        "Нептун": "neptune",
        "Плутон": "pluto",
        "Хирон": "chiron",
        "Лилит": "lilith",
        "Восх. узел": "north_node",
        "Восх\. узел": "north_node",
        "Асцендент": "ascendant",
    }

    sign_re = r"(Овен|Телец|Близнецы|Рак|Лев|Дева|Весы|Скорпион|Стрелец|Козерог|Водолей|Рыбы)"

    def parse_planets(section_text: str, out: dict[str, Any]):
        for ru_name, key in planet_map.items():
            mm = re.search(rf"{ru_name}\\s+[^A-Za-zА-Яа-я0-9]*\\s*{sign_re}", section_text)
            if mm:
                out[key] = mm.group(1)

        # Долготы (опционально) — сохраняем как raw для возможного финального форматирования
        for ru_name, key in planet_map.items():
            mm = re.search(rf"{ru_name}\\s+.*?{sign_re}\\s+([0-9]{{1,2}}°[0-9]{{1,2}}'\"?[0-9]{{0,2}}\"?)", section_text)
            if mm:
                out[f"{key}_deg"] = mm.group(2) if mm.lastindex and mm.lastindex >= 2 else mm.group(1)

    # Разрезаем на части "Планеты 1" и "Планеты 2"
    parts = re.split(r"Планеты\s*1\s*\(|Планеты\s*2\s*\(", text)
    # Если split не сработал, пробуем по ключам
    sec1 = ""
    sec2 = ""

    m1 = re.search(r"Планеты\s*1\s*\(.*?\)(.*?)(Планеты\s*2\s*\(|$)", text, re.IGNORECASE | re.DOTALL)
    if m1:
        sec1 = m1.group(1)
    m2 = re.search(r"Планеты\s*2\s*\(.*?\)(.*)$", text, re.IGNORECASE | re.DOTALL)
    if m2:
        sec2 = m2.group(1)

    if sec1:
        parse_planets(sec1, client_1)
    if sec2:
        parse_planets(sec2, client_2)

    return {
        "client_1": client_1,
        "client_2": client_2,
        "aspects": [],
        "source_text": text,
        "status": "TEXT_INPUT",
        "missing": {"client_1": [], "client_2": []},
    }
