"""
ContractIQ — LangGraph Edge Functions

Conditional routing logic for the workflow graph.
"""

import logging
from graph.state import ContractState

logger = logging.getLogger(__name__)


def should_continue_after_parse(state: ContractState) -> str:
    """
    After parsing, check if we have valid text to proceed.
    Routes to 'classify' or 'end' if parsing failed completely.
    """
    cleaned_text = state.get("cleaned_text", "")

    if not cleaned_text or len(cleaned_text) < 50:
        logger.warning("Parsing produced insufficient text, ending workflow")
        return "end"

    return "classify"


def should_continue_after_risk(state: ContractState) -> str:
    """
    After risk analysis, determine whether human review is needed.
    Routes to 'human_review' (which just flags it) then continues to summary.
    """
    # Always continue to summary — human review decision is just a flag
    return "summary"


def route_after_human_review(state: ContractState) -> str:
    """
    After human review decision, always continue to end.
    The actual pausing happens in the API layer, not in the graph.
    """
    return "end"
