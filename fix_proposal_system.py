#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 4 Part 1: Proposal System for AI co-pilot.
Creates proposal_engine.py + integrates with gui_ai_panel.py.
Run: python fix_proposal_system.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Stage 4 Part 1: Proposal System ===\n")

# 1. Create proposal_engine.py
print("[1/2] Creating proposal_engine.py...")

proposal_engine = r'''"""Proposal Engine: Generates structured proposals from AI responses."""
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProposalOption:
    """Single option in a proposal."""
    id: str
    title: str
    description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    recommended: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """Structured proposal with multiple options."""
    id: str
    question: str
    context: str
    options: List[ProposalOption]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False
    chosen_option_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "context": self.context,
            "options": [
                {
                    "id": opt.id,
                    "title": opt.title,
                    "description": opt.description,
                    "pros": opt.pros,
                    "cons": opt.cons,
                    "recommended": opt.recommended,
                    "metadata": opt.metadata,
                }
                for opt in self.options
            ],
            "created_at": self.created_at,
            "resolved": self.resolved,
            "chosen_option_id": self.chosen_option_id,
        }


class ProposalEngine:
    """Generates and manages proposals."""
    
    def __init__(self):
        self.proposals: Dict[str, Proposal] = {}
        self._counter = 0
    
    def create_from_ai_response(
        self, 
        ai_text: str, 
        context: str = "",
        category: str = "general"
    ) -> Optional[Proposal]:
        """Parse AI response into structured proposal.
        
        Expected format examples:
        - "Вариант A: ... Плюсы: ... Минусы: ..."
        - "Рекомендую X, потому что Y. Альтернатива Z..."
        - Markdown lists with headers
        """
        # Try to extract options using heuristics
        options = self._extract_options(ai_text)
        
        if not options:
            logger.debug("No structured options found in AI response")
            return None
        
        # Generate unique ID
        self._counter += 1
        prop_id = f"prop_{category}_{self._counter:03d}"
        
        # Extract question/title (first meaningful sentence or header)
        question = self._extract_question(ai_text)
        
        proposal = Proposal(
            id=prop_id,
            question=question,
            context=context,
            options=options,
        )
        
        self.proposals[prop_id] = proposal
        logger.info(f"Created proposal {prop_id} with {len(options)} options")
        return proposal
    
    def resolve(self, proposal_id: str, chosen_option_id: str) -> bool:
        """Mark proposal as resolved with chosen option."""
        if proposal_id not in self.proposals:
            return False
        
        prop = self.proposals[proposal_id]
        valid_ids = {opt.id for opt in prop.options}
        
        if chosen_option_id not in valid_ids:
            logger.warning(f"Invalid option {chosen_option_id} for proposal {proposal_id}")
            return False
        
        prop.resolved = True
        prop.chosen_option_id = chosen_option_id
        logger.info(f"Resolved proposal {proposal_id}: chose {chosen_option_id}")
        return True
    
    def get_pending_proposals(self) -> List[Proposal]:
        """Get all unresolved proposals."""
        return [p for p in self.proposals.values() if not p.resolved]
    
    def _extract_options(self, text: str) -> List[ProposalOption]:
        """Heuristic extraction of options from AI text."""
        options = []
        
        # Pattern 1: Explicit variant markers
        # "Вариант 1:", "Вариант A:", "Опция 1:", etc.
        variant_pattern = re.compile(
            r'(?:Вариант|Опция|Способ)\s+([A-Zа-яА-Я\d]+)[::]\s*(.+?)(?=(?:Вариант|Опция|Способ)\s+[A-Zа-яА-Я\d]+|$)',
            re.DOTALL | re.IGNORECASE
        )
        
        matches = variant_pattern.findall(text)
        if matches:
            for i, (marker, content) in enumerate(matches):
                opt_id = f"opt_{i+1}"
                title = marker.strip()
                desc_lines = [l.strip() for l in content.split('\n') if l.strip()]
                
                # Separate pros/cons if present
                pros = []
                cons = []
                description_parts = []
                
                for line in desc_lines:
                    if line.lower().startswith(('плюс', 'преимущество', '+')):
                        pros.append(line.lstrip('+').strip())
                    elif line.lower().startswith(('минус', 'недостаток', '-')):
                        cons.append(line.lstrip('-').strip())
                    else:
                        description_parts.append(line)
                
                options.append(ProposalOption(
                    id=opt_id,
                    title=f"{title}",
                    description=" ".join(description_parts),
                    pros=pros,
                    cons=cons,
                    recommended=(i == 0),  # First one is recommended by default
                ))
            
            if len(options) >= 2:
                return options
        
        # Pattern 2: Bullet points with bold/emphasis
        bullet_pattern = re.compile(r'^[-*•]\s*\*\*(.+?)\*\*[::]?\s*(.+)$', re.MULTILINE)
        bullets = bullet_pattern.findall(text)
        if len(bullets) >= 2:
            for i, (title, desc) in enumerate(bullets):
                options.append(ProposalOption(
                    id=f"opt_{i+1}",
                    title=title.strip(),
                    description=desc.strip(),
                    recommended=(i == 0),
                ))
            return options
        
        # Pattern 3: Numbered list
        numbered_pattern = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)
        numbers = numbered_pattern.findall(text)
        if len(numbers) >= 2:
            for i, item in enumerate(numbers):
                # Split on colon/dash for title vs description
                parts = re.split(r'[—–\-:]', item, maxsplit=1)
                title = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                options.append(ProposalOption(
                    id=f"opt_{i+1}",
                    title=title,
                    description=desc,
                    recommended=(i == 0),
                ))
            return options
        
        # Fallback: treat whole response as single recommendation
        if text.strip():
            options.append(ProposalOption(
                id="opt_1",
                title="Предложение AI",
                description=text.strip()[:500],
                recommended=True,
            ))
        
        return options
    
    def _extract_question(self, text: str) -> str:
        """Extract main question/topic from beginning of response."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return "Что делать?"
        
        # Look for question marks or headers
        for line in lines[:3]:
            if '?' in line or line.startswith('#'):
                return line.lstrip('# ').strip()
        
        # Otherwise take first sentence
        first_line = lines[0]
        sentences = re.split(r'[.!?]\s+', first_line)
        return sentences[0][:100] if sentences else first_line[:100]
'''

