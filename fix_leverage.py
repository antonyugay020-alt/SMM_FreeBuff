p = 'src/execution.py'
c = open(p, 'r', encoding='utf-8').read()

old = "            # Устанавливаем плечо\n            self.exchange.set_leverage(leverage, symbol)"
new = """            # Устанавливаем плечо (игнорируем, если оно уже такое)
            try:
                self.exchange.set_leverage(leverage, symbol)
            except Exception as e:
                if '110043' not in str(e) and 'leverage not modified' not in str(e).lower():
                    raise"""

if old in c:
    c = c.replace(old, new)
    open(p, 'w', encoding='utf-8').write(c)
    print('✅ Исправлено: игнорируем ошибку leverage not modified')
else:
    print('⚠️ Шаблон не найден')