import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

e = ccxt.bybit({
    'options': {'defaultType': 'swap'},
    'apiKey': os.getenv('BYBIT_API_KEY'),
    'secret': os.getenv('BYBIT_API_SECRET')
})
e.urls['api'] = {'public': 'https://api-demo.bybit.com', 'private': 'https://api-demo.bybit.com'}
e.has['fetchCurrencies'] = False
e.load_markets()

positions = e.fetch_positions()
print("Открытые позиции на бирже:")
for p in positions:
    if float(p.get('contracts', 0) or 0) > 0:
        print(f"Символ: '{p['symbol']}' | Сторона: {p['side']} | Объем: {p['contracts']}")