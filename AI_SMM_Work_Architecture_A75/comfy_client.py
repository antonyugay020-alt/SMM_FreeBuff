#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI API Client. Auto-detects SDXL/SD1.5 + auto-upscale if model present."""

import json, time, uuid, urllib.request, urllib.parse, logging
from pathlib import Path

logger = logging.getLogger(__name__)
CKPT_DIR = Path(r"C:\ComfyUI_windows_portable\ComfyUI\models\checkpoints")
UP_DIR = Path(r"C:\ComfyUI_windows_portable\ComfyUI\models\upscale_models")
SDXL_KW = ('juggernaut', 'realvis', 'sdxl', 'xl')


class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.output_dir = Path(__file__).resolve().parent.parent / "data" / "generated_images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _detect_mode(self):
        files = sorted(CKPT_DIR.glob("*.safetensors"))
        sdxl = [f for f in files if any(k in f.name.lower() for k in SDXL_KW)]
        if sdxl:
            return sdxl[0].name, True
        return (files[0].name if files else None), False

    def _detect_upscaler(self):
        exts = ("*.pth", "*.pt", "*.safetensors")
        for e in exts:
            got = sorted(UP_DIR.glob(e))
            if got:
                return got[0].name
        return None

    def _detect_controlnet(self):
        root = CKPT_DIR.parent / "controlnet"
        got = [f for f in root.rglob("*") if f.is_file() and "canny" in f.name.lower()]
        if not got:
            return None
        return got[0].relative_to(root).as_posix()

    def _queue_prompt(self, prompt):
        data = json.dumps({"prompt": prompt, "client_id": self.client_id}).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt",
                                     data=data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8')).get('prompt_id')
        except Exception as e:
            logger.error(f"queue fail: {e}"); return None

    def _get_history(self, pid):
        try:
            with urllib.request.urlopen(f"http://{self.server_address}/history/{pid}", timeout=10) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"history fail: {e}"); return None

    def _get_image(self, filename, subfolder="", folder_type="output"):
        params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
        try:
            with urllib.request.urlopen(f"http://{self.server_address}/view?{params}", timeout=30) as r:
                return r.read()
        except Exception as e:
            logger.error(f"image fail: {e}"); return None

    def _wait(self, pid, timeout=240):
        t0 = time.time()
        while time.time() - t0 < timeout:
            h = self._get_history(pid)
            if h and pid in h:
                return True
            time.sleep(1)
        return False

    def generate_image(self, positive_prompt, negative_prompt="blurry, low quality, distorted, watermark",
                       checkpoint=None, width=None, height=None, steps=None, cfg=None, seed=None,
                       upscale=True, control_scheme=None):
        model, is_sdxl = self._detect_mode()
        if checkpoint is None:
            checkpoint = model
        if not checkpoint:
            logger.error("No checkpoint found"); return None

        up_name = self._detect_upscaler() if upscale else None

        if is_sdxl:
            width = width or 1024; height = height or 1024
            steps = steps or 28; cfg = cfg or 6.5
            sampler, sched = "dpmpp_2m", "karras"
        else:
            width = width or 512; height = height or 512
            steps = steps or 20; cfg = cfg or 7.5
            sampler, sched = "euler", "normal"

        if seed is None:
            seed = int(time.time() * 1000) % (2**32)

        # base chain: ckpt -> sampler -> vae decode -> (upscale?) -> save
        wf = {
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive_prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_prompt, "clip": ["4", 1]}},
            "3": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": cfg, "sampler_name": sampler,
                "scheduler": sched, "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        }

        if up_name:
            wf["10"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": up_name}}
            wf["11"] = {"class_type": "ImageUpscaleWithModel", "inputs": {
                "upscale_model": ["10", 0], "image": ["8", 0]}}
            wf["9"] = {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": "sdxl_up"}}
        else:
            wf["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "sdxl_gen"}}

        if control_scheme == "court":
            try:
                import court_scheme
                sp = court_scheme.ensure_scheme()
                cname = self._detect_controlnet()
                if cname:
                    wf["20"] = {"class_type": "LoadImage", "inputs": {"image": sp.name}}
                    wf["21"] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": cname}}
                    wf["22"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
                        "strength": 0.85, "start_percent": 0.0, "end_percent": 0.75,
                        "positive": ["6", 0], "negative": ["7", 0],
                        "control_net": ["21", 0], "image": ["20", 0]}}
                    wf["3"]["inputs"]["positive"] = ["22", 0]
                    wf["3"]["inputs"]["negative"] = ["22", 1]
                    logger.info(f"controlnet armed: {cname}")
                else:
                    logger.warning("no canny controlnet found, skipping control")
            except Exception as e:
                logger.warning(f"controlnet setup failed: {e}")
        pid = None
        if "21" in wf:
            base = wf["21"]["inputs"]["control_net_name"]
            for alt in (base, base.replace("/", "\\"), base.split("/")[-1]):
                wf["21"]["inputs"]["control_net_name"] = alt
                pid = self._queue_prompt(wf)
                if pid:
                    break
        else:
            pid = self._queue_prompt(wf)
        if not pid: return None
        logger.info(f"queued {pid} | model={checkpoint} | sdxl={is_sdxl} | upscaler={up_name} | {width}x{height}")
        if not self._wait(pid): return None

        h = self._get_history(pid)
        if not h or pid not in h: return None
        outs = h[pid].get('outputs', {})
        imgs = outs.get('9', {}).get('images', [])
        if not imgs: return None
        b = self._get_image(imgs[0]['filename'], imgs[0].get('subfolder', ''))
        if not b: return None
        p = self.output_dir / f"gen_{seed}.png"
        p.write_bytes(b)
        try:
            from memory_core import log_generation
            log_generation(p.name, positive_prompt, model=checkpoint, sdxl=str(is_sdxl), status="ok")
        except Exception:
            pass
        return p

    def check_connection(self):
        try:
            with urllib.request.urlopen(f"http://{self.server_address}/system_stats", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False


if __name__ == "__main__":
    c = ComfyUIClient()
    if not c.check_connection():
        print("✗ ComfyUI не отвечает (порт 8188)."); raise SystemExit(1)
    model, sdxl = c._detect_mode()
    up = c._detect_upscaler()
    print("✓ ComfyUI connected")
    print(f"→ Модель: {model}")
    print(f"→ Режим: {'SDXL 1024x1024' if sdxl else 'SD1.5 512x512'}")
    print(f"→ Апскейлер: {up or 'НЕ НАЙДЕН (выход без апскейла)'}")
    res = c.generate_image(
        positive_prompt="empty tennis court, green surface, white lines, autumn trees, no people, photorealistic, highly detailed, 8k",
        negative_prompt="blurry, low quality, distorted, watermark, people, person, woman, man, face, portrait",
        control_scheme="court",
    )
    print(f"✓ Image generated: {res}" if res else "✗ Generation failed")