import openai
import yaml
from pathlib import Path

config_path = Path("config/config.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

api_key = config.get("openai", {}).get("api_key", "")

if api_key:
    client = openai.OpenAI(api_key=api_key)
    try:
        models = client.models.list()
        print("Доступные модели OpenAI:")
        for model in sorted(models.data, key=lambda x: x.id):
            print(f"  - {model.id}")
    except Exception as e:
        print(f"Ошибка: {e}")
else:
    print("API ключ не найден в config.yaml")