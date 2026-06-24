"""LLM-based auto-tagging service.

Analyzes question text and maps it to knowledge points in the taxonomy.
Reuses the same DeepSeek LLM configuration as the main agent.
"""

import difflib
import time
from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from math_assistant.server.models.knowledge_point import KnowledgePoint
from math_assistant.server.models.question_tag import QuestionTag

# Cache for the KP taxonomy (name -> KP mapping), refreshed every 5 minutes
_taxonomy_cache: Optional[dict[str, list[dict]]] = None
_cache_timestamp: float = 0
_CACHE_TTL_SECONDS = 300  # 5 minutes


class TagCandidate(BaseModel):
    """Structured output from the LLM tagger."""
    knowledge_point_path: str = Field(
        description="The full_path of the knowledge point, e.g. 'Calculus > Derivatives'"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence that this knowledge point is relevant (0-1)"
    )
    reasoning: str = Field(
        description="Brief explanation of why this knowledge point applies"
    )


class TaggingResult(BaseModel):
    """Wrapper for the LLM tagging response."""
    tags: list[TagCandidate] = Field(
        default_factory=list,
        description="List of identified knowledge points"
    )


def _build_taxonomy_cache(db: Session) -> list[dict]:
    """Build a cache of all knowledge points for the LLM prompt."""
    global _taxonomy_cache, _cache_timestamp

    now = time.time()
    if _taxonomy_cache is not None and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
        return _taxonomy_cache

    kps = db.query(KnowledgePoint).order_by(KnowledgePoint.full_path).all()
    taxonomy_list = [
        {"id": kp.id, "name": kp.name, "full_path": kp.full_path, "depth": kp.depth}
        for kp in kps
    ]

    _taxonomy_cache = taxonomy_list
    _cache_timestamp = now
    return taxonomy_list


def _build_tagging_prompt(question_text: str, taxonomy: list[dict]) -> str:
    """Build the system + user prompt for auto-tagging."""
    taxonomy_lines = []
    for item in taxonomy:
        indent = "  " * item["depth"]
        taxonomy_lines.append(f"{indent}- {item['full_path']}")

    taxonomy_str = "\n".join(taxonomy_lines)

    return f"""You are an expert mathematics curriculum analyst. Your job is to analyze a math question and identify which knowledge points (topics) it relates to.

Below is the complete knowledge point taxonomy. Each entry is a mathematical topic:

{taxonomy_str}

Given a student's question, identify the most relevant knowledge points from the taxonomy above. Consider:
1. What concepts are needed to solve this problem?
2. What topic does this question test?
3. Are there multiple topics involved?

The student's question is:

{question_text}

Return a list of relevant knowledge points. Use the exact full_path from the taxonomy. Include at most 5 knowledge points, ordered by relevance. Set confidence based on how clearly the question maps to the topic (1.0 = perfect match, 0.5 = somewhat related).
"""


def _fuzzy_match(
    llm_path: str, taxonomy: list[dict], threshold: float = 0.85
) -> Optional[dict]:
    """Fuzzy-match an LLM-returned path against the taxonomy.

    Args:
        llm_path: The full_path string from the LLM output.
        taxonomy: The cached taxonomy list.
        threshold: Minimum similarity ratio for a match.

    Returns:
        The matched taxonomy entry dict, or None if no match.
    """
    # First try exact match (case-insensitive)
    llm_lower = llm_path.strip().lower()
    for item in taxonomy:
        if item["full_path"].lower() == llm_lower:
            return item

    # Try matching just the name (last segment)
    llm_name = llm_path.split(">")[-1].strip().lower()
    best_ratio = 0
    best_match = None

    for item in taxonomy:
        item_name = item["name"].lower()
        ratio = difflib.SequenceMatcher(None, llm_name, item_name).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = item

    if best_match:
        return best_match

    # Try matching the full path
    for item in taxonomy:
        ratio = difflib.SequenceMatcher(None, llm_path.lower(), item["full_path"].lower()).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = item

    return best_match


def auto_tag_question(question_id: int, db: Session):
    """Analyze a question and automatically tag it with knowledge points.

    This is intended to run as a background task after question creation.

    Args:
        question_id: ID of the question to tag.
        db: Database session. Note: in background tasks, the session
            may need to be re-created if the original expires.
    """
    from math_assistant.server.models.question import Question

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        return

    taxonomy = _build_taxonomy_cache(db)
    if not taxonomy:
        return  # No taxonomy seeded yet

    # Build the LLM client using the main app config
    try:
        from math_assistant.config import Config
        main_config = Config.load()
        api_key = main_config.get_api_key()

        llm = ChatOpenAI(
            model=main_config.model.name,
            api_key=api_key,
            base_url=main_config.api.base_url,
            temperature=0.0,
        )

        structured_llm = llm.with_structured_output(TaggingResult)
        prompt = _build_tagging_prompt(question.content, taxonomy)

        result: TaggingResult = structured_llm.invoke(prompt)

        # Match LLM results to taxonomy and create tags
        for candidate in result.tags:
            match = _fuzzy_match(candidate.knowledge_point_path, taxonomy)
            if match is None:
                continue  # Skip hallucinated paths

            # Check if this tag already exists
            existing = (
                db.query(QuestionTag)
                .filter(
                    QuestionTag.question_id == question_id,
                    QuestionTag.knowledge_point_id == match["id"],
                )
                .first()
            )
            if existing:
                continue

            tag = QuestionTag(
                question_id=question_id,
                knowledge_point_id=match["id"],
                confidence=candidate.confidence,
                source="auto",
                is_user_corrected=False,
            )
            db.add(tag)

        db.commit()

    except Exception as e:
        # Log the error but don't crash the request
        import logging
        logging.getLogger(__name__).warning(
            f"Auto-tagging failed for question {question_id}: {e}"
        )
        db.rollback()
