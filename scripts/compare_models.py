import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

# Allow running: python scripts/compare_models.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.capabilities.rag import retrieve
from src.models.model_client import OllamaModelClient


MODELS = [
    "llama3.2",
    "qwen3.5:4b",
    "qwen3.5:9b",
]

TESTS = [
    {
        "id": "fractions",
        "concept_id": "fractions",
        "question": (
            "Explain how to add fractions with different denominators. "
            "Calculate 5/24 + 1/40 and explain each step."
        ),
        "expected": (
            "Find a common denominator of 120: "
            "25/120 + 3/120 = 28/120 = 7/30."
        ),
    },
    {
        "id": "composition",
        "concept_id": "function_composition",
        "question": (
            "Explain function composition. "
            "Given f(x) = x^2 and g(x) = x + 2, "
            "find and expand f(g(x)). "
            "Also find g(f(x)) and explain why order matters."
        ),
        "expected": (
            "f(g(x)) = (x + 2)^2 = x^2 + 4x + 4. "
            "g(f(x)) = x^2 + 2. "
            "Function composition is not commutative in general."
        ),
    },
    {
        "id": "limits",
        "concept_id": "limits",
        "question": (
            "Find the limit of (x^2 - 4)/(x - 2) as x approaches 2. "
            "Explain why direct substitution is insufficient "
            "and show the algebraic steps."
        ),
        "expected": (
            "Direct substitution gives 0/0, an indeterminate form. "
            "For x != 2, factor and cancel x - 2 to get x + 2. "
            "The limit is 4, although the original expression "
            "is undefined at x = 2."
        ),
    },
    {
        "id": "derivative_rules",
        "concept_id": "derivative_rules",
        "question": (
            "Differentiate f(x) = 3x^2 + 2x - 5. "
            "Explain the rules used for each term, "
            "including why the constant term disappears."
        ),
        "expected": (
            "f'(x) = 6x + 2. "
            "Use the sum, constant multiple, and power rules. "
            "The derivative of the constant -5 is 0."
        ),
    },
    {
        "id": "chain_rule",
        "concept_id": "chain_rule",
        "question": (
            "Explain the chain rule and use it to differentiate "
            "h(x) = (3x^2 + 1)^4. "
            "Identify the inner and outer functions and "
            "explain the role of the inner derivative."
        ),
        "expected": (
            "Inner function u(x) = 3x^2 + 1, derivative 6x. "
            "Outer function F(u) = u^4, derivative 4u^3. "
            "h'(x) = 24x(3x^2 + 1)^3."
        ),
    },
]


def save_results(path, report):
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_prompt(question, sources):
    source_text = "\n\n".join(
        f"[Source {i}]\n"
        f"{source['book']} — {source['section']}\n"
        f"{source['text']}"
        for i, source in enumerate(sources, start=1)
    )

    return (
        "You are a mathematics tutor helping a college student.\n"
        "Use the supplied sources for mathematical rules and "
        "apply those rules to the requested problem.\n"
        "Explain your calculation steps in clear English.\n"
        "Use Markdown and LaTeX for mathematics.\n"
        "Keep the answer under about 250 words.\n"
        "If essential information is missing from the sources, "
        "state that limitation rather than inventing a rule.\n"
        "Cite the source numbers supporting your explanation.\n\n"
        f"Sources:\n{source_text}\n\n"
        f"Question:\n{question}"
    )


def main():
    run_id = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    output_dir = (
        PROJECT_ROOT / "evaluation" / "model_comparison" / run_id
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    results_path = output_dir / "results.json"

    report = {
        "started_at_utc": run_id,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "models": MODELS,
        "method": {
            "runs_per_model_per_question": 1,
            "retrieval": "Retrieved once per question and reused for all models.",
            "source_limit": "First 4000 characters of each of three chunks.",
            "timing": (
                "Wall-clock seconds around client.generate(), "
                "excluding retrieval and a separate warm-up request."
            ),
            "settings": (
                "Uses the existing OllamaModelClient: "
                "think=False, num_ctx=8192. "
                "Other generation settings use model defaults."
            ),
            "limitations": (
                "Single-run exploratory comparison. "
                "Model defaults may differ and results can vary. "
                "Timing may still include model reloads."
            ),
        },
        "tests": [],
        "warmups": [],
        "results": [],
    }

    print("Preparing the same source texts for every model...", flush=True)

    for test in TESTS:
        chunks = retrieve(
            test["concept_id"],
            query=test["question"],
            top_k=3,
        )

        if not chunks:
            raise RuntimeError(
                f"No source chunks found for {test['concept_id']}."
            )

        sources = [
            {
                "id": chunk.id,
                "book": chunk.book,
                "section": chunk.section,
                "source_url": chunk.source_url,
                "text": chunk.text[:4000],
                "truncated": len(chunk.text) > 4000,
            }
            for chunk in chunks
        ]

        report["tests"].append({
            **test,
            "sources": sources,
            "prompt": build_prompt(test["question"], sources),
        })

    save_results(results_path, report)

    for model_name in MODELS:
        print(f"\nModel: {model_name}", flush=True)
        client = OllamaModelClient(model_name=model_name)

        # Exclude an initial model-loading request from test timing.
        try:
            client.generate("Reply with only the word OK.")
            report["warmups"].append({
                "model": model_name,
                "status": "completed",
            })
        except Exception as error:
            report["warmups"].append({
                "model": model_name,
                "status": "error",
                "error": str(error),
            })
            print(f"Warm-up failed: {error}", flush=True)

        save_results(results_path, report)

        for number, test in enumerate(report["tests"], start=1):
            print(
                f"  [{number}/{len(TESTS)}] {test['id']}...",
                flush=True,
            )

            started = perf_counter()
            answer = ""
            error_text = None

            try:
                answer = client.generate(test["prompt"]).strip()
                execution_status = "completed" if answer else "empty"
            except Exception as error:
                execution_status = "error"
                error_text = str(error)

            seconds = round(perf_counter() - started, 3)

            result = {
                "model": model_name,
                "test_id": test["id"],
                "response_seconds": seconds,
                "execution_status": execution_status,
                "answer": answer,
                "error": error_text,
                "correctness_score": None,
                "clarity_score": None,
                "review_notes": "",
            }

            report["results"].append(result)
            save_results(results_path, report)

            safe_model_name = model_name.replace(":", "_")
            answer_path = (
                output_dir / f"{safe_model_name}_{test['id']}.md"
            )
            answer_path.write_text(
                f"# {model_name} — {test['id']}\n\n"
                f"Time: {seconds} seconds\n\n"
                f"Execution status: {execution_status}\n\n"
                f"## Question\n\n{test['question']}\n\n"
                f"## Answer\n\n{answer or error_text or '(empty response)'}\n\n"
                f"## Review reference\n\n{test['expected']}\n",
                encoding="utf-8",
            )

            print(
                f"    {execution_status}: {seconds} seconds",
                flush=True,
            )

    print(f"\nFinished. Results saved to:\n{output_dir}")
    print("Correctness and clarity still require manual review.")


if __name__ == "__main__":
    main()