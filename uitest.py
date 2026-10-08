import gradio as gr

from src.services.ai_service import (
    list_goals,
    start_assessment,
    submit_answer,
    get_study_material,
)


def _question_text(question) -> str:
    if question is None:
        return "**Assessment done.** Click *Get study material* below."
    return f"**Question:** {question.question}"


def _material_markdown(result) -> str:
    if result.error:
        return f"**Error:** {result.error}"
    if not result.items:
        return "No gaps found, nothing to study."

    parts = []
    for item in result.items:
        badge = "verified" if item.lesson.verified else "UNVERIFIED"
        parts.append(f"## {item.concept.name} ({badge})\n\n{item.lesson.content}")
        if item.verifier_issues:
            parts.append("**Verifier notes:**\n" + "\n".join(f"- {i}" for i in item.verifier_issues))
        if item.quiz:
            parts.append("**Practice:**\n" + "\n".join(f"- {q.question}" for q in item.quiz))
    return "\n\n".join(parts)


def build_ui() -> gr.Blocks:
    """
    Skeleton UI. Only talks to the service layer, never to models directly.
    Ugly on purpose: Fei replaces it.
    """
    goals = [(c.name, c.id) for c in list_goals()]

    with gr.Blocks(title="Turbo Super Study Helper") as demo2:
        gr.Markdown("# Turbo Super Study Helper\nSkeleton version, running on fake data.")

        # Per-browser-session state
        progress_state = gr.State({})
        question_state = gr.State(None)

        goal = gr.Dropdown(
            choices=goals,
            value=goals[-1][1] if goals else None,
            label="What do you want to learn?",
        )
        start_btn = gr.Button("Start NOW", variant="primary")

        question_md = gr.Markdown()
        answer_box = gr.Textbox(label="Your answer", placeholder="e.g. 2*x")
        answer_btn = gr.Button("Submit answer")
        feedback_md = gr.Markdown()

        material_btn = gr.Button("Get study material")
        material_md = gr.Markdown()

        def on_start(goal_id):
            step = start_assessment(goal_id)
            return step.progress, step.question, _question_text(step.question), step.message

        def on_answer(goal_id, progress, question, text):
            step = submit_answer(goal_id, progress, question, text)
            return step.progress, step.question, _question_text(step.question), step.message, ""

        def on_material(goal_id, progress):
            return _material_markdown(get_study_material(goal_id, progress))

        start_btn.click(
            on_start,
            inputs=goal,
            outputs=[progress_state, question_state, question_md, feedback_md],
        )
        
        answer_inputs = [goal, progress_state, question_state, answer_box]
        answer_outputs = [progress_state, question_state, question_md, feedback_md, answer_box]
        answer_btn.click(on_answer, inputs=answer_inputs, outputs=answer_outputs)
        answer_box.submit(on_answer, inputs=answer_inputs, outputs=answer_outputs)

        material_btn.click(on_material, inputs=[goal, progress_state], outputs=material_md)

    return demo2