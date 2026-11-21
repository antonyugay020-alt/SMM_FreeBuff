"""
fix_think.py — Вырезает тег <think> из ответа AI перед парсингом JSON.
"""
from pathlib import Path

p = Path('src/ai_brain.py')
c = p.read_text(encoding='utf-8')

# Находим метод _parse_response и добавляем вырезку тега <think>
old_code = '''    def _parse_response(self, content: str) -> List[Dict]:
        """Парсит ответ AI и извлекает JSON. Устойчив к markdown и лишнему тексту."""
        try:
            # 1. Вырезаем markdown-блоки ```json ... ```
            markdown_match = re.search(r'```json\\s*\\n?(.*?)\\n?```', content, re.DOTALL)'''

new_code = '''    def _parse_response(self, content: str) -> List[Dict]:
        """Парсит ответ AI и извлекает JSON. Устойчив к markdown и лишнему тексту."""
        try:
            # 0. Вырезаем тег <think> от reasoning-моделей
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            # 1. Вырезаем markdown-блоки ```json ... ```
            markdown_match = re.search(r'```json\\s*\\n?(.*?)\\n?```', content, re.DOTALL)'''

if old_code in c:
    c = c.replace(old_code, new_code)
    p.write_text(c, encoding='utf-8')
    print('✅ Исправлено: вырезаем тег <think> перед парсингом JSON')
else:
    print('⚠️ Шаблон не найден. Проверь src/ai_brain.py вручную')