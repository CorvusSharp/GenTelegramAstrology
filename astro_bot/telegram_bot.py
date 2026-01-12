import os
import base64
import logging
import asyncio
from typing import Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv

from flow_manager import AstroFlowOrchestrator
from llm_client import LLMService
from prompts import IMAGE_EXTRACTION_PROMPT
from text_input_parser import parse_text_input
from pdf_renderer import PDFReportGenerator
from docx_renderer import DOCXReportGenerator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Unhandled exception while handling an update", exc_info=context.error)

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class AstroBot:
    def __init__(self):
        self.orchestrator = AstroFlowOrchestrator()
        self.llm = LLMService()
        # Память между сообщениями: сначала фото (таблица), потом текст с именами/метаданными.
        self.pending_inputs: dict[int, dict[str, Any]] = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Привет! Я Астро-Бот. 🌌\n\nОтправь мне скриншот таблицы синастрии или натальных карт, и я сделаю подробный разбор совместимости."
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        # Создаём/обновляем состояние сразу, чтобы текст можно было прислать пока идёт распознавание
        state = self.pending_inputs.get(chat_id) or {}
        state.update(
            {
                "status": "EXTRACTING",
                "image_data": None,
                "raw_text": state.get("raw_text"),
                "image_message_id": update.message.message_id,
            }
        )
        self.pending_inputs[chat_id] = state
        
        # 1. Скачиваем фото
        photo_file = await update.message.photo[-1].get_file()
        await context.bot.send_message(chat_id=chat_id, text="Получил фото! Начинаю анализ... Это займет некоторое время (около 5-10 минут). ⏳")
        
        byte_array = await photo_file.download_as_bytearray()
        base64_image = base64.b64encode(byte_array).decode('utf-8')

        # 2. Распознаем данные (Gemini Vision)
        data_extraction_msg = await context.bot.send_message(chat_id=chat_id, text="👀 Смотрю на карты... Распознаю планеты...")
        
        try:
            client_data = self.llm.extract_data_from_image(base64_image, IMAGE_EXTRACTION_PROMPT)
            
            if not client_data:
                state["status"] = "IDLE"
                await context.bot.send_message(chat_id=chat_id, text="❌ Не удалось распознать данные на изображении. Попробуйте отправить более четкий скриншот таблицы.")
                return

            if client_data.get("status") == "NEEDS_CLEARER_IMAGE":
                state["status"] = "IDLE"
                missing = client_data.get("missing") or {}
                m1 = ", ".join(missing.get("client_1", []) or [])
                m2 = ", ".join(missing.get("client_2", []) or [])
                hint = "❌ Скриншот распознан не полностью (меньше 5 планет у партнёра).\n"
                if m1:
                    hint += f"Partner 1 не вижу: {m1}.\n"
                if m2:
                    hint += f"Partner 2 не вижу: {m2}.\n"
                hint += "Пожалуйста, пришлите более чёткий скрин (без сжатия, крупнее)."
                await context.bot.send_message(chat_id=chat_id, text=hint)
                return

            # Сохраняем распознанные данные.
            state["image_data"] = client_data
            state["status"] = "WAITING_TEXT"

            # Форматируем распознанные данные для проверки пользователем (кратко, но максимально полно)
            c1 = client_data.get("client_1") or {}
            c2 = client_data.get("client_2") or {}

            def fmt_planets(c: dict) -> str:
                keys = [
                    ("sun", "Солнце"),
                    ("moon", "Луна"),
                    ("mercury", "Меркурий"),
                    ("venus", "Венера"),
                    ("mars", "Марс"),
                    ("jupiter", "Юпитер"),
                    ("saturn", "Сатурн"),
                    ("uranus", "Уран"),
                    ("neptune", "Нептун"),
                    ("pluto", "Плутон"),
                    ("lilith", "Лилит"),
                    ("north_node", "Северный узел"),
                    ("ascendant", "ASC"),
                ]
                parts: list[str] = []
                for k, label in keys:
                    v = c.get(k)
                    if v:
                        parts.append(f"{label}: {v}")
                return "; ".join(parts) if parts else "(ничего уверенно не видно)"

            aspects = client_data.get("aspects") or []
            aspects_preview = "\n".join([f"- {a}" for a in aspects[:12]])
            if len(aspects) > 12:
                aspects_preview += f"\n- … ещё {len(aspects) - 12}"

            parsed_info = (
                "✅ Распознал со скриншота (что удалось увидеть):\n\n"
                f"👤 Клиент 1: {c1.get('name', 'Partner 1')}\n{fmt_planets(c1)}\n\n"
                f"👤 Клиент 2: {c2.get('name', 'Partner 2')}\n{fmt_planets(c2)}\n\n"
                f"💑 Аспекты: {len(aspects)}\n"
                + (aspects_preview + "\n\n" if aspects_preview else "\n")
                + "✍️ Теперь пришлите ОТДЕЛЬНЫМ сообщением текст с именами/датами/городом.\n"
                + "Я использую и скрин, и ваш текст во всех промптах."
            )
            await context.bot.edit_message_text(chat_id=chat_id, message_id=data_extraction_msg.message_id, text=parsed_info)

            # Если текст уже пришёл, пока мы распознавали скрин — сразу продолжаем.
            if state.get("raw_text"):
                await context.bot.send_message(chat_id=chat_id, text="✍️ Текст уже получен ранее. Продолжаю без ожидания...")
                await self._finalize_with_text(chat_id=chat_id, raw_text=str(state.get("raw_text") or ""), update=update, context=context)
            return

        except Exception as e:
            logging.error(f"Error handling photo: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Произошла внутренняя ошибка: {str(e)}")


    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        raw_text = (update.message.text or "").strip()
        if not raw_text:
            return

        pending = self.pending_inputs.get(chat_id)
        if not pending:
            pending = {"status": "WAITING_IMAGE", "image_data": None, "raw_text": None}
            self.pending_inputs[chat_id] = pending

        # Сохраняем текст сразу, даже если фото ещё распознаётся
        pending["raw_text"] = raw_text

        status = pending.get("status")
        if status == "EXTRACTING":
            await context.bot.send_message(
                chat_id=chat_id,
                text="✍️ Текст получил. Скриншот ещё распознаётся — продолжу автоматически, как только закончу распознавание.",
            )
            return

        if status == "WAITING_FOR_FEEDBACK_TEXT":
            # Пользователь нажал "Переписать" и прислал текст
            await context.bot.send_message(chat_id=chat_id, text=f"🔧 Принято: '{raw_text}'. Переписываю отчет с учетом ваших пожеланий...")
            await self._handle_feedback_refinement(chat_id, raw_text, update, context)
            return
        
        if status == "WAITING_FOR_FEEDBACK_CHOICE":
             # Пользователь не нажал кнопку, а написал текст. Считаем, что это правка.
             await context.bot.send_message(chat_id=chat_id, text=f"🔧 Воспринимаю текст как правку: '{raw_text}'. Переписываю...")
             self.pending_inputs[chat_id]["status"] = "WAITING_FOR_FEEDBACK_TEXT"
             await self._handle_feedback_refinement(chat_id, raw_text, update, context)
             return

        if not pending.get("image_data"):
            await context.bot.send_message(
                chat_id=chat_id,
                text="✍️ Текст получил. Теперь пришлите скриншот таблицы (фото) — после распознавания начну отчёт.",
            )
            pending["status"] = "WAITING_IMAGE"
            return

        await self._finalize_with_text(chat_id=chat_id, raw_text=raw_text, update=update, context=context)

    async def _handle_feedback_refinement(self, chat_id: int, feedback_text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pending = self.pending_inputs.get(chat_id)
        if not pending or not pending.get("last_report_text"):
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Потерял контекст отчета. Пожалуйста, начните заново.")
            return

        current_report = pending["last_report_text"]
        client_data = pending.get("client_data") or pending.get("image_data") # Fallback

        try:
            loop = asyncio.get_running_loop()
            
            # 1. Refine text
            refined_text = await loop.run_in_executor(None, self.orchestrator.refine_report, current_report, feedback_text)
            
            # Update state with new text
            pending["last_report_text"] = refined_text

            # 2. Re-generate files (reuse logic)
            await self._generate_and_send_files(chat_id, client_data, refined_text, update, context)

        except Exception as e:
            logging.error(f"Error refining report: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Ошибка при обновлении отчета: {str(e)}")

    async def _generate_and_send_files(self, chat_id: int, client_data: dict, report_text: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Helper to generate PDF/DOCX and send them, then wait for feedback."""
        try:
            loop = asyncio.get_running_loop()
            
            await context.bot.send_message(chat_id=chat_id, text="🧩 Применяю правки и обновляю верстку...")
            
            def layout_task():
                # Issues list is empty for refined reports as we assume user manually overrode check
                return self.orchestrator.layout_report_astromarkup(client_data, report_text, [])

            astromarkup_text = await loop.run_in_executor(None, layout_task)

            await context.bot.send_message(chat_id=chat_id, text="🎨 Пересобираю PDF...")
            pdf_filename = f"Analys_{chat_id}_{update.message.message_id}.pdf"

            def generate_pdf_task():
                pdf_gen = PDFReportGenerator(pdf_filename)
                return pdf_gen.create_pdf(client_data, astromarkup_text)

            final_pdf_path = await loop.run_in_executor(None, generate_pdf_task)

            # await context.bot.send_message(chat_id=chat_id, text="📝 Формирую DOCX версию...") # Reduce spam
            docx_filename = f"Analys_{chat_id}_{update.message.message_id}.docx"

            def generate_docx_task():
                docx_gen = DOCXReportGenerator(docx_filename)
                return docx_gen.create_docx(client_data, astromarkup_text)

            final_docx_path = await loop.run_in_executor(None, generate_docx_task)

            await context.bot.send_message(chat_id=chat_id, text="✨ Готово! Вот обновленная версия.")

            name1 = client_data.get("client_1", {}).get("name", "Partner 1")
            name2 = client_data.get("client_2", {}).get("name", "Partner 2")

            await context.bot.send_document(
                chat_id=chat_id,
                document=open(final_pdf_path, 'rb'),
                filename=f"Совместимость_{name1}_{name2}_v2.pdf",
            )
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(final_docx_path, 'rb'),
                filename=f"Совместимость_{name1}_{name2}_v2.docx",
            )

            if os.path.exists(final_pdf_path):
                os.remove(final_pdf_path)
            if os.path.exists(final_docx_path):
                os.remove(final_docx_path)

            # Set status to waiting for feedback choice
            self.pending_inputs[chat_id]["status"] = "WAITING_FOR_FEEDBACK_CHOICE"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Всё ок, спасибо!", callback_data="feedback_no"),
                    InlineKeyboardButton("✏️ Переписать / Внести правки", callback_data="feedback_yes"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=chat_id, 
                text="Отчёт готов! 👇\n\nХотите что-то исправить или оставить как есть?",
                reply_markup=reply_markup
            )

        except Exception as e:
            logging.error(f"Error generating files: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Ошибка генерации файлов: {e}")

    async def _finalize_with_text(self, chat_id: int, raw_text: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        pending = self.pending_inputs.get(chat_id) or {}
        image_data = pending.get("image_data")
        if not image_data:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Не нашёл распознанные данные со скриншота. Пришлите фото ещё раз.")
            return

        await context.bot.send_message(chat_id=chat_id, text="✍️ Склеиваю текст и скриншот, запускаю отчёт...")

        try:
            text_data = parse_text_input(raw_text)
            client_data = image_data
            client_data["source_text"] = raw_text

            # Переносим имена из текста (приоритетнее Partner 1/2)
            if text_data.get("client_1", {}).get("name"):
                client_data.setdefault("client_1", {})["name"] = text_data["client_1"]["name"]
            if text_data.get("client_2", {}).get("name"):
                client_data.setdefault("client_2", {})["name"] = text_data["client_2"]["name"]

            # формируем краткую сводку
            name1 = client_data.get("client_1", {}).get("name", "Partner 1")
            name2 = client_data.get("client_2", {}).get("name", "Partner 2")
            sun1 = client_data.get("client_1", {}).get("sun", "?")
            sun2 = client_data.get("client_2", {}).get("sun", "?")
            moon1 = client_data.get("client_1", {}).get("moon", "?")
            moon2 = client_data.get("client_2", {}).get("moon", "?")

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Данные распознаны из текста:\n"
                    f"👤 {name1}: Солнце {sun1}, Луна {moon1}\n"
                    f"👤 {name2}: Солнце {sun2}, Луна {moon2}\n\n"
                    f"✍️ Начинаю написание отчёта по 7 блокам с проверкой качества..."
                ),
            )

            loop = asyncio.get_running_loop()
            report_text, issues = await loop.run_in_executor(None, self.orchestrator.process_compatibility_report, client_data)

            if report_text:
                # Сохраняем состояние для возможного редактирования пользователем
                self.pending_inputs[chat_id]["last_report_text"] = report_text
                self.pending_inputs[chat_id]["client_data"] = client_data
                
                # Показываем предупреждения, если были (до генерации файлов)
                if issues:
                    parts = ["⚠️ Предупреждение: после проверки остались возможные неточности:"]
                    for item in issues:
                        bid = item.get("block_id")
                        fb = (item.get("feedback") or "").strip()
                        line = f"Блок {bid}"
                        if fb:
                            line += f": {fb[:200]}"
                        parts.append(line)
                    await context.bot.send_message(chat_id=chat_id, text="\n".join(parts))

                # Генерируем и отправляем файлы
                await self._generate_and_send_files(chat_id, client_data, report_text, update, context)

            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Произошла ошибка при генерации отчёта.")

        except Exception as e:
            logging.error(f"Error handling text: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Произошла внутренняя ошибка: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на инлайн-кнопки."""
        query = update.callback_query
        chat_id = update.effective_chat.id
        await query.answer()

        data = query.data
        pending = self.pending_inputs.get(chat_id)

        if not pending:
             # Если бот перезагружался, состояния может не быть
             await query.edit_message_text(text="⚠️ Данные устарели. Пожалуйста, начните заново, прислав фото.")
             return

        if data == "feedback_no":
            # Пользователь доволен
            if chat_id in self.pending_inputs:
                del self.pending_inputs[chat_id]
            
            await query.edit_message_text(text="👌 Отлично! Рад, что вам понравилось. Жду следующие данные для нового разбора!")
        
        elif data == "feedback_yes":
            # Пользователь хочет внести правки
            pending["status"] = "WAITING_FOR_FEEDBACK_TEXT"
            await query.edit_message_text(text="🔧 Напишите, что именно нужно исправить или добавить в отчет.\n(Можно скопировать кусок текста и написать: перепиши это так-то).")


if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)

    astro_bot = AstroBot()
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    start_handler = CommandHandler('start', astro_bot.start)
    photo_handler = MessageHandler(filters.PHOTO, astro_bot.handle_photo)
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, astro_bot.handle_text)
    callback_handler = CallbackQueryHandler(astro_bot.handle_callback)
    
    application.add_handler(start_handler)
    application.add_handler(photo_handler)
    application.add_handler(text_handler)
    application.add_handler(callback_handler)

    application.add_error_handler(error_handler)
    
    print("🤖 Astro Bot started polling...")
    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("Stopping bot (KeyboardInterrupt)")
