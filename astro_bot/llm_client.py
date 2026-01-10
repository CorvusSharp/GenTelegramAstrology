import os
from openai import OpenAI
import json
import time
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        # Используем OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"), 
        )
        # Единая модель для всего проекта
        # По запросу: использовать Gemini 3 Pro Preview
        self.common_model = "google/gemini-3-pro-preview"
        
        self.model_main = self.common_model 
        self.model_text = self.common_model
        self.model_verifier = self.common_model 
        self.model_stylist = self.common_model

        # Модели для распознавания изображения (попробуем несколько и сольём результат)
        # Важно: список должен содержать только модели с поддержкой image_url.
        self.vision_models = [
            "google/gemini-3-pro-preview",
            "google/gemini-2.0-flash-001",
        ]

    def _completion(self, messages, response_format=None, max_retries: int = 4):
        """Единый вызов LLM с повторными попытками (на случай 429/временных сбоев)."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": self.common_model,
                    "messages": messages,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format

                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                last_error = e
                sleep_s = min(8.0, 0.75 * (2**attempt))
                print(f"⚠️ LLM request failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(sleep_s)

        raise last_error if last_error is not None else RuntimeError("LLM request failed")

    def _completion_model(self, model: str, messages, response_format=None, max_retries: int = 3):
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                last_error = e
                sleep_s = min(6.0, 0.6 * (2**attempt))
                print(f"⚠️ Vision model '{model}' failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(sleep_s)

        raise last_error if last_error is not None else RuntimeError("Vision request failed")

    @staticmethod
    def _normalize_value(value):
        if value is None:
            return None
        if isinstance(value, str):
            v = value.strip()
            if not v or v.lower() in {"null", "none", "unknown", "?"}:
                return None
            return v
        return value

    def _merge_extractions(self, results: list[dict]) -> dict:
        """Сливает несколько JSON-результатов распознавания.

        Правило: по каждому полю берем наиболее частое непустое значение (majority vote).
        Если нет большинства — берем первое непустое.
        Аспекты объединяем по множеству.
        """
        merged = {
            "client_1": {},
            "client_2": {},
            "aspects": [],
            "missing": {"client_1": [], "client_2": []},
            "status": "Unknown",
        }

        def pick_value(values: list):
            norm = [self._normalize_value(v) for v in values]
            norm = [v for v in norm if v is not None]
            if not norm:
                return None
            counts = {}
            for v in norm:
                counts[v] = counts.get(v, 0) + 1
            best = sorted(counts.items(), key=lambda x: (-x[1], norm.index(x[0])))[0][0]
            return best

        # keys expected
        planet_keys = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
            "lilith",
            "north_node",
            "ascendant",
            "name",
            "gender",
        ]

        for who in ("client_1", "client_2"):
            for key in planet_keys:
                vals = []
                for r in results:
                    vals.append((r.get(who) or {}).get(key))
                merged[who][key] = pick_value(vals)

        # aspects union
        aspect_set = set()
        for r in results:
            for a in (r.get("aspects") or []):
                if isinstance(a, str):
                    aa = a.strip()
                    if aa:
                        aspect_set.add(aa)
        merged["aspects"] = sorted(aspect_set)

        # recompute missing + status based on ">=5 planets" rule
        core_planets = [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]

        for who in ("client_1", "client_2"):
            known = 0
            missing = []
            for k in core_planets:
                if self._normalize_value(merged[who].get(k)) is None:
                    missing.append(k)
                else:
                    known += 1
            merged["missing"][who] = missing
            if known < 5:
                merged["status"] = "NEEDS_CLEARER_IMAGE"

        return merged

    def extract_data_from_image(self, base64_image, prompt):
        """Анализ изображения через Vision модели (majority vote)"""
        try:
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]

            parsed_results = []
            for model in self.vision_models:
                try:
                    response = self._completion_model(model, messages)
                    content = response.choices[0].message.content
                    if not content:
                        continue
                    content = content.replace("```json", "").replace("```", "").strip()
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        parsed_results.append(parsed)
                except Exception as e:
                    print(f"Error extracting data from image with {model}: {e}")
                    continue

            if not parsed_results:
                return None

            return self._merge_extractions(parsed_results)
        except Exception as e:
            print(f"Error extracting data from image: {e}")
            return None

    def generate_full_report(self, system_prompt, user_data, full_prompt):
        """Генерация полного отчета (всех блоков) за один проход"""
        try:
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ДАННЫЕ КЛИЕНТОВ:\n{user_data}\n\nЗАДАЧА:\n{full_prompt}"}
            ]
            # Можно увеличить таймаут или макс токенов, если нужно
            response = self._completion(messages)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating full report: {e}")
            return f"Ошибка генерации полного отчета: {e}"

    def generate_block(self, system_prompt, user_data, block_prompt):
        """Генерация блока текста (Первичная)"""
        try:
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"ДАННЫЕ КЛИЕНТОВ:\n{user_data}\n\nЗАДАЧА:\n{block_prompt}"}
            ]
            response = self._completion(messages)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating block: {e}")
            return f"Ошибка генерации блока: {e}" 

    def verify_block(self, user_data, generated_text, verification_prompt):
        """Проверка блока на фактологию"""
        try:
            messages=[
                {"role": "system", "content": "Ты строгий астрологический аудитор. Отвечай только в формате JSON."},
                {"role": "user", "content": f"{verification_prompt}\n\nВОТ ДАННЫЕ:\n{user_data}\n\nВОТ ТЕКСТ НА ПРОВЕРКУ:\n{generated_text}"}
            ]
            response = self._completion(messages, response_format={"type": "json_object"})
            content = response.choices[0].message.content
            if not content:
                return {"status": "NEEDS_MANUAL_REVIEW", "critical_errors": [], "feedback": "Empty response from verifier"}
             # Gemini может добавить markdown
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Error verifying block: {e}")
            # Возвращаем заглушку, чтобы процесс не падал
            return {"status": "NEEDS_MANUAL_REVIEW", "critical_errors": [], "feedback": f"Verification failed: {e}"}

    def refine_style(self, text, style_prompt):
        """Стилистическая вычитка"""
        try:
            messages=[
                {"role": "system", "content": "Ты профессиональный редактор."},
                {"role": "user", "content": f"{style_prompt}\n\nТЕКСТ ДЛЯ РЕДАКТУРЫ:\n{text}"}
            ]
            response = self._completion(messages)
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error styling text: {e}")
            return text

    def run_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """Универсальный вызов LLM без предустановленного "редактора".

        Использовать для задач, где важны структура/формат (верстка, сборка),
        а не стилистическая вычитка.
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = self._completion(messages)
            content = response.choices[0].message.content
            return content if isinstance(content, str) else str(content)
        except Exception as e:
            print(f"Error running prompt: {e}")
            return ""

    def consistency_check(self, full_text: str, check_prompt: str) -> str:
        """Финальная проверка на противоречия/склейки (без изменения формата)."""
        result = self.run_prompt(
            "Ты главный редактор.",
            f"{check_prompt}\n\nПОЛНЫЙ ТЕКСТ:\n{full_text}",
        )
        return result if result else full_text