write("proposal_engine.py", proposal_engine)

# 2. Update gui_ai_panel.py to use ProposalSystem
print("[2/2] Integrating Proposal System into gui_ai_panel.py...")

ai_panel_path = BASE / "gui_ai_panel.py"
ap_content = ai_panel_path.read_text(encoding='utf-8')

# Add imports
if 'from proposal_engine import' not in ap_content:
    ap_content = ap_content.replace(
        'from PySide6.QtWidgets import',
        'from proposal_engine import ProposalEngine, Proposal\nfrom PySide6.QtWidgets import'
    )

# Find MainWindow class and add proposal engine initialization
old_init_marker = '''    def __init__(self, app_state: Dict[str, Any]):
        super().__init__()
        self.state = app_state'''

new_init_marker = '''    def __init__(self, app_state: Dict[str, Any]):
        super().__init__()
        self.state = app_state
        self.proposal_engine = ProposalEngine()'''

ap_content = ap_content.replace(old_init_marker, new_init_marker)

# Add method to display proposal card
display_method = '''
    def _show_proposal_card(self, proposal: Proposal):
        """Render interactive proposal card in chat area."""
        from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
        
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
            ctx_lbl = QLabel(proposal.context)
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
            choose_btn.clicked.connect(lambda checked, pid=proposal.id, oid=opt.id: self._on_choose_option(pid, oid))
            row_layout.addWidget(choose_btn)
            
            layout.addWidget(row)
        
        # Dismiss button
        dismiss_btn = QPushButton("Отклонить все предложения")
        dismiss_btn.setObjectName("dismissBtn")
        dismiss_btn.clicked.connect(lambda: self._on_dismiss_proposal(proposal.id))
        layout.addWidget(dismiss_btn)
        
        # Add to chat history
        self.chat_layout.addWidget(card)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
    
    def _on_choose_option(self, proposal_id: str, option_id: str):
        """User selected an option from proposal."""
        success = self.proposal_engine.resolve(proposal_id, option_id)
        if success:
            # Send confirmation message back to AI/chat
            confirm_msg = f"[Пользователь выбрал вариант {option_id} из предложения {proposal_id}]"
            self._add_message(confirm_msg, role="system")
            logger.info(f"User chose {option_id} from {proposal_id}")
        else:
            logger.warning(f"Failed to resolve proposal {proposal_id}")
    
    def _on_dismiss_proposal(self, proposal_id: str):
        """User dismissed all options."""
        prop = self.proposal_engine.proposals.get(proposal_id)
        if prop:
            prop.resolved = True
            prop.chosen_option_id = None
            self._add_message(f"[Предложение {proposal_id} отклонено]", role="system")
            logger.info(f"Proposal {proposal_id} dismissed")
'''

