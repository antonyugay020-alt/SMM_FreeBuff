"""AI Panel: Chat interface with Local LLM + Task Router + Proposal System + Auto-Distribution."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QScrollArea, QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent, QThread, QObject
from PySide6.QtGui import QFont, QColor
from comfy_client import ComfyUIClient
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication

# Imports wrapped safely
try:
    from proposal_engine import ProposalEngine, Proposal
except ImportError:
    class ProposalEngine: pass
    class Proposal: pass

try:
    from ai_task_router import AITaskRouter
except ImportError:
    class AITaskRouter: pass

try:
    from local_llm_client import LocalLLMClient
except ImportError:
    class LocalLLMClient:
        def __init__(self, *args, **kwargs): self.available = False
        def generate(self, *args, **kwargs): return None

try:
    from content_distributor import ContentDistributor
except ImportError:
    # Fallback if distributor file is missing during initial boot
    class ContentDistributor:
        def __init__(self, dm): self.dm = dm
        def distribute(self, query, resp, cat): return {"success": False, "actions": []}

from ai_core import AICore

logger = logging.getLogger(__name__)


BRIDGE_SYS = ("You rewrite a user's image request (any language) into ONE detailed English "
"prompt for Stable Diffusion XL. Describe: scene type, main subjects, exact materials and "
"surfaces, lighting, camera/lens, style, quality tags. If the request implies a real-world "
"structured object (sports court, room, vehicle, product), use its correct technical terms "
"(e.g. 'hard tennis court, acrylic surface, regulation baseline and service lines'). "
"Output ONLY the prompt text. No quotes, no preamble, no explanation, no bullet points. "
"Do not invent people unless the request asks for them.")

class _GenWorker(QObject):
    done = Signal(object)
    def __init__(self, prompt, llm=None):
        super().__init__()
        self.prompt = prompt
        self.llm = llm
    def run(self):
        try:
            final_prompt = self.prompt
            try:
                from prompt_bridge import translate_to_prompt
                rw = translate_to_prompt(self.prompt)
                if rw and rw.strip():
                    final_prompt = rw.strip().strip('"').strip()
            except Exception:
                pass
            try:
                from memory_core import log_bridge
                log_bridge(self.prompt, final_prompt)
            except Exception:
                pass
            client = ComfyUIClient()
            img = client.generate_image(
                positive_prompt=final_prompt + ", photorealistic, high quality, 8k, professional",
                negative_prompt="blurry, low quality, distorted, ugly, watermark, bad anatomy, poorly drawn, extra fingers, deformed faces",
            )
            self.done.emit(("ok", str(img)) if img else ("err", "Ошибка генерации. Проверь, что ComfyUI запущен (порт 8188)."))
        except Exception as e:
            self.done.emit(("err", f"Ошибка: {e}"))

class AIPanel(QWidget):
    """Right-side panel for AI interaction."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state if isinstance(app_state, dict) else {"config": {}}
        self.dm = self.state.get("data_manager")
        self.proposal_engine = ProposalEngine()
        self.task_router = AITaskRouter()
        
        # Connect to Local LLM (LM Studio port 1235)
        self.local_llm = LocalLLMClient(base_url="http://localhost:1235/v1")
        if getattr(self.local_llm, 'available', False):
            logger.info("Connected to Local LLM successfully!")
        else:
            logger.warning("Local LLM unavailable. Falling back to simulation.")
            
        self.ai_core = None
        self._build_ui()
        self._connect_signals()
        self.set_data_manager(self.dm)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)

        title = QLabel("🤖 AI Менеджер")
        title.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold;")
        hl.addWidget(title)
        hl.addStretch()

        self.budget_label = QLabel("")
        self.budget_label.setStyleSheet("color: #8b949e; font-size: 10px; padding-right: 8px;")
        hl.addWidget(self.budget_label)

        journal_btn = QPushButton("Журнал")
        journal_btn.setObjectName("topBtn")
        journal_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        journal_btn.clicked.connect(lambda: self._send_text("журнал"))
        hl.addWidget(journal_btn)

        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.setObjectName("topBtn")
        clear_btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        clear_btn.clicked.connect(self._clear_chat)
        hl.addWidget(clear_btn)

        layout.addWidget(header)

        # Chat Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: #0a0e13; }
            QScrollBar:vertical { 
                background-color: #121820; width: 12px; margin: 0; 
                border-radius: 6px;
            }
            QScrollBar::handle:vertical { 
                background-color: #1e252e; min-height: 30px; 
                border-radius: 6px; 
            }
            QScrollBar::handle:vertical:hover { background-color: #58a6ff; }
        """)

        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(16)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_content)
        layout.addWidget(self.chat_scroll, stretch=1)

        # Input Area
        input_frame = QFrame()
        input_frame.setObjectName("inputZone")
        input_frame.setStyleSheet("""
            QFrame#inputZone { background-color: #121820; border-top: 1px solid #1e252e; }
        """)
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(12, 12, 12, 12)
        il.setSpacing(8)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Напишите сообщение или вопрос...")
        self.input_box.setMaximumHeight(100)
        self.input_box.setStyleSheet("""
            QTextEdit { 
                background-color: #0a0e13; color: #c9d1d9; 
                border: 1px solid #1e252e; border-radius: 4px; 
                padding: 10px; font-size: 13px; 
            }
            QTextEdit:focus { border-color: #58a6ff; }
        """)
        il.addWidget(self.input_box, stretch=1)

        send_btn = QPushButton("➤ Отправить")
        send_btn.setObjectName("primaryBtn")
        send_btn.setProperty("class", "primary")
        send_btn.setStyleSheet("""
            QPushButton#primaryBtn { 
                background-color: #238636; color: white; 
                border: none; border-radius: 4px; 
                padding: 10px 16px; font-weight: bold;
            }
            QPushButton#primaryBtn:hover { background-color: #2ea043; }
        """)
        send_btn.clicked.connect(self.send_message)
        il.addWidget(send_btn)

        layout.addWidget(input_frame)

    def _connect_signals(self):
        self.input_box.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.input_box and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def _add_image_bubble(self, image_path: str):
        """Add generated image to chat with proper sizing."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Adding image bubble: {image_path}")
        
        frame = QFrame()
        frame.setStyleSheet("background-color: #2d333b; border-radius: 8px; margin: 4px; padding: 8px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            logger.info(f"Image loaded: {pixmap.width()}x{pixmap.height()}")
            # Scale to max 512px width, keep aspect ratio
            scaled = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)
            label.setFixedSize(scaled.size())
        else:
            label.setText("❌ Ошибка загрузки изображения")
            logger.error(f"Failed to load image: {image_path}")
            
        layout.addWidget(label)
        
        # Insert before stretch (at the end, but before addStretch)
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, frame)
        
        # Scroll to bottom
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
        logger.info("Image bubble added successfully")


    def _on_gen_done(self, result):
        self._gen_busy = False
        kind, payload = result
        if kind == "ok":
            self._add_image_bubble(payload)
            self._add_bubble("system", "✅ Изображение сгенерировано!")
        else:
            self._add_bubble("system", f"❌ {payload}")

    def send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        # Check for image generation request (async, non-blocking)
        lower_text = text.lower()
        if any(kw in lower_text for kw in ["сгенерируй картинку", "сгенерируй изображение", "нарисуй", "создай картинку", "сгенерируй фото"]):
            if getattr(self, "_gen_busy", False):
                self._add_bubble("system", "⏳ Уже генерирую предыдущий запрос, подожди окончания.")
                return
            prompt = text
            for kw in ["сгенерируй картинку:", "сгенерируй изображение:", "нарисуй:", "создай картинку:", "сгенерируй фото:"]:
                if kw in lower_text:
                    prompt = text.split(kw, 1)[-1].strip()
                    break
            self._gen_busy = True
            self._add_bubble("system", f"🎨 Генерирую: «{prompt}»... (SDXL + апскейл, 1–2 мин; чат не замерзнет)")
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
            self._gen_thread = QThread()
            self._gen_worker = _GenWorker(prompt, getattr(self, 'local_llm', None))
            self._gen_worker.moveToThread(self._gen_thread)
            self._gen_thread.started.connect(self._gen_worker.run)
            self._gen_worker.done.connect(self._on_gen_done)
            self._gen_worker.done.connect(self._gen_thread.quit)
            self._gen_thread.finished.connect(self._gen_thread.deleteLater)
            self._gen_thread.start()
            return

        
        self._add_bubble("user", text)
        self.input_box.clear()
        QTimer.singleShot(0, lambda: self._on_ai_reply(text))

    # === AI core bridge ===
    def set_data_manager(self, dm):
        """Rebind the core when the project changes."""
        self.dm = dm
        if dm is None:
            self.ai_core = None
            return
        self.ai_core = AICore(dm, self.state.get("settings"))
        self.ai_core.on_change = self._refresh_workspace
        self._update_budget()

    def _send_text(self, text: str):
        self._add_bubble("user", text)
        self._on_ai_reply(text)

    def _on_ai_reply(self, text: str):
        if self.ai_core is None:
            self._add_bubble("assistant", "Ядро AI не подключено: нет проекта.")
            return
        try:
            reply = self.ai_core.handle(text)
        except Exception as exc:
            logger.exception("ai core failed")
            self._add_bubble("assistant", f"Ошибка ядра AI: {exc}")
            return

        self._add_bubble("assistant", reply.text)
        for action in reply.actions or []:
            self._add_action_row(action)
        self._update_budget()
        if reply.actions:
            self._refresh_workspace()
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum())

    def _add_action_row(self, action: Dict[str, Any]):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = QLabel(f"↩ {action.get('tool')}: {action.get('summary', '')[:60]}")
        label.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(label, stretch=1)
        if action.get("id"):
            undo_btn = QPushButton("Отменить")
            undo_btn.setObjectName("topBtn")
            undo_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
            undo_btn.clicked.connect(lambda checked=False, aid=action["id"]: self._undo(aid))
            layout.addWidget(undo_btn)
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, row)

    def _undo(self, action_id: str):
        if self.ai_core is None:
            return
        reply = self.ai_core.undo(action_id)
        self._add_bubble("assistant", reply.text)
        self._refresh_workspace()

    def _update_budget(self):
        if not self.ai_core:
            self.budget_label.setText("")
            return
        try:
            spent = self.ai_core.budget.spent_month()
            limit = self.ai_core.budget.limit
            self.budget_label.setText(f"{spent:.2f} $ / {limit:.0f} $")
        except Exception:
            self.budget_label.setText("")

    def _refresh_workspace(self):
        win = self.window()
        if hasattr(win, "refresh_stats"):
            win.refresh_stats()
        if hasattr(win, "current_section"):
            win._on_nav(win.current_section)
    
    def _build_system_prompt(self):
        """Base system prompt enriched with live project context."""
        base = ("Ты опытный SMM менеджер и стратег. Помогай пользователю создавать кампании, "
                "стратегии и контент-планы на русском языке. Будь лаконичен, но информативен.")
        try:
            from project_context_builder import build_context
            win = self.window()
            dm = getattr(win, "data_manager", None)
            if dm is None and isinstance(self.state, dict):
                dm = self.state.get("data_manager")
            if dm is not None:
                ctx = build_context(dm)
                if ctx:
                    logger.info(f"Injected project context: {len(ctx)} chars")
                    return base + "\n\nКОНТЕКСТ ПРОЕКТА (учитывай его в ответах):\n" + ctx
        except Exception as e:
            logger.warning(f"Context build failed: {e}")
        return base

    def _add_bubble(self, role: str, text: str, timestamp: str = ""):
        """Add a chat bubble to the UI with PROPER WORD WRAP."""
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")

        if role == "assistant":
            icon = "🤖 AI"
            bg_color = "#2d2d30"
            text_color = "#e0e0e0"
            align = Qt.AlignLeft
        elif role == "user":
            icon = "👤 Вы"
            bg_color = "#1f6feb"
            text_color = "#ffffff"
            align = Qt.AlignRight
        else:
            icon = "ℹ️ Система"
            bg_color = "#9e6a03"
            text_color = "#ffffff"
            align = Qt.AlignCenter

        container = QWidget()
        cl = QHBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        
        if align == Qt.AlignRight:
            cl.addStretch()
        elif align == Qt.AlignCenter:
            cl.addStretch()

        bubble = QFrame()
        bubble.setStyleSheet(f"""
            QFrame {{ 
                background-color: {bg_color}; 
                border-radius: 8px; 
                padding: 12px; 
            }}
        """)
        bl = QVBoxLayout(bubble)
        bl.setSpacing(6)

        hdr = QLabel(f"{icon}  ·  {timestamp}")
        hdr.setStyleSheet(f"color: {'rgba(255,255,255,0.7)' if role=='user' else '#8b949e'}; font-size: 11px; font-weight: bold;")
        bl.addWidget(hdr)

        txt = QLabel(text)
        txt.setWordWrap(True)
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse)
        txt.setStyleSheet(f"""
            color: {text_color}; 
            font-size: 13px; 
            font-family: 'Segoe UI', sans-serif; 
            line-height: 1.5;
            padding: 4px 0;
        """)
        bl.addWidget(txt)

        cl.addWidget(bubble)
        
        if align == Qt.AlignLeft:
            cl.addStretch()

        insert_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_index, container)
        
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _show_proposal_card(self, proposal: Proposal):
        """Render interactive proposal card with COMPACT DESIGN."""
        card = QFrame()
        card.setObjectName("proposalCard")
        card.setStyleSheet("""
            QFrame#proposalCard {
                background-color: #1c2333;
                border: 2px solid #58a6ff;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
            }
            QLabel#proposalTitle {
                color: #e6edf3;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 8px;
            }
            QLabel#proposalContext {
                color: #8b949e;
                font-size: 12px;
                margin-bottom: 12px;
                font-style: italic;
            }
            QFrame#optionRow {
                background-color: #0a0e13;
                border: 1px solid #1e252e;
                border-radius: 6px;
                padding: 10px;
                margin: 8px 0;
            }
            QFrame#optionRow:hover {
                border-color: #58a6ff;
            }
            QLabel#optionTitle {
                color: #58a6ff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 6px;
            }
            QLabel#optionDesc {
                color: #c9d1d9;
                font-size: 12px;
                margin-bottom: 8px;
                line-height: 1.4;
            }
            QLabel#proLabel {
                color: #238636;
                font-size: 11px;
            }
            QLabel#conLabel {
                color: #da3633;
                font-size: 11px;
            }
            QPushButton#chooseBtn {
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#chooseBtn:hover {
                background-color: #2ea043;
            }
            QPushButton#dismissBtn {
                background-color: transparent;
                color: #8b949e;
                border: 1px solid #1e252e;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton#dismissBtn:hover {
                border-color: #8b949e;
                color: #c9d1d9;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        # Title
        title_lbl = QLabel(proposal.question)
        title_lbl.setObjectName("proposalTitle")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        
        # Context
        if proposal.context:
            ctx_lbl = QLabel(f"Контекст: {proposal.context}")
            ctx_lbl.setObjectName("proposalContext")
            ctx_lbl.setWordWrap(True)
            layout.addWidget(ctx_lbl)
        
        # Options Container (NO internal scroll - compact design)
        for opt in proposal.options:
            row = QFrame()
            row.setObjectName("optionRow")
            row_layout = QVBoxLayout(row)
            row_layout.setSpacing(6)
            
            # Option title + recommended badge
            hdr = QHBoxLayout()
            opt_title = QLabel(opt.title)
            opt_title.setObjectName("optionTitle")
            opt_title.setWordWrap(True)
            hdr.addWidget(opt_title)
            
            if opt.recommended:
                rec_badge = QLabel("⭐ Рекомендация")
                rec_badge.setStyleSheet("background-color:#9e6a03;color:white;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;")
                hdr.addWidget(rec_badge)
            
            hdr.addStretch()
            row_layout.addLayout(hdr)
            
            # Description
            desc_lbl = QLabel(opt.description)
            desc_lbl.setObjectName("optionDesc")
            desc_lbl.setWordWrap(True)
            row_layout.addWidget(desc_lbl)
            
            # Pros/Cons
            if opt.pros or opt.cons:
                pc_layout = QHBoxLayout()
                if opt.pros:
                    pro_txt = "✅ " + " · ".join(opt.pros)
                    pro_lbl = QLabel(pro_txt)
                    pro_lbl.setObjectName("proLabel")
                    pro_lbl.setWordWrap(True)
                    pc_layout.addWidget(pro_lbl)
                
                if opt.cons:
                    con_txt = "❌ " + " · ".join(opt.cons)
                    con_lbl = QLabel(con_txt)
                    con_lbl.setObjectName("conLabel")
                    con_lbl.setWordWrap(True)
                    pc_layout.addWidget(con_lbl)
                
                row_layout.addLayout(pc_layout)
            
            # Choose button
            choose_btn = QPushButton("Выбрать этот вариант")
            choose_btn.setObjectName("chooseBtn")
            pid = proposal.id
            oid = opt.id
            choose_btn.clicked.connect(lambda checked, p=pid, o=oid: self._on_choose_option(p, o))
            row_layout.addWidget(choose_btn)
            
            layout.addWidget(row)
        
        # Dismiss button
        dismiss_btn = QPushButton("Отклонить все предложения")
        dismiss_btn.setObjectName("dismissBtn")
        pid_dismiss = proposal.id
        dismiss_btn.clicked.connect(lambda checked, p=pid_dismiss: self._on_dismiss_proposal(p))
        layout.addWidget(dismiss_btn)
        
        insert_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_index, card)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _on_choose_option(self, proposal_id: str, option_id: str):
        success = self.proposal_engine.resolve(proposal_id, option_id)
        if success:
            confirm_msg = f"[Пользователь выбрал вариант {option_id} из предложения {proposal_id}]"
            self._add_bubble("system", confirm_msg)
            logger.info(f"User chose {option_id} from {proposal_id}")
        else:
            logger.warning(f"Failed to resolve proposal {proposal_id}")

    def _on_dismiss_proposal(self, proposal_id: str):
        prop = self.proposal_engine.proposals.get(proposal_id)
        if prop:
            prop.resolved = True
            prop.chosen_option_id = None
            self._add_bubble("system", f"[Предложение {proposal_id} отклонено]")
            logger.info(f"Proposal {proposal_id} dismissed")

    def _clear_chat(self):
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.chat_layout.addStretch()
        self.proposal_engine.proposals.clear()
        logger.info("Chat cleared")
