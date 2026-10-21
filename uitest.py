import gradio as gr

from src.services.ai_service import (
    list_goals,
    get_progress,
    start_assessment,
    submit_answer,
    get_study_material,
    get_assessment_concepts,
    get_questions,
    generate_response,
)

def _question_text(question) -> str:
    if question is None:
        return "**Assessment done.** Click *Get study material* below."

    return f"**Question:** {question.question}"

def _material_markdown(result) -> str:
    if result.error: return f"**Error:** {result.error}"

    if not result.items: return "No gaps found, nothing to study."

    parts = []
    for item in result.items:
        badge = "verified" if item.lesson.verified else "UNVERIFIED"

        parts.append(
            f"## {item.concept.name} ({badge})\n\n"
            f"{item.lesson.content}"
        )

        if item.verifier_issues:
            parts.append(
                "**Verifier notes:**\n"
                + "\n".join(
                    f"- {issue}"
                    for issue in item.verifier_issues
                )
            )

        if item.quiz:
            parts.append(
                "**Practice:**\n"
                + "\n".join(
                    f"- {question.question}"
                    for question in item.quiz
                )
            )
    return "\n\n".join(parts)

import difflib
import json
import re

from src.config import config


QUESTIONS_PER_TOPIC = 5  # generate_quiz returns at most 5 questions

# Gradio only renders $$...$$ by default. Questions and lessons also use inline $...$.
LATEX_DELIMITERS = [
    {"left": "$$", "right": "$$", "display": True},
    {"left": "$", "right": "$", "display": False},
]


def _make_loader(concept_id):
    """Button handler: generate the questions for one topic and reveal the answer boxes.

    Returns values for: [questions_state, status_md, load_btn, group_1, question_md_1, group_2, ...]
    """
    def load():
        try:
            questions = get_questions(concept_id)
        except Exception as error:
            hidden = [gr.update(visible=False), ""] * QUESTIONS_PER_TOPIC
            return [[], f"**Could not generate questions:** {error}", gr.update(visible=True), *hidden]

        if not questions:
            hidden = [gr.update(visible=False), ""] * QUESTIONS_PER_TOPIC
            return [[], "No questions available for this topic.", gr.update(visible=True), *hidden]

        slots = []
        for i in range(QUESTIONS_PER_TOPIC):
            if i < len(questions):
                slots += [gr.update(visible=True), f"**Q{i + 1}:** {questions[i].question}"]
            else:
                slots += [gr.update(visible=False), ""]

        return [questions, "Answer the questions below.", gr.update(visible=False), *slots]
    return load


def _make_checker(index):
    """Answer handler for question number `index` of a topic.

    Returns values for: [progress_state, result_md, check_btn, answer_box]
    """
    def check(goal_id, progress, questions, answer):
        if index >= len(questions):
            return progress, "", gr.update(), gr.update()

        step = submit_answer(goal_id, progress, questions[index], answer)

        # Empty answer: submit_answer hands the question back, so let the user try again.
        if step.question is not None:
            return step.progress, step.message, gr.update(), gr.update()

        # Answered: lock the box so one question cannot be scored twice.
        return step.progress, step.message, gr.update(interactive=False), gr.update(interactive=False)
    return check


def _rank_goals(text, goals):
    """Score every concept against the user's text. Returns [(score, concept)] best first."""
    try:
        with open(config.concept_map_path, encoding="utf-8") as f:
            extra = {item["id"]: item for item in json.load(f)}
    except (OSError, ValueError, KeyError):
        extra = {}

    text_l = text.lower()
    words = [w for w in re.findall(r"[\wåäö]+", text_l) if len(w) >= 3]
    ranked = []

    for concept in goals:
        raw = extra.get(concept.id, {})
        names = {
            concept.name.lower(),
            concept.id.lower().replace("_", " "),
            str(raw.get("name_en", "")).lower(),
            str(raw.get("name_fi", "")).lower(),
        }
        names.discard("")

        score = 0
        for name in names:
            if name in text_l:
                score = max(score, 100 + len(name))

        name_words = {w for n in names for w in re.findall(r"[\wåäö]+", n) if len(w) >= 3}
        desc_words = set(re.findall(r"[\wåäö]+", concept.description.lower()))

        for word in words:
            if word in name_words:
                score += 10
            elif difflib.get_close_matches(word, name_words, n=1, cutoff=0.8):
                score += 8
            elif len(word) >= 5 and any(n.startswith(word[:5]) for n in name_words):
                score += 6
            elif word in desc_words:
                score += 2

        if score > 0:
            ranked.append((score, concept))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked

