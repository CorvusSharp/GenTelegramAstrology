import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from astro_bot.docx_renderer import DOCXReportGenerator


def main() -> None:
    out = os.path.abspath("smoke_report.docx")
    gen = DOCXReportGenerator(out)

    full_text = """[H1]Ваши планеты[/H1]
[P]23 Мая 1984 года, Москва[/P]
[P][B]Солнце[/B] — Близнецы[/P]
[P][B]Луна[/B] — Рыбы[/P]
[P][B]Меркурий[/B] — Телец[/P]
[P][B]Венера[/B] — Телец[/P]
[P][B]Марс[/B] — Скорпион[/P]
[P][B]Сатурн[/B] — Скорпион[/P]
[P][B]Юпитер[/B] — Козерог[/P]

[H1]Планеты партнёра[/H1]
[P]17 Ноября 1980 года, Москва[/P]
[P][B]Солнце[/B] — Скорпион[/P]
[P]Луна — Рыбы[/P]
[P]Меркурий — Скорпион[/P]
[P]Венера — Весы[/P]
[P]Марс — Стрелец[/P]
[P]Сатурн — Весы[/P]
[P]Юпитер — Весы[/P]

[H1]Общая картина связи[/H1]

[P]Здесь начинается основной текст после планет партнёра.[/P]

БЛОК 2. ЭМОЦИИ И ЛУНА
[P]Текст блока для проверки заголовка без слова БЛОК.[/P]
"""

    gen.create_docx({}, full_text)
    print(out)


if __name__ == "__main__":
    main()
