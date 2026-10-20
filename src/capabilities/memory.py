import json
from pathlib import Path
from pydantic import ValidationError
from src.schemas.study import ConceptProgress

FILE = Path("data/progress_path.json")

def load_progress() -> dict[str, ConceptProgress]:
    if not FILE.exists():
        return {}

    try:
        with open(FILE, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}

    if not isinstance(raw, dict):
        return {}

    result = {}
    for concept_id, entry_dict in raw.items():
        try:
            result[concept_id] = ConceptProgress.model_validate(entry_dict)
        except ValidationError:
            continue
    return result

def save_progress(progress: dict[str, ConceptProgress]) -> None:
   plain = {}
   for concept_id, entry in progress.items():
      plain[concept_id] = entry.model_dump()
      
   FILE.parent.mkdir(parents=True, exist_ok=True)
   with open(FILE, "w", encoding="utf-8") as f:
      json.dump(plain, f, indent=2)
"""
Optional project capability: Memory & Persistent Conversation State.

Implement this module only if this capability is relevant to your application's
user problem. Remove the file if the capability is not used.

Conceptual Overview:
-------------------
Memory enables an application to retain conversational context across multiple user interactions
or persist state between user sessions.

Key concepts when implementing memory:
1. Short-term Memory (Chat History): Maintaining an ordered list of user and assistant
   messages within the current session and appending them to model requests.
2. Context Window Management: Truncating, summarizing, or pruning history when it exceeds
   the model's maximum context length.
3. Long-term / Persistent Memory: Storing user preferences, session history, or key facts
   in local files or persistent state stores.

Note:
-----
Keep memory implementations simple and relevant to the user's workflow needs.
"""

# Implement custom conversation memory or state management below if selected.
