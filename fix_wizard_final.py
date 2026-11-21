"""Final fix with CORRECT 1-space indentation matching wizard.py."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

DST = Path(r"C:\Users\anubi\Desktop\BCC_qwen")
PY = Path(r"C:\Users\anubi\Desktop\BCC\FINAL_QA_3da12354\.check_venv\Scripts\python.exe")


def load_verify(root):
    path = Path(root) / "tools" / "verify_package.py"
    spec = importlib.util.spec_from_file_location("bcc_verify_dst", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def atomic_write(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    tmp.replace(path)


def main():
    target = DST / "bcc" / "wizard.py"
    text = target.read_text(encoding="utf-8", newline="")
    lines = text.split("\n")
    changes = 0

    # 1. Add import after config import block
    if "from .market import PublicData, DataUnavailable" not in text:
        for i, line in enumerate(lines):
            if "from .config import (" in line:
                end = i
                while end < len(lines) and ")" not in lines[end]:
                    end += 1
                lines.insert(end + 1, "from .market import PublicData, DataUnavailable")
                print("[1/3] Added import")
                changes += 1
                break

    # 2. Add validation method before commit() - using 1-space indent
    if "_validate_symbols_exist" not in text:
        for i, line in enumerate(lines):
            if line == " def commit(self):":
                method = """
 def _validate_symbols_exist(self, symbols):
  from PySide6.QtWidgets import QMessageBox, QProgressDialog
  from PySide6.QtCore import Qt
  if not symbols:
   return True
  progress = QProgressDialog("Проверка монет на Bybit...", None, 0, 0, self)
  progress.setWindowModality(Qt.WindowModal)
  progress.setWindowTitle("Проверка")
  progress.show()
  try:
   source = PublicData()
   available = []
   cursor = ""
   while True:
    params = {"category": "linear", "limit": 1000}
    if cursor:
     params["cursor"] = cursor
    response = source.get("https://api.bybit.com/v5/market/instruments-info", params, ttl=3600)
    if response.get("retCode") != 0:
     raise RuntimeError(f"Bybit API: {response.get('retMsg', 'unknown')}")
    result = response.get("result", {})
    for item in result.get("list", []):
     if item.get("status") == "Trading" and item.get("quoteCoin") == "USDT" and item.get("contractType") == "LinearPerpetual":
      available.append(item["symbol"])
    cursor = result.get("nextPageCursor", "")
    if not cursor:
     break
   source.close()
  except Exception as exc:
   progress.close()
   QMessageBox.critical(self, "Ошибка", f"Не удалось получить список монет: {exc}")
   return False
  progress.close()
  available_set = set(available)
  missing = [s for s in symbols if s not in available_set]
  if missing:
   msg = f"Следующие монеты НЕ торгуются на Bybit:\\n\\n{', '.join(missing[:20])}{'...' if len(missing) > 20 else ''}\\n\\nВсего: {len(missing)} из {len(symbols)}.\\n\\nУдалите их и попробуйте снова."
   QMessageBox.warning(self, "Несуществующие монеты", msg)
   return False
  return True
"""
                lines.insert(i, method.rstrip("\n"))
                print("[2/3] Added validation method")
                changes += 1
                break

    # 3. Modify commit() to call validation
    if "_validate_symbols_exist(symbols)" not in text:
        for i, line in enumerate(lines):
            if line == " def commit(self):":
                # Find the docstring end
                j = i + 1
                while j < len(lines) and '"""' not in lines[j]:
                    j += 1
                j += 1  # skip closing """
                # Find next non-empty line
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                # Insert validation before self.result_config = None
                indent = " "
                validation_code = f"""{indent}# Validate symbols exist on Bybit before saving
{indent}symbols = [s.strip().upper() for s in self.symbols.text().split(",") if s.strip()]
{indent}if not self._validate_symbols_exist(symbols):
{indent} return"""
                lines.insert(j, validation_code)
                print("[3/3] Modified commit()")
                changes += 1
                break

    if changes == 0:
        print("All changes already applied")
        return 0

    text = "\n".join(lines)
    compile(text, str(target), "exec")
    atomic_write(target, text)
    print(f"Applied {changes} changes + syntax PASSED")

    # Reseal manifest
    ver = load_verify(DST)
    manifest_path = DST / "SHA256_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in ver.source_inventory(DST)
    }
    atomic_write(
        manifest_path,
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )
    result = ver.verify(DST)
    print(f"Sealed: {result['verified_files']} files")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())