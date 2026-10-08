import gradio as gr

from src.services.ai_service import (
    list_goals,
    start_assessment,
    submit_answer,
    get_study_material,
    get_assessment_concepts,
    get_questions,
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

def build_ui() -> gr.Blocks:
    goals = [
        (concept.name, concept.id)
        for concept in list_goals()
    ]

    with gr.Blocks(title="Turbo Super Study Helper") as demo:
        gr.Markdown(
            "Skeleton version, running on fake data."
        )

        progress_state = gr.State({})
        question_state = gr.State(None)

        goal = gr.Dropdown(
            choices=goals,
            value=goals[-1][1] if goals else None,
            label="What do you want to learn?",
        )

        start_btn = gr.Button(
            "Start Assesment",
            variant="primary",
        )

        @gr.render(inputs=goal)
        def render_assessments(goal_id):
            if not goal_id: return

            concepts = get_assessment_concepts(goal_id)
            if not concepts:
                gr.Markdown("No prerequisite subjects found.")
                return

            # Jokainen täbi oma aihealueensa, jokaisella omat kysymykset
            with gr.Tabs():
                for concept_id in concepts:
                    subject_name = (concept_id.replace("_", " ").title())
                    questions = get_questions(concept_id)

                    with gr.Tab(subject_name):
                        if not questions:
                            gr.Markdown("No questions available.")
                            continue

                        for index, question in enumerate(questions, start=1):
                            gr.Markdown(
                                f"**Q{index}**: "
                                f"{question.question}"
                            )

                            gr.Textbox(
                                label=f"Answer {index}",
                                placeholder="Type your answer here..."
                            )

        material_btn = gr.Button("Get study material")
        material_md = gr.Markdown()

        def on_start(goal_id):
            step = start_assessment(goal_id)
            return (step.progress, step.question)

        def on_material(goal_id, progress):
            return _material_markdown(get_study_material(goal_id, progress))

        start_btn.click(
            on_start,
            inputs=goal,
            outputs=[progress_state, question_state],
        )

        material_btn.click(
            on_material,
            inputs=[goal, progress_state,],
            outputs=material_md,
        )
        
    return demo