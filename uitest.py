import gradio as gr

from src.services.ai_service import (
    list_goals,
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

    if matched_goal is None:
        goal_options = "\n".join(
            f"{concept.id}: {concept.name} — {concept.description}"
            for concept in goals
        )

        prompt = f"""
            You are a mathematics learning-goal classifier.

            The student may use a full sentence, extra words, or spelling mistakes.
            Identify the intended topic and match it to the closest concept below.
            Choose the single best matching goal from this list.

            Available goals:
            {goal_options}

            User's learning goal:
            {user_message}

            Return ONLY the exact goal ID from the list.
            If none matches, return NONE.
            """

        try: response = generate_response(prompt).strip()
        except Exception as error:
            return f"Could not identify the learning goal: {error}", None

        selected_id = response.strip().strip('`"\' ')
        matched_goal = next((
                concept for concept in goals
                if concept.id.lower() == selected_id.lower()
            ), None,
        )

        if matched_goal is None:
            matched_goal = next((
                    concept for concept in goals
                    if concept.id.lower() in response.lower()
                ), None,
            )

        if matched_goal is None or selected_id.upper() == "NONE":
            return (
                "I couldn't match that learning goal to the available "
                "topics. Try Functions, Limits, Derivative rules or Chain rule.",
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

                    questions = get_questions(concept_id)

                    with gr.Tab(subject_name):
                        if not questions:
                            gr.Markdown("No questions available.")
                        else:
                            for index, question in enumerate(questions, start=1):
                                gr.Markdown(f"**Q{index}:** {question.question}")

                                gr.Textbox(
                                    label=f"Answer {index}",
                                    placeholder="Type your answer here...",
                                )

        material_btn = gr.Button("Get study material")
        material_md = gr.Markdown()

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