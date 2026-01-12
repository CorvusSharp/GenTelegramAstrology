import time
from typing import Any
import asyncio
import threading
from collections.abc import Coroutine
from llm_client import LLMService
from prompts import MAIN_PERSONA, BLOCK_PROMPTS, VERIFICATION_PROMPT, STYLE_PROMPT, CONSISTENCY_CHECK_PROMPT, FINAL_LAYOUT_PROMPT, FULL_REPORT_PROMPT, REFINE_REPORT_PROMPT

class AstroFlowOrchestrator:
    def __init__(self):
        self.llm = LLMService()

    @staticmethod
    def _run_coro_in_new_loop(coro: Coroutine[Any, Any, Any]) -> Any:
        """Запускает coroutine в новом event loop в отдельном потоке.

        Нужен, чтобы безопасно вызывать async-код из sync-функций,
        даже если текущий поток уже внутри запущенного event loop.
        """
        result_container: dict[str, Any] = {}
        error_container: dict[str, BaseException] = {}

        def runner():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result_container["result"] = loop.run_until_complete(coro)
            except BaseException as e:
                error_container["error"] = e
            finally:
                try:
                    loop = asyncio.get_event_loop()
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        t.join()
        if "error" in error_container:
            raise error_container["error"]
        return result_container.get("result")

    def process_compatibility_report(self, client_data_json: Any) -> tuple[str, list[dict[str, Any]]]:
        """
        Основной пайплайн:
        Оптимизированная версия:
        1. Единый запрос на генерацию полного отчета (Блоки 1-7).
        """
        # Конвертируем данные в читаемую строку для LLM.
        data_str = str(client_data_json)
        if isinstance(client_data_json, dict) and client_data_json.get("source_text"):
            data_str += "\n\nRAW_SOURCE_TEXT:\n" + str(client_data_json.get("source_text"))

        print("--- STARTING ANALYSIS (OPTIMIZED SINGLE PASS) ---")

        # Так как это синхронный метод, а llm_client методы синхронны (внутри OpenAI клиента),
        # то можно вызывать напрямую. Но старый код использовал to_thread, оставим если нужно.
        # В llm_client _completion блокирующий.
        
        full_text = self.llm.generate_full_report(MAIN_PERSONA, data_str, FULL_REPORT_PROMPT)
        
        # Если генерация упала
        if not full_text or "Ошибка генерации" in full_text:
             return f"К сожалению, не удалось создать отчет. Ошибка: {full_text}", []

        # Возвращаем результат без списка ошибок, так как верификация теперь внедрена в промпт
        return full_text, []

    def refine_report(self, current_report: str, user_feedback: str) -> str:
        """Перегенерация/улучшение текста отчета на основе обратной связи пользователя."""
        print(f"--- REFINING REPORT WITH FEEDBACK: {user_feedback[:50]}... ---")
        
        prompt = REFINE_REPORT_PROMPT.format(
            current_report=current_report,
            user_feedback=user_feedback
        )
        
        refined_text = self.llm.run_prompt(
            system_prompt="Ты — профессиональный астролог-редактор. Следуй инструкциям по доработке текста.",
            user_prompt=prompt
        )
        return str(refined_text)

    def layout_report_astromarkup(self, client_data_json: Any, report_text: str, issues: list[dict[str, Any]] | None = None) -> str:
        """Финальная разметка для рендера в DOCX/PDF через простой текстовый формат AstroMarkup."""
        issues = issues or []
        payload = (
            FINAL_LAYOUT_PROMPT
            + "\n\nCLIENT_DATA_JSON:\n"
            + str(client_data_json)
            + "\n\nISSUES_JSON:\n"
            + str(issues)
            + "\n\nREPORT_TEXT:\n"
            + str(report_text)
        )
        formatted: Any = self.llm.run_prompt(
            "Ты — аккуратный редактор-верстальщик.",
            payload,
        )
        return formatted if isinstance(formatted, str) else str(formatted)

    def save_to_file(self, text: str, filename: str = "final_report.txt") -> None:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Report saved to {filename}")

