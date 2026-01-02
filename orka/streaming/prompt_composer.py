"""
PromptComposer builds a stable, budgeted prompt for the streaming executor.

It enforces per-section budgets and a total token cap while always including
invariants. Tokenizer is pluggable; default is a whitespace-token counter for
deterministic offline tests.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .state import StreamingState
from .types import PromptBudgets


class TokenizerProtocol:
    def count(self, text: str) -> int:  # pragma: no cover - protocol
        raise NotImplementedError


class WhitespaceTokenizer(TokenizerProtocol):
    def count(self, text: str) -> int:
        if not text:
            return 0
        return len([t for t in text.split() if t])


@dataclass
class PromptComposer:
    budgets: PromptBudgets
    tokenizer: TokenizerProtocol | None = None

    def __post_init__(self) -> None:
        if self.tokenizer is None:
            self.tokenizer = WhitespaceTokenizer()

    def compose(self, state: StreamingState) -> Dict[str, Any]:
        """Compose prompt sections from state within budgets.

        Returns a dictionary containing:
        - sections: mapping of section->text (invariants always present)
        - section_tokens: mapping of section->token_count
        - total_tokens: int
        - fingerprint: stable hash string
        - prompt_version: monotonically increasing int (state.version)
        - state_version_used: same as state.version for traceability
        """
        assert self.tokenizer is not None

        # Build base sections from mutable state in lexical order
        mutable_dict = state.mutable.__dict__.copy()
        sections: Dict[str, str] = {k: str(mutable_dict[k]) for k in sorted(mutable_dict.keys())}

        # Enforce per-section caps first
        section_tokens: Dict[str, int] = {}
        for name, content in sections.items():
            cap = self.budgets.sections.get(name)
            if cap is None:
                # Default: no explicit cap prior to total budget enforcement
                tokens = self.tokenizer.count(content)
                section_tokens[name] = tokens
                continue
            trimmed, used = self._trim_to_tokens(content, cap)
            sections[name] = trimmed
            section_tokens[name] = used

        # Invariants always present and excluded from trimming
        inv = state.clone_invariants()
        inv_text = self._invariants_text(inv)
        inv_tokens = self.tokenizer.count(inv_text)

        # Now enforce total budget
        total_tokens = inv_tokens + sum(section_tokens.values())
        if total_tokens > self.budgets.total_tokens:
            # Trim lower-priority sections using fair-share approach
            over = total_tokens - self.budgets.total_tokens
            sections, section_tokens = self._fair_trim(sections, section_tokens, over)
            total_tokens = inv_tokens + sum(section_tokens.values())

        fingerprint = self._fingerprint(inv_text, sections, section_tokens, self.budgets)

        return {
            "sections": {"invariants": inv_text, **sections},
            "section_tokens": {"invariants": inv_tokens, **section_tokens},
            "total_tokens": total_tokens,
            "fingerprint": fingerprint,
            "prompt_version": state.version,
            "state_version_used": state.version,
        }

    # Helpers
    def _invariants_text(self, inv: Dict[str, Any]) -> str:
        # Stable ordering
        order = ["identity", "voice", "refusal", "tool_permissions", "safety_policies"]
        parts = []
        for key in order:
            val = inv.get(key, "")
            parts.append(f"{key}: {val}")
        return "\n".join(parts)

    def _trim_to_tokens(self, text: str, cap: int) -> Tuple[str, int]:
        assert self.tokenizer is not None
        tokens = text.split()
        if len(tokens) <= cap:
            return text, len(tokens)
        trimmed_tokens = tokens[:cap]
        return " ".join(trimmed_tokens), cap

    def _fair_trim(
        self,
        sections: Dict[str, str],
        section_tokens: Dict[str, int],
        over: int,
    ) -> Tuple[Dict[str, str], Dict[str, int]]:
        """Fairly trim sections to reduce total tokens by 'over'.

        Strategy: repeatedly subtract one token from the largest sections (by
        current tokens) in lexical name order to ensure determinism.
        """
        assert self.tokenizer is not None
        items = sorted(section_tokens.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        while over > 0 and items:
            name, tok = items[0]
            if tok == 0:
                break
            # Remove one token
            content_tokens = sections[name].split()
            if content_tokens:
                content_tokens = content_tokens[:-1]
                sections[name] = " ".join(content_tokens)
                section_tokens[name] -= 1
                over -= 1
            # Resort
            items = sorted(section_tokens.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        return sections, section_tokens

    def _fingerprint(
        self,
        inv_text: str,
        sections: Dict[str, str],
        section_tokens: Dict[str, int],
        budgets: PromptBudgets,
    ) -> str:
        h = hashlib.sha256()
        h.update(inv_text.encode("utf-8"))
        for name in sorted(sections.keys()):
            h.update(name.encode("utf-8"))
            h.update(sections[name].encode("utf-8"))
            h.update(str(section_tokens.get(name, 0)).encode("utf-8"))
        h.update(str(budgets.total_tokens).encode("utf-8"))
        for name in sorted(budgets.sections.keys()):
            h.update(name.encode("utf-8"))
            h.update(str(budgets.sections[name]).encode("utf-8"))
        return h.hexdigest()
