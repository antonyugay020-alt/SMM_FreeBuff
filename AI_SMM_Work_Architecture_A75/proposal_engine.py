"""Proposal Engine: Generates structured proposals from AI responses."""
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
