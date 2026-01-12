import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from astro_bot.pdf_renderer import PDFReportGenerator


def main() -> None:
    out = os.path.abspath("smoke_report.pdf")
    gen = PDFRcceportGenerator(out)

    # Минимальный фрагмент, чтобы проверить:
    # 1) титульную страницу с image.png
    # 2) жирное выделение планет в строках "Планета — Знак"
    full_text = """[H1]Ваши планеты[/H1]
[P]23 Мая 1984 года, Москва[/P]
[P]Солнце — Близнецы[/P]
[P]Луна — Рыбы[/P]
[P]Меркурий — Телец[/P]
[P]Венера — Телец[/P]
[P]Марс — Скорпион[/P]
[P]Сатурн — Скорпион[/P]
[P]Юпитер — Козерог[/P]

[H1]Планеты партнёра[/H1]
[P]17 Ноября 1980 года, Москва[/P]
[P]Солнце — Скорпион[/P]
[P]Луна — Рыбы[/P]
[P]Меркурий — Скорпион[/P]
[P]Венера — Весы[/P]
[P]Марс — Стрелец[/P]
[P]Сатурн — Весы[/P]
[P]Юпитер — Весы[/P]

[H1]Общая картина связи[/H1]
[P]Здесь начинается основной текст после планет партнёра.[/P]
"""

    gen.create_pdf({}, full_text)
    print(out)


if __name__ == "__main__":
    main()
