#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean rewrite of gui_ai_panel.py. No patching, no broken scopes.
Run: python fix_ai_panel_clean.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Clean Rewrite: gui_ai_panel.py ===\n")

ai_panel_code = r'''"""AI Panel: Chat interface with Local LLM + Task Router + Proposal System."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QScrollArea, QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QFont, QColor

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

logger = logging.getLogger(__name__)


class AIPanel(QWidget):
    """Right-side panel for AI interaction."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.proposal_engine = ProposalEngine()
        self.task_router = AITaskRouter()
        
        # Connect to Local LLM (LM Studio port 1235)
        self.local_llm = LocalLLMClient(base_url="http://localhost:1235/v1")
        if getattr(self.local_llm, 'available', False):
            logger.info("Connected to Local LLM successfully!")
        else:
            logger.warning("Local LLM unavailable. Falling back to simulation.")
            
        self._build_ui()
        self._connect_signals()

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
            QScrollArea { border: none; background-color: #0d1117; }
            QScrollBar:vertical { 
                background-color: #161b22; width: 12px; margin: 0; 
                border-radius: 6px;
            }
            QScrollBar::handle:vertical { 
                background-color: #30363d; min-height: 30px; 
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
            QFrame#inputZone { background-color: #161b22; border-top: 1px solid #30363d; }
        """)
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(12, 12, 12, 12)
        il.setSpacing(8)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Напишите сообщение или вопрос...")
        self.input_box.setMaximumHeight(100)
        self.input_box.setStyleSheet("""
            QTextEdit { 
                background-color: #0d1117; color: #c9d1d9; 
                border: 1px solid #30363d; border-radius: 4px; 
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
                padding: 10px 16px; font-weight: bold; cursor: pointer; 
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

    def send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        
        self._add_bubble("user", text)
        self.input_box.clear()

        # Check if this looks like a complex task requiring routing
        lower_text = text.lower()
        is_complex_task = any(kw in lower_text for kw in [
            "создай кампанию", "разработай стратегию", "подготовь контент",
            "сгенерируй изображения", "обнови позиционирование"
        ])
        
        if is_complex_task:
            # Route through task parser
            QTimer.singleShot(500, lambda: self._handle_routed_request(text))
        else:
            # Standard simulated response
            QTimer.singleShot(500, lambda: self._simulate_response(text))
    
    def _handle_routed_request(self, user_text: str):
        """Process request through AI Task Router."""
        # Parse request into sub-tasks
        parsed = self.task_router.parse_request(user_text, project_context=self.state)
        
        # Show planning message
        plan_msg = f"🧠 Проанализировал ваш запрос. Составил план из {len(parsed.sub_tasks)} этапов:"
        self._add_bubble("assistant", plan_msg)
        
        # Display each sub-task briefly
        for i, task in enumerate(parsed.sub_tasks, 1):
            short_desc = task.description[:80] + ("..." if len(task.description) > 80 else "")
            detail_msg = f"{i}. [{task.task_type.upper()}] → {short_desc}"
            self._add_bubble("system", detail_msg)
        
        # Execute simulation (would be replaced by real AI/tools later)
        exec_result = self.task_router.execute_parsed_request(parsed, self.dm if hasattr(self, 'dm') else None)
        
        completion_msg = f"✅ План выполнен! Завершено: {exec_result['completed']} из {exec_result['total_tasks']} задач."
        self._add_bubble("assistant", completion_msg)
        
        # Optionally show detailed breakdown
        details_toggle = QPushButton("Показать детали выполнения")
        details_toggle.setObjectName("topBtn")
        details_toggle.setStyleSheet("font-size: 11px; padding: 4px 8px; margin-top: 8px;")
        details_toggle.clicked.connect(lambda: self._show_execution_details(exec_result))
        
        # Insert toggle button before stretch
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, details_toggle)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
    
    def _show_execution_details(self, exec_result: Dict[str, Any]):
        """Show collapsible details of executed tasks."""
        details_frame = QFrame()
        details_frame.setObjectName("detailsPanel")
        details_frame.setStyleSheet("""
            QFrame#detailsPanel {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 12px;
                margin: 8px 0;
            }
            QLabel#detailTitle {
                color: #58a6ff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 8px;
            }
            QTextEdit#detailContent {
                background-color: #0d1117;
                color: #c9d1d9;
                border: none;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        
        dl = QVBoxLayout(details_frame)
        dl.setSpacing(8)
        
        title = QLabel("Детали выполнения")
        title.setObjectName("detailTitle")
        dl.addWidget(title)
        
        content = QTextEdit()
        content.setObjectName("detailContent")
        content.setReadOnly(True)
        content.setMaximumHeight(200)
        
        # Format JSON-like output
        import json
        formatted = json.dumps(exec_result, indent=2, ensure_ascii=False)
        content.setPlainText(formatted)
        
        dl.addWidget(content)
        
        close_btn = QPushButton("✖ Скрыть детали")
        close_btn.setObjectName("topBtn")
        close_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; align-self: flex-end;")
        close_btn.clicked.connect(lambda: details_frame.deleteLater())
        dl.addWidget(close_btn)
        
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, details_frame)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _simulate_response(self, user_input: str):
        """Generate response using Local LLM or fallback to mock."""
        lower_input = user_input.lower()
        
        # ATTEMPT REAL GENERATION VIA LOCAL LLM FIRST
        if hasattr(self, 'local_llm') and getattr(self.local_llm, 'available', False):
            sys_prompt = ("Ты опытный SMM менеджер и стратег. Помогай пользователю создавать кампании, "
                          "стратегии и контент-планы на русском языке. Будь лаконичен, но информативен.")
            
            try:
                # Blocking call acceptable for short queries; consider threading for long ones later
                real_resp = self.local_llm.generate(user_input, system_prompt=sys_prompt)
                
                if real_resp and len(real_resp.strip()) > 10:
                    self._add_bubble("assistant", real_resp)
                    
                    # SAFE CATEGORY DETECTION INLINE (No external method calls!)
                    lc = user_input.lower()
                    cat = "general"
                    if any(w in lc for w in ['стратег', 'позицион']): cat = "strategy"
                    elif any(w in lc for w in ['контент', 'план']): cat = "content_plan"
                    elif any(w in lc for w in ['съёмк', 'фото', 'видео']): cat = "shooting"
                    elif any(w in lc for w in ['обработ', 'фильтр']): cat = "processing"
                    
                    proposal = self.proposal_engine.create_from_ai_response(real_resp, context=user_input, category=cat)
                    if proposal:
                        self._show_proposal_card(proposal)
                        
                    logger.info("Used REAL Local LLM response.")
                    return  # Exit early – no need for mocks
                    
            except Exception as ex:
                logger.warning(f"Local LLM attempt failed gracefully falling back: {ex}")
        
        # ORIGINAL MOCK LOGIC BELOW (unchanged behavior when offline/error)
        if "вариант" in lower_input or "идея" in lower_input or "стратегия" in lower_input:
            response = f"""Я проанализировал ваш запрос «{user_input}». Вот несколько вариантов решения:

Вариант 1: Агрессивный маркетинг
Описание: Фокус на быстрых результатах и скидках.
Плюсы: Быстрый рост базы клиентов.
Минусы: Низкая лояльность, демпинг цен.

Вариант 2: Премиум позиционирование
Описание: Акцент на эксклюзивности и качестве сервиса.
Плюсы: Высокий средний чек, лояльная аудитория.
Минусы: Долгий цикл продаж.

Вариант 3: Гибридный подход
Описание: Баланс между доступностью и качеством.
Плюсы: Универсальность.
Минусы: Размытое позиционирование."""
            
            self._add_bubble("assistant", response)
            
            proposal = self.proposal_engine.create_from_ai_response(response, context=user_input, category="strategy")
            if proposal:
                self._show_proposal_card(proposal)
                
        else:
            response = f"AI получил сообщение: «{user_input}». Это тестовый режим."
            self._add_bubble("assistant", response)

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
                background-color: #0d1117;
                border: 1px solid #30363d;
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
                border: 1px solid #30363d;
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
'''

write("gui_ai_panel.py", ai_panel_code)

# Verify compilation before finishing
try:
    compile(ai_panel_code, "gui_ai_panel.py", 'exec')
    print("\n[SUCCESS] File compiles without errors!")
except SyntaxError as e:
    print(f"\n[CRITICAL ERROR] Compilation still fails at line {e.lineno}: {e.msg}")
    print(f"  Problematic text: {e.text}")

print("\nRun START.bat now!")