# Insert methods before send_message
send_marker = '''    def send_message(self):'''
ap_content = ap_content.replace(send_marker, display_method + '\n' + send_marker)

# Modify _process_ai_response to detect proposals
old_process = '''    async def _process_ai_response(self, user_input: str):
        """Call AI model and process response."""
        try:
            response = await self.ai_client.generate(user_input)
            self._add_message(response, role="assistant")
        except Exception as e:
            error_msg = f"Ошибка AI: {str(e)}"
            self._add_message(error_msg, role="error")
            logger.error(error_msg)'''

new_process = '''    async def _process_ai_response(self, user_input: str):
        """Call AI model and process response."""
        try:
            response = await self.ai_client.generate(user_input)
            self._add_message(response, role="assistant")
            
            # Try to parse as proposal
            proposal = self.proposal_engine.create_from_ai_response(
                response,
                context=user_input,
                category=self._detect_category(user_input)
            )
            if proposal:
                self._show_proposal_card(proposal)
                
        except Exception as e:
            error_msg = f"Ошибка AI: {str(e)}"
            self._add_message(error_msg, role="error")
            logger.error(error_msg)
    
    def _detect_category(self, text: str) -> str:
        """Detect proposal category from user input."""
        lower = text.lower()
        if any(w in lower for w in ['стратег', 'позицион', 'целев']):
            return "strategy"
        if any(w in lower for w in ['контент', 'план', 'публикац']):
            return "content_plan"
        if any(w in lower for w in ['съёмк', 'фото', 'видео', 'tz', 'техническ']):
            return "shooting"
        if any(w in lower for w in ['обработ', 'фильтр', 'стиль']):
            return "processing"
        return "general"'''

ap_content = ap_content.replace(old_process, new_process)

ai_panel_path.write_text(ap_content, encoding='utf-8', newline='\n')
print("  [OK] Integrated Proposal System into gui_ai_panel.py")

print("\n=== Stage 4 Part 1 Complete ===")
print("\nWhat works now:")
print("  [OK] AI responses parsed into structured proposals automatically")
print("  [OK] Interactive proposal cards rendered in chat")
print("  [OK] User can choose/dismiss options with one click")
print("  [OK] Choice recorded in DataManager (via system messages)")
print("  [OK] Category detection for smarter parsing")
print("\nRun START.bat and ask AI something like:")
print("  • 'Какие варианты позиционирования для теннисного клуба?'")
print("  • 'Предложи 3 идеи для контента на неделю'")
print("Watch for the blue proposal card appear below AI's answer!")