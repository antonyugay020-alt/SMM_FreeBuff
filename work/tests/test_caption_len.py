import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile, json
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from ai_core import AICore, StubProvider, CAPTION_LIMIT, _shorten_caption
from data_manager import DataManager

fails = []
def build(replies):
    tmp = Path(tempfile.mkdtemp(prefix="tc_"))
    dm = DataManager("p", str(tmp / "p"))
    dm.save_brand_profile({"client_name": "Пар", "niche": "кофейня", "tone_of_voice": "тёплый"})
    stub = StubProvider(list(replies))
    return AICore(dm, {"monthly_budget_usd": 0}, providers=(stub, None)), stub

SHORT = "Заходите на свежую обжарку до 10:00. #кофе"
LONG = "Мы обжариваем зерно каждое утро, чтобы у вас была свежая чашка. " * 7 + "#кофе #пар"

# 1. короткая подпись не трогается и лишнего запроса нет
core, stub = build([SHORT])
out = core.router.write_caption("тема: утренний фильтр")
print("1 len:", len(out), "calls:", len(stub.calls), "|", out[:40])
if out != SHORT: fails.append("короткая подпись изменилась")
if len(stub.calls) != 1: fails.append("лишний запрос на короткой подписи")

# 2. длинная -> повторный проход даёт укладывающийся вариант
core2, stub2 = build([LONG, SHORT])
out2 = core2.router.write_caption("тема: закулисье")
print("2 len:", len(out2), "calls:", len(stub2.calls))
if out2 != SHORT: fails.append("повторный проход не принят")
if len(stub2.calls) != 2: fails.append("нет повторного запроса")
if "400" not in stub2.calls[1][1] and "400" not in stub2.calls[1][0]:
    fails.append("в повторном запросе нет лимита 400")

# 3. повторный проход тоже длинный -> обрезка по предложению
core3, _ = build([LONG, LONG])
out3 = core3.router.write_caption("тема: закулисье")
print("3 len:", len(out3), "| хвост:", repr(out3[-30:]))
if len(out3) > CAPTION_LIMIT: fails.append("обрезка по предложению не уложилась в 400")
if not out3.endswith(".") and not out3.endswith("!"):
    fails.append("обрезка не по границе предложения")

# 4. одно длинное предложение -> обрезка по слову
core4, _ = build(["а" * 600, "б" * 600])
out4 = core4.router.write_caption("тема: длинная")
print("4 len:", len(out4), "| хвост:", repr(out4[-6:]))
if len(out4) > CAPTION_LIMIT: fails.append("обрезка по слову не уложилась в 400")

# 5. ровно 400 не трогаем
exact = "я" * 400
core5, stub5 = build([exact])
out5 = core5.router.write_caption("тема: ровно")
if out5 != exact or len(stub5.calls) != 1:
    fails.append("ровно 400 символов обработаны неверно")

# 6. промпт тем: про гостя, без домашней обжарки
tmp6 = Path(tempfile.mkdtemp(prefix="tc6_"))
dm6 = DataManager("p", str(tmp6 / "p"))
dm6.save_brand_profile({"client_name": "Пар", "niche": "кофейня", "tone_of_voice": "тёплый"})
stub6 = StubProvider([json.dumps({"topics": [{"topic": "Три сорта утреннего фильтра", "rubric": "Польза", "format": "Пост"}]}, ensure_ascii=False)])
core6 = AICore(dm6, {"monthly_budget_usd": 0}, providers=(stub6, None))
core6.handle("создай контент-план на 1 пост")
sysprompt = stub6.calls[0][0]
print("6 темы:", [i["topic"] for i in dm6.get_content_plan()])
if "про гостя и его выгоду" not in sysprompt: fails.append("в промпте тем нет требования про выгоду гостя")
if "обжаривает кофе дома" not in sysprompt: fails.append("в промпте тем нет запрета на домашнюю обжарку")

# 7. прямой вызов обрезки: несколько предложений
multi = "Первое предложение о кофе. Второе предложение о бариста. Третье предложение о десерте. " * 5
cut = _shorten_caption(multi)
print("7 len:", len(cut), "| последнее слово:", repr(cut[-25:]))
if len(cut) > CAPTION_LIMIT or not cut.endswith("."): fails.append("_shorten_caption обрезал не по предложению")

print("FAILS:", fails or "нет")
sys.exit(1 if fails else 0)
