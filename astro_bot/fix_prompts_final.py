
full_path = 'c:/Users/Ярослав/Desktop/Astrolog/astro_bot/prompts.py'
lines = open(full_path, encoding='utf-8').readlines()
# Truncate to where duplication starts (line 988 corresponds to index 987, but verification showed duplicates main persona at line 988)
# Let's count properly.
# Grep said line 988 has MAIN_PERSONA.
# So we want lines 0 to 987 (python slice [:988]). 
# Index 987 is line 988? No, lines are 1-based in grep usually.
# If grep says line 988, that is index 987.
# So lines[:988] includes index 987 (line 988). No, slice excludes end.
# lines[:987] gives lines 0..986 (lines 1..987).

# Let's verify what line 987 is.
# In previous read, line 987 was `"""`.
# Line 988 was `MAIN_PERSONA = """`.
# So we want to keep up to line 987 inclusive.
# So lines[:987] (indices 0 to 986) + line 987 (index 987)? No.
# lines 1..987 -> indices 0..986. python [:987] gets 0..986. Good.

truncated_lines = lines[:987]

final_layout_prompt = """

FINAL_LAYOUT_PROMPT = \"\"\"
Ты — верстальщик финального отчета.
Твоя задача — оформить текст в специальном формате AstroMarkup для последующей конвертации в DOCX/PDF.

ФОРМАТ РАЗМЕТКИ:
1. Заголовки блоков (=== БЛОК N ===) преобразуй в [H1]Название блока[/H1].
2. Внутренние подзаголовки (Вы:, В паре:, Совет:) преобразуй в [H2]Подзаголовок[/H2].
3. Основной текст оставь без изменений.
4. Выдели жирным ключевые астрологические термины (планеты, знаки): [B]Солнце в Овне[/B].
5. Списки (если есть) оформляй как [L]Элемент списка[/L] (каждый пункт с новой строки).

Пример:
[H1]Общая картина[/H1]
В вашей паре [B]Солнце[/B] находится в [B]Льве[/B]...

ВЕРНИ ТОЛЬКО РАЗМЕЧЕННЫЙ ТЕКСТ.
\"\"\"
"""

with open(full_path, 'w', encoding='utf-8') as f:
    f.writelines(truncated_lines)
    f.write(final_layout_prompt)

print("Fixed prompts.py")
