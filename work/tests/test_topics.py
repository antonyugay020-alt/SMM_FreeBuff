import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile, json
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from ai_core import AICore, StubProvider
from data_manager import DataManager

fails = []
TOPICS = {"topics": [
    {"topic": "Три сорта для утреннего фильтра", "rubric": "Польза", "format": "Пост"},
    {"topic": "Как мы обжариваем зерно", "rubric": "Закулисье", "format": "Reels"},
    {"topic": "Кофе с собой за 20 минут", "rubric": "Продажа", "format": "Пост"},
]}
CAPTION = "Тёплый текст подписи для гостей кофейни."

def build(replies, profile=None):
    tmp = Path(tempfile.mkdtemp(prefix="tp_"))
    dm = DataManager("p", str(tmp / "p"))
    dm.save_brand_profile(profile or {"client_name": "Пар", "niche": "кофейня", "tone_of_voice": "тёплый, без снобизма"})
    stub = StubProvider(list(replies))
    core = AICore(dm, {"monthly_budget_usd": 0}, providers=(stub, None))
    return dm, core, stub

# 1. темы от модели
dm, core, stub = build([json.dumps(TOPICS, ensure_ascii=False)])
core.handle("создай контент-план на 3 поста")
plan = dm.get_content_plan()
print("1 план:", [(i["topic"], i["rubric"], i["format"]) for i in plan])
if [i["topic"] for i in plan] != [t["topic"] for t in TOPICS["topics"]]:
    fails.append("темы от модели не попали в план")
if plan[1]["format"] != "Reels":
    fails.append("формат Reels не сохранился")
prompt = stub.calls[0][1]
if "Кофейня" not in prompt and "Пар" not in prompt:
    fails.append("бренд-профиль не попал в запрос тем")

# 2. fallback: модель не дала тем
dm2, core2, _ = build([])   # stub отвечает "{}"
core2.handle("создай контент-план на 2 поста")
plan2 = dm2.get_content_plan()
print("2 fallback:", [i["topic"] for i in plan2])
if not plan2 or "идея" not in plan2[0]["topic"]:
    fails.append("без тем от модели шаблон не сработал")

# 3. topics передан явно
dm3, core3, _ = build([])
core3.tools.create_content_plan(count=2, topics=[{"topic": "Своя тема", "rubric": "Кейс", "format": "карусель"}])
plan3 = dm3.get_content_plan()
print("3 явные темы:", [(i["topic"], i["rubric"], i["format"]) for i in plan3])
if plan3[0]["topic"] != "Своя тема" or plan3[0]["format"] != "Карусель" or plan3[0]["rubric"] != "Кейс":
    fails.append("явные темы не применились")
if plan3[1]["topic"] != "Полезное: идея 2":
    fails.append("недостающие позиции не добираются шаблоном")

# 4. промпт подписи: тон и обращение
dm4, core4, stub4 = build([CAPTION])
core4.tools.create_content_plan(count=1, topics=[{"topic": "Утренний фильтр", "rubric": "Польза"}])
core4.tools.write_captions(dm4.get_content_plan()[0]["id"])
system = stub4.calls[-1][0]
print("4 подпись, system:", system[:160], "...")
if "тёплый, без снобизма" not in system:
    fails.append("tone_of_voice не попал в промпт подписи")
if "на «вы»" not in system:
    fails.append("в промпте нет единого обращения")
if (dm4.get_content_plan()[0].get("caption") or "") != CAPTION:
    fails.append("подпись не записалась")

# 5. фраза «придумай темы»
dm5, core5, _ = build([json.dumps(TOPICS, ensure_ascii=False)])
d = core5.router.route("придумай темы для контента на неделю")
print("5 router:", d.tool, d.args)
if d.tool != "create_content_plan":
    fails.append(f"фраза «придумай темы» ушла в {d.tool}")
core5.handle("придумай темы для контента на неделю")
print("5 план:", [i["topic"] for i in dm5.get_content_plan()])

print("\nFAILS:", fails or "нет")
sys.exit(1 if fails else 0)
