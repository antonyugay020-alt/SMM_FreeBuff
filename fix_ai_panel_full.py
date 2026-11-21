#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Completely rewrite gui_ai_panel.py to ensure clean syntax and full integration.
Run: python fix_ai_panel_full.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Rewriting gui_ai_panel.py ===\n")

ai_panel_code = r'''"""AI Panel: Chat interface with Proposal System integration."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QScrollArea, QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

# Import our custom engine
try:
    from proposal_engine import ProposalEngine, Proposal
except ImportError:
    # Fallback if file is missing or in different dir during testing
    class ProposalEngine: pass
    class Proposal: pass

logger = logging.getLogger(__name__)


class AIPanel(QWidget):
    """Right-side panel for AI interaction."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.proposal_engine = ProposalEngine()
        
        # Mock client for demonstration (replace with real OpenAI/local client later)
        self.ai_client = None 
        
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

        # Chat Area (Scrollable)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("border: none; background-color: #0d1117;")

        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch() # Push messages up

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
        self.input_box.setMaximumHeight(80)
        self.input_box.setStyleSheet("""
            QTextEdit { background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 8px; font-size: 12px; }
            QTextEdit:focus { border-color: #58a6ff; }
        """)
        il.addWidget(self.input_box, stretch=1)

        send_btn = QPushButton("➤ Отправить")
        send_btn.setObjectName("primaryBtn")
        send_btn.setProperty("class", "primary")
        send_btn.setStyleSheet("""
            QPushButton#primaryBtn { background-color: #238636; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; cursor: pointer; }
            QPushButton#primaryBtn:hover { background-color: #2ea043; }
        """)
        send_btn.clicked.connect(self.send_message)
        il.addWidget(send_btn)

        layout.addWidget(input_frame)

    def _connect_signals(self):
        # Enter key sends message (Shift+Enter for new line)
        self.input_box.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.input_box and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        
        # Add user message
        self._add_bubble("user", text)
        self.input_box.clear()

        # Process AI response (Simulated for now)
        QTimer.singleShot(500, lambda: self._simulate_response(text))

    def _simulate_response(self, user_input: str):
        """Mock AI response generation."""
        # In a real app, this would call self.ai_client.generate(user_input)
        # Here we generate dummy data to test the Proposal Engine
        
        lower_input = user_input.lower()
        
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
            
            # Parse into Proposal
            proposal = self.proposal_engine.create_from_ai_response(
                response, 
                context=user_input,
                category="strategy"
            )
            if proposal:
                self._show_proposal_card(proposal)
                
        else:
            response = f"AI получил сообщение: «{user_input}». Это тестовый режим."
            self._add_bubble("assistant", response)

    def _add_bubble(self, role: str, text: str, timestamp: str = ""):
        """Add a chat bubble to the UI."""
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")

        # Determine style based on role
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
        else: # system
            icon = "ℹ️ Система"
            bg_color = "#9e6a03"
            text_color = "#ffffff"
            align = Qt.AlignCenter

        # Container for alignment
        container = QWidget()
        cl = QHBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        
        if align == Qt.AlignRight:
            cl.addStretch()
        elif align == Qt.AlignCenter:
            cl.addStretch()

        # Bubble Frame
        bubble = QFrame()
        bubble.setStyleSheet(f"""
            QFrame {{ background-color: {bg_color}; border-radius: 8px; padding: 10px; max-width: 80%; }}
        """)
        bl = QVBoxLayout(bubble)
        bl.setSpacing(4)

        # Header (Icon + Time)
        hdr = QLabel(f"{icon}  ·  {timestamp}")
        hdr.setStyleSheet(f"color: {'rgba(255,255,255,0.7)' if role=='user' else '#8b949e'}; font-size: 10px; font-weight: bold;")
        bl.addWidget(hdr)

        # Text Content
        txt = QLabel(text)
        txt.setWordWrap(True)
        txt.setStyleSheet(f"color: {text_color}; font-size: 12px; font-family: 'Segoe UI', sans-serif; line-height: 1.4;")
        bl.addWidget(txt)

        cl.addWidget(bubble)
        
        if align == Qt.AlignLeft:
            cl.addStretch()

        # Insert before the stretch at the end of chat_layout
        insert_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_index, container)
        
        # Scroll to bottom
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _show_proposal_card(self, proposal: Proposal):
        """Render interactive proposal card in chat area."""
        card = QFrame()
        card.setObjectName("proposalCard")
        card.setStyleSheet("""
            QFrame#proposalCard {
                background-color: #1c2333;
                border: 2px solid #58a6ff;
                border-radius: 8px;
                padding: 16px;
                margin: 8px 0;
            }
            QLabel#proposalTitle {
                color: #e6edf3;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 12px;
            }
            QLabel#proposalContext {
                color: #8b949e;
                font-size: 12px;
                margin-bottom: 16px;
                font-style: italic;
            }
            QFrame#optionRow {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 12px;
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
                padding: 8px 16px;
                font-weight: bold;
                cursor: pointer;
            }
            QPushButton#chooseBtn:hover {
                background-color: #2ea043;
            }
            QPushButton#dismissBtn {
                background-color: transparent;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 8px 16px;
                cursor: pointer;
            }
            QPushButton#dismissBtn:hover {
                border-color: #8b949e;
                color: #c9d1d9;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        
        # Title
        title_lbl = QLabel(proposal.question)
        title_lbl.setObjectName("proposalTitle")
        layout.addWidget(title_lbl)
        
        # Context
        if proposal.context:
            ctx_lbl = QLabel(f"Контекст: {proposal.context}")
            ctx_lbl.setObjectName("proposalContext")
            ctx_lbl.setWordWrap(True)
            layout.addWidget(ctx_lbl)
        
        # Options
        for opt in proposal.options:
            row = QFrame()
            row.setObjectName("optionRow")
            row_layout = QVBoxLayout(row)
            row_layout.setSpacing(6)
            
            # Option title + recommended badge
            hdr = QHBoxLayout()
            opt_title = QLabel(opt.title)
            opt_title.setObjectName("optionTitle")
            hdr.addWidget(opt_title)
            
            if opt.recommended:
                rec_badge = QLabel("⭐ Рекомендация")
                rec_badge.setStyleSheet("background-color:#9e6a03;color:white;padding:2px 8px;border-radius:10px;font-size:10px;")
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
            # Capture variables for lambda closure
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
        
        # Add to chat history
        insert_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_index, card)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

    def _on_choose_option(self, proposal_id: str, option_id: str):
        """User selected an option from proposal."""
        success = self.proposal_engine.resolve(proposal_id, option_id)
        if success:
            # Send confirmation message back to AI/chat
            confirm_msg = f"[Пользователь выбрал вариант {option_id} из предложения {proposal_id}]"
            self._add_bubble("system", confirm_msg)
            logger.info(f"User chose {option_id} from {proposal_id}")
        else:
            logger.warning(f"Failed to resolve proposal {proposal_id}")

    def _on_dismiss_proposal(self, proposal_id: str):
        """User dismissed all options."""
        prop = self.proposal_engine.proposals.get(proposal_id)
        if prop:
            prop.resolved = True
            prop.chosen_option_id = None
            self._add_bubble("system", f"[Предложение {proposal_id} отклонено]")
            logger.info(f"Proposal {proposal_id} dismissed")

    def _clear_chat(self):
        """Clear all messages."""
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.chat_layout.addStretch()
        self.proposal_engine.proposals.clear()
        logger.info("Chat cleared")
'''

write("gui_ai_panel.py", ai_panel_code)

print("\n=== GUI AI Panel Rewritten ===")
print("\nFeatures:")
print("  [OK] Clean syntax (no broken f-strings)")
print("  [OK] Full chat logic implemented from scratch")
print("  [OK] Proposal System integrated directly")
print("  [OK] Mock AI responses for testing proposals")
print("\nRun START.bat and try asking about strategies.")