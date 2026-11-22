import sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(ROOT))
from data_manager import DataManager
from ai_core import AICore


def ok(name, cond, extra=""):
    print(("D2_OK " if cond else "D2_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


class FakeCloudinary:
    def __init__(self):
        self.uploads = []
        self.deleted = []

    def upload(self, file_path, public_id):
        self.uploads.append((file_path, public_id))
        return {"url": f"https://res.cloudinary.com/demo/image/upload/{public_id}.jpg",
                "public_id": public_id, "resource_type": "image"}

    def delete(self, public_id, resource_type="image"):
        self.deleted.append((public_id, resource_type))
        return True


class BrokenCloudinary(FakeCloudinary):
    def upload(self, file_path, public_id):
        raise RuntimeError("Cloudinary отклонил загрузку (401): Invalid Signature")


tmp = Path(tempfile.mkdtemp(prefix="d2_"))
photo = tmp / "пляж.jpg"; photo.write_bytes(b"JPEG" * 100)
dm = DataManager("d2", str(tmp / "proj"))
core = AICore(dm, {"monthly_budget_usd": 0})
dm._data["media_ready"].append({"id": "m1", "name": "пляж.jpg", "type": "image",
                                "path": str(photo), "status": "approved"})
dm.save()

fake = FakeCloudinary()
core.tools.cloudinary = fake
r = core.run_tool("host_media", media_id="m1")
record = dm.get_media_ready()[0]
ok("url записан в запись", record["remote_url"].startswith("https://res.cloudinary.com/"),
   record)
ok("public_id записан", bool(record["remote_public_id"]), record)
ok("операция отмечена", "hosted" in (record.get("processed") or []), record)
ok("файл загружен один раз", len(fake.uploads) == 1, fake.uploads)
ok("отчёт короткий", "публичный URL" in r.text.splitlines()[0], r.text)
entries = [e for e in core.journal.list(5) if e["tool"] == "host_media"]
ok("журнал", len(entries) == 1, entries)

dm2 = DataManager("d2", str(tmp / "proj"))
ok("url переживает перезапуск",
   dm2.get_media_ready()[0]["remote_url"] == record["remote_url"], dm2.get_media_ready()[0])

core.undo(entries[0]["id"])
ok("откат удалил файл с хостинга", fake.deleted and fake.deleted[0][0] == record["remote_public_id"],
   fake.deleted)
ok("откат стёр url", not dm.get_media_ready()[0].get("remote_url"), dm.get_media_ready()[0])

core.tools.cloudinary = BrokenCloudinary()
r = core.run_tool("host_media", media_id="m1")
ok("ошибка хостинга без записи в журнал",
   "Cloudinary не принял файл" in r.text
   and len([e for e in core.journal.list(5) if e["tool"] == "host_media"]) == 1, r.text)

core.tools.cloudinary = None
r = core.run_tool("host_media", media_id="m1")
ok("без ключей — честный отказ", "CLOUDINARY_CLOUD_NAME" in r.text, r.text)

r = core.run_tool("host_media", media_id="нет")
ok("неизвестный материал", "не найден" in r.text, r.text)

dm._data["media_ready"][0]["path"] = str(tmp / "нет.jpg")
dm.save()
core.tools.cloudinary = FakeCloudinary()
r = core.run_tool("host_media", media_id="m1")
ok("нет файла — отказ", "файл не найден" in r.text, r.text)

import cloudinary_client
ok("ресурс по расширению", cloudinary_client.resource_type_for(Path("a.mp4")) == "video"
   and cloudinary_client.resource_type_for(Path("a.jpg")) == "image"
   and cloudinary_client.resource_type_for(Path("a.pdf")) == "raw")
ok("без env — нет клиента", cloudinary_client.CloudinaryClient.from_env() is None)
print("D2_OK")