def ask_agent(user_message):
    if not user_message or not user_message.strip():
        return "Please enter a learning goal.", None

    goals = list_goals()

    if not goals: return "No learning goals are available.", None

    normalized_input = user_message.strip().lower()

    matched_goal = next((
            concept for concept in goals
            if concept.name.lower() == normalized_input
            or concept.id.lower() == normalized_input
        ), None,
    )

    candidates = []
    if matched_goal is None:
        candidates = _rank_goals(user_message, goals)

        # 1) Clear name match, no model needed
        if candidates and candidates[0][0] >= 100:
            matched_goal = candidates[0][1]

    if matched_goal is None and candidates:
        # 2) Ask the model, but only to choose from a short list
        shortlist = [concept for _, concept in candidates[:8]]
        goal_options = "\n".join(
            f"{concept.id}: {concept.name}" for concept in shortlist
        )

        prompt = f"""
            Pick which topic the student wants to learn.

            Topics:
            {goal_options}

            Student said: {user_message}

            Return ONLY the topic ID from the list, nothing else.
            """

        response = ""
        try:
            response = generate_response(prompt).strip()
        except Exception:
            response = ""

        if not response.startswith("[Error]"):
            selected_id = response.strip().strip('`"\' .').lower()
            matched_goal = next((c for c in shortlist if c.id.lower() == selected_id), None)
            if matched_goal is None:
                matched_goal = next((c for c in shortlist if c.id.lower() in response.lower()), None)

        # 3) Model failed or answered nonsense: trust the best keyword match
        if matched_goal is None:
            matched_goal = shortlist[0]

    if matched_goal is None:
        examples = ", ".join(c.name for c in goals[:6])
        return (
            "I couldn't match that learning goal to the available topics. "
            f"Try a topic name, for example: {examples}.",
            None,
        )

    prerequisite_ids = get_assessment_concepts(matched_goal.id)
    concepts_by_id = {concept.id: concept for concept in goals}

    if not prerequisite_ids:
        return (
            f"**Your learning goal:** {matched_goal.name}\n\n"
            "No prerequisite subjects were found for this goal.",
            matched_goal.id,
        )

    subject_names = [
        concepts_by_id[concept_id].name
        for concept_id in prerequisite_ids
        if concept_id in concepts_by_id
    ]

    # Styling works sometimes??
    response_text = (
        f"Your learning goal: **{matched_goal.name}**\n\n"
        "Study these prerequisite subjects first:\n\n"
        + "\n".join(f"- {name}" for name in subject_names)
        + "\n\nThe assessment tabs below contain questions for each subject."
    )

    return response_text, matched_goal.id

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Turbo Super Study Helper") as demo:
        gr.Markdown("# Turbo Super Study Helper")
        gr.Markdown("Skeleton version, running on fake data.")

        user_input = gr.Textbox(
            label="What do you want to learn?",
            placeholder="e.g. I want to learn the chain rule",
        )

        ask_btn = gr.Button(
            "Ask Turbo Super Study Helper",
            variant="primary",
        )

        agent_output = gr.Markdown()
        goal_state = gr.State(None)
        progress_state = gr.State({})

        ask_btn.click(
            fn=ask_agent,
            inputs=user_input,
            outputs=[agent_output, goal_state],
        )

        # Saved progress from disk, so a restart continues where the user left off.
        demo.load(fn=get_progress, inputs=None, outputs=progress_state)

        @gr.render(inputs=goal_state)
        def render_assessments(goal_id):
            if not goal_id: return

            prerequisite_ids = get_assessment_concepts(goal_id)

            if not prerequisite_ids:
                gr.Markdown("No prerequisite subjects found.")
                return

            concepts_by_id = {concept.id: concept for concept in list_goals()}

            with gr.Tabs():
                for concept_id in prerequisite_ids:
                    concept = concepts_by_id.get(concept_id)

                    subject_name = (
                        concept.name
                        if concept
                        else concept_id.replace("_", " ").title()
                    )

                    with gr.Tab(subject_name):
                        questions_state = gr.State([])
                        status_md = gr.Markdown(
                            "Questions for this topic are generated when you click the button."
                        )
                        load_btn = gr.Button("Generate questions")

                        # Fixed answer slots, hidden until the questions exist.
                        slots = []
                        for i in range(QUESTIONS_PER_TOPIC):
                            with gr.Group(visible=False) as group:
                                question_md = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
                                answer_box = gr.Textbox(label="Your answer")
                                check_btn = gr.Button("Check answer")
                                result_md = gr.Markdown()

                            gr.on(
                                triggers=[check_btn.click, answer_box.submit],
                                fn=_make_checker(i),
                                inputs=[goal_state, progress_state, questions_state, answer_box],
                                outputs=[progress_state, result_md, check_btn, answer_box],
                            )
                            slots += [group, question_md]

                        load_btn.click(
                            fn=_make_loader(concept_id),
                            inputs=None,
                            outputs=[questions_state, status_md, load_btn, *slots],
                        )

        material_btn = gr.Button("Get study material")
        material_md = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)

        def on_material(goal_id, progress):
            if not goal_id: return "Please enter a learning goal first."

            result = get_study_material(goal_id, progress)
            return _material_markdown(result)

        material_btn.click(
            fn=on_material,
            inputs=[goal_state, progress_state],
            outputs=material_md,
        )

    return demo