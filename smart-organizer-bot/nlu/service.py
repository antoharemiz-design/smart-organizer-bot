import logging
from datetime import datetime

from nlu.classifier import classify
from nlu.llm_client import LLMClient
from common.schemas import IntentResult, TaskDraft

logger = logging.getLogger(__name__)
llm_client = LLMClient()

async def parse_message(text: str, current_dt: datetime | None = None) -> IntentResult:
    if current_dt is None:
        current_dt = datetime.now()

    intent = classify(text)
    logger.debug(f"Classified intent: {intent}")

    result = IntentResult(intent=intent)

    if intent == "task":
        task_draft = await llm_client.extract_task(text, current_dt)
        if task_draft:
            result.task_draft = task_draft
            logger.debug(f"Extracted task draft: {task_draft.model_dump_json()}")
        else:
            logger.warning("Failed to extract task draft")

    return result