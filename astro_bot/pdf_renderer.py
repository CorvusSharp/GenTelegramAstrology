import os
import re
from typing import Any, Dict
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.pdfgen import canvas

class PDFReportGenerator:
    def __init__(self, output_filename="report.pdf"):
        self.output_filename = output_filename
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._create_custom_styles()

    def _register_fonts(self):
        """Регистрация шрифтов с поддержкой кириллицы (Cross-platform)"""
        
        # Определяем возможные пути к шрифтам (приоритет: локальная папка -> Linux -> Windows)
        # Имена файлов шрифтов (Regular, Bold, Italic, BoldItalic)
        font_files = {
            'regular': ['times.ttf', 'Times_New_Roman.ttf'],
            'bold': ['timesbd.ttf', 'Times_New_Roman_Bold.ttf'],
            'italic': ['timesi.ttf', 'Times_New_Roman_Italic.ttf'],
            'bold_italic': ['timesbi.ttf', 'Times_New_Roman_Bold_Italic.ttf']
        }

        # Пути поиска
        search_paths = [
            os.path.join(os.getcwd(), 'fonts'),                    # 1. Папка fonts в корне проекта
            os.path.join(os.path.dirname(__file__), '..', 'fonts'), # 2. Папка fonts относительно скрипта
            '/usr/share/fonts/truetype/msttcorefonts',             # 3. Linux (если установлен пакет ttf-mscorefonts-installer)
            '/usr/share/fonts/TTF',                                # 4. Linux (Arch/Manjaro)
            r'C:\Windows\Fonts',                                   # 5. Windows
        ]

        found_fonts = {}

        def find_font(font_variants):
            for path in search_paths:
                for filename in font_variants:
                    full_path = os.path.join(path, filename)
                    if os.path.exists(full_path):
                        return full_path
            return None

        # Ищем каждый шрифт
        found_fonts['regular'] = find_font(font_files['regular'])
        found_fonts['bold'] = find_font(font_files['bold'])
        found_fonts['italic'] = find_font(font_files['italic'])
        found_fonts['bold_italic'] = find_font(font_files['bold_italic'])

        try:
            # Регистрируем основной шрифт
            if found_fonts['regular']:
                pdfmetrics.registerFont(TTFont('TimesNewRoman', found_fonts['regular']))
                self.font_name = 'TimesNewRoman'
                print(f"Font loaded: {found_fonts['regular']}")

                # Регистрируем варианты, если найдены
                if found_fonts['bold']:
                    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', found_fonts['bold']))
                if found_fonts['italic']:
                    pdfmetrics.registerFont(TTFont('TimesNewRoman-Italic', found_fonts['italic']))
                if found_fonts['bold_italic']:
                    pdfmetrics.registerFont(TTFont('TimesNewRoman-BoldItalic', found_fonts['bold_italic']))
                
                # Создаем семейство (Family) для работы тегов <b> и <i>
                # Если какой-то вариант не найден, подставляем Regular (чтобы не падало), но стиль не применится.
                try:
                    pdfmetrics.registerFontFamily(
                        'TimesNewRoman',
                        normal='TimesNewRoman',
                        bold='TimesNewRoman-Bold' if found_fonts['bold'] else 'TimesNewRoman',
                        italic='TimesNewRoman-Italic' if found_fonts['italic'] else 'TimesNewRoman',
                        boldItalic='TimesNewRoman-BoldItalic' if found_fonts['bold_italic'] else 'TimesNewRoman'
                    )
                except Exception as ex_fam:
                    print(f"Family registration warning: {ex_fam}")

            else:
                # Если Times New Roman не найден совсем
                print("⚠️ Warning: Times New Roman font not found. Using Helvetica (No Cyrillic support in standard PDF).")
                print(f"Please copy 'times.ttf' to '{os.path.join(os.getcwd(), 'fonts')}'")
                self.font_name = 'Helvetica'
                
        except Exception as e:
            print(f"Font registration error: {e}")
            self.font_name = 'Helvetica'

    def _create_custom_styles(self):
        """Создание стилей для отчета"""
        # Заголовок отчета (на титульной)
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Title'],
            fontName=(self.font_name + '-Bold') if (self.font_name == 'TimesNewRoman' and 'TimesNewRoman-Bold' in pdfmetrics.getRegisteredFontNames()) else self.font_name,
            fontSize=22, # Reduced from 24 to 22
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=50,
            textColor=colors.HexColor('#1a237e') # Глубокий синий
        ))

        # Подзаголовок (имена)
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontName=(self.font_name + '-Bold') if (self.font_name == 'TimesNewRoman' and 'TimesNewRoman-Bold' in pdfmetrics.getRegisteredFontNames()) else self.font_name,
            fontSize=16,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=100,
            textColor=colors.HexColor('#303f9f')
        ))

        # Заголовок блока (Главы)
        self.styles.add(ParagraphStyle(
            name='BlockHeader',
            parent=self.styles['Heading1'],
            fontName=(self.font_name + '-Bold') if (self.font_name == 'TimesNewRoman' and 'TimesNewRoman-Bold' in pdfmetrics.getRegisteredFontNames()) else self.font_name,
            fontSize=14,  # Reduced from 16 to 14
            leading=18,
            alignment=TA_LEFT,
            spaceBefore=20,
            spaceAfter=15,
            textColor=colors.HexColor('#283593'),
            borderPadding=5,
            borderColor=colors.HexColor('#e8eaf6'),
            borderWidth=0,
            backColor=colors.HexColor('#e8eaf6'), # Легкая подложка
            keepWithNext=True
        ))

        # Подзаголовок внутри блока: меньше, чем BlockHeader
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Normal'],
            fontName=(self.font_name + '-Bold') if (self.font_name == 'TimesNewRoman' and 'TimesNewRoman-Bold' in pdfmetrics.getRegisteredFontNames()) else self.font_name,
            fontSize=13,  # Reduced from 15 to 13
            leading=16,
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor('#1f2a44'),
            keepWithNext=True
        ))

        # Небольшой акцент «ИТОГ/ВЫВОД»: жирный курсив, не заголовок
        self.styles.add(ParagraphStyle(
            name='EmphasisLine',
            parent=self.styles['Normal'],
            fontName=self.font_name + '-Italic' if (self.font_name == 'TimesNewRoman' and 'TimesNewRoman-Italic' in pdfmetrics.getRegisteredFontNames()) else self.font_name,
            fontSize=11,
            leading=15,
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=6,
            textColor=colors.HexColor('#37474f'),
        ))

        # Основной текст
        self.styles.add(ParagraphStyle(
            name='BodyTextCustom',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=12,  # Reduced from 14 to 12
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10
        ))

        # Лист (точечный список)
        self.styles.add(ParagraphStyle(
            name='ListTextCustom',
            parent=self.styles['BodyTextCustom'],
            leftIndent=20,
            firstLineIndent=0,
            bulletIndent=10,
            spaceAfter=5
        ))

        # Строки с планетами: обычный текст, но названия планет будут курсивом через встроенный tag <i>
        # (для Truetype-шрифтов ReportLab корректно переключит face на -Italic, если он зарегистрирован).
        self.styles.add(ParagraphStyle(
            name='PlanetLine',
            parent=self.styles['BodyTextCustom'],
            fontName=self.font_name,
            fontSize=12,  # Matching body text (12)
            leading=16,
            alignment=TA_LEFT,
            spaceAfter=6
        ))

        # Цитаты / Выделения
        self.styles.add(ParagraphStyle(
            name='HighlightText',
            parent=self.styles['Normal'],
            fontName=self.font_name + '-Italic' if self.font_name == 'Arial' else self.font_name,
            fontSize=12,
            leading=17,
            alignment=TA_LEFT,
            leftIndent=20,
            textColor=colors.HexColor('#455a64'),
            spaceAfter=10
        ))

    def create_pdf(self, client_data: Dict[str, Any], full_text: str) -> str:
        """Генерация PDF документа"""
        story = []
        
        # --- Титульная страница ---
        # Делаем её через onFirstPage, чтобы баннер был на всю ширину,
        # а заголовок был поверх баннера (как на скриншоте).

        # Баннер рисуется прямо на canvas, поэтому story должен начать контент ниже баннера.
        cover_banner_h = 2 * cm
        cover_gap_h = 1.5 * cm
        story.append(Spacer(1, cover_banner_h + cover_gap_h - 15))


        # --- Основной контент ---
        # Парсим текст, пытаясь найти заголовки блоков
        # Предполагаем, что заголовки начинаются с "БЛОК X" или "Блок X"
        
        astromarkup_re = re.compile(r"^\[(TITLE|SUBTITLE|H1|H2|P|EM|L|B)\](.*)\[/\1\]$")
        planet_label_re = re.compile(
            r"^\s*(?:[•\-–—]\s*)?(Солнце|Луна|Меркурий|Венера|Марс|Юпитер|Сатурн|Уран|Нептун|Плутон|Лилит|Северный узел|ASC)\s*—\s*(.+?)\s*$",
            re.IGNORECASE,
        )

        # Нельзя полагаться на <i> в Paragraph: в некоторых связках шрифтов/верстки
        # визуально курсив может не проявляться. Поэтому для названий планет
        # явно задаём italic-face через font tag и зарегистрированный Arial-Italic.
        italic_face = (
            'TimesNewRoman-Italic'
            if (self.font_name == 'TimesNewRoman' and 'TimesNewRoman-Italic' in pdfmetrics.getRegisteredFontNames())
            else self.font_name
        )
        
        # Pre-process text:
        # 1. Normalize blocks that span multiple lines into single lines (replacing \n with space inside blocks)
        def normalize_block(m):
            tag = m.group(1)
            content = m.group(2)
            # Replace newlines with space to make it a single line for line-based parser
            norm_content = re.sub(r'\s+', ' ', content).strip()
            return f"[{tag}]{norm_content}[/{tag}]"
            
        full_text = re.sub(r"\[(H1|H2|P|EM|L|B)\](.*?)\[/\1\]", normalize_block, full_text, flags=re.DOTALL)

        # 2. Ensure block tags are on separate lines (fixes [P]...[/P][P]...[/P])
        full_text = re.sub(r'\[/(P|H1|H2|L|EM)\]\s*\[', r'[/\1]\n[', full_text)

        lines = full_text.split('\n')

        in_partner_planets = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            m = astromarkup_re.match(line)
            if m:
                tag = m.group(1)
                content = m.group(2).strip()
                if not content:
                    continue
                
                # Обработка вложенных тегов [B]...[/B] внутри контента
                # ReportLab поддерживает тег <b>...</b>, поэтому заменим наши [B] на <b>
                content = content.replace("[B]", "<b>").replace("[/B]", "</b>")

                if tag in {"TITLE", "SUBTITLE"}:
                    continue  # Уже отрисовали заголовок отдельно (или можно добавить в story)
                elif tag == "H1":
                    story.append(Paragraph(content, self.styles['BlockHeader']))
                elif tag == "H2":
                    story.append(Paragraph(content, self.styles['SubHeader']))
                elif tag == "EM":
                    story.append(Paragraph(content, self.styles['EmphasisLine']))
                elif tag == "P":
                    story.append(Paragraph(content, self.styles['BodyTextCustom']))
                elif tag == "L": # List item
                    # Добавляем буллит вручную или используем ListFlowable, но Paragraph проще
                    story.append(Paragraph("• " + content, self.styles['ListTextCustom']))
                elif tag == "B": # Если вдруг вся строка помечена как B
                    story.append(Paragraph(f"<b>{content}</b>", self.styles['BodyTextCustom']))
                
                continue
            
            # Если строка не обернута в [TAG]...[/TAG], пробуем эвристики или просто текст
            # Если есть инлайн [B], тоже меняем на <b>
            line = line.replace("[B]", "<b>").replace("[/B]", "</b>")

            # Проверка на список планет
            m_planet = planet_label_re.match(line)
            if m_planet:
                label = m_planet.group(1)
                rest = m_planet.group(2)
                story.append(
                    Paragraph(
                        f"<font name=\"{italic_face}\"><b>{label}</b></font> — {rest}",
                        self.styles['PlanetLine'],
                    )
                )
            else:
                # Первый непланетный абзац после списка планет партнёра — просто продолжаем текст
                if in_partner_planets:
                    in_partner_planets = False

                story.append(Paragraph(line, self.styles['BodyTextCustom']))

        # --- Генерация ---
        doc = SimpleDocTemplate(
            self.output_filename,
            pagesize=A4,
            rightMargin=28, leftMargin=28,
            topMargin=28, bottomMargin=28
        )

        def draw_cover(canv: canvas.Canvas, doc_obj):
            canv.saveState()

            page_w, page_h = A4
            top = doc_obj.topMargin

            # Баннер: на всю ширину страницы (без полей), но по высоте ограничиваем.
            image_path = os.path.join(os.path.dirname(__file__), "..", "image.png")
            image_path = os.path.abspath(image_path)
            banner_h = 3.2 * cm  # компактный баннер, как на примере
            banner_top_pad = 1.0 * cm

            if os.path.exists(image_path):
                try:
                    canv.drawImage(
                        image_path,
                        0,
                        page_h - banner_top_pad - banner_h,
                        width=page_w,
                        height=banner_h,
                        preserveAspectRatio=False,
                        mask='auto',
                    )
                except Exception as e:
                    print(f"⚠️ Could not draw cover image: {e}")

            # Заголовок поверх баннера
            title = "Анализ совместимости"
            canv.setFillColor(colors.white)
            # Если Arial доступен — используем жирный, иначе fallback
            font_bold = 'TimesNewRoman-Bold' if 'TimesNewRoman-Bold' in pdfmetrics.getRegisteredFontNames() else self.font_name
            # Подгоняем размер шрифта под ширину страницы с небольшими полями
            size = 28
            max_w = page_w - (2.0 * cm)
            while size > 16 and pdfmetrics.stringWidth(title, font_bold, size) > max_w:
                size -= 1
            canv.setFont(font_bold, size)
            canv.drawCentredString(page_w / 2, page_h - banner_top_pad - (banner_h / 2) - 3, title)

            canv.restoreState()

        doc.build(story, onFirstPage=draw_cover)
        return self.output_filename

# Пример использования
if __name__ == "__main__":
    dummy_data = {"client_1": {"name": "Иван"}, "client_2": {"name": "Мария"}}
    dummy_text = "БЛОК 1 ОБЩАЯ КАРТИНА\nЗдесь идет текст описания.\n\nБЛОК 2 ЭМОЦИИ\nЕще текст."
    gen = PDFReportGenerator("test_report.pdf")
    gen.create_pdf(dummy_data, dummy_text)
