import gradio as gr
import difflib
import json
import re
import html
import textwrap

from src.config import config
from src.services.ai_service import (
    list_goals,
    get_progress,
    start_assessment,
    submit_answer,
    start_topic,
    get_tree,
    get_topic_material,
    new_quiz,
    grade_quiz,
    QUIZ_QUESTIONS,
    get_assessment_concepts,
    get_questions,
    generate_response,
    verify_topic_material
)

css = """
.bridge { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; }
.tree-edge { stroke: #A1A1AA; stroke-width: 3; }
.tnode { cursor: pointer; }
.tnode circle { stroke-width: 3; transition: transform .12s; transform-box: fill-box; transform-origin: center; }
.tnode:hover circle { transform: scale(1.12); }
.tnode.untested circle { fill: #D4D4D8; stroke: #71717A; }
.tnode.known circle { fill: #86EFAC; stroke: #16A34A; }
.tnode.missing circle { fill: #FDBA74; stroke: #EA580C; }
.tmark { font-size: 22px; font-weight: 700; fill: #18181B; pointer-events: none; }
.tlabel { font-size: 13px; font-weight: 600; fill: var(--body-text-color, #27272A); pointer-events: none;
    paint-order: stroke; stroke: var(--background-fill-primary, #FFFFFF); stroke-width: 6px; stroke-linejoin: round; }
.topic-modal {
    position: fixed !important;
    top: 4vh; bottom: 4vh; left: 50%; right: auto;
    transform: translateX(-50%);
    width: min(92vw, 1000px) !important;
    max-width: none !important;
    min-width: 0 !important;
    flex: none !important;
    box-sizing: border-box;
    z-index: 1000;
    overflow-y: auto;
    padding: 20px;
    border-radius: 18px;
    background: var(--background-fill-primary);
    border: 1px solid var(--border-color-primary);
    box-shadow: 0 0 0 100vmax rgba(0, 0, 0, 0.55);
}

"""

def _question_text(question) -> str:
    if question is None:
        return "**Assessment done.** Click *Get study material* below."

    return f"**Question:** {question.question}"

QUESTIONS_PER_TOPIC = 10  # at most 10 questions per topic
FIRST_QUESTIONS = 5       # shown at the start, more appear one by one while 80% is still reachable

# Gradio only renders $$...$$ by default. Questions and lessons also use inline $...$.
LATEX_DELIMITERS = [
    {"left": "$$", "right": "$$", "display": True},
    {"left": "$", "right": "$", "display": False},
]

def _quiz_updates(questions):
    """Values for [quiz_state, quiz_status, (group, question_md, answer_box) x QUIZ_QUESTIONS, quiz_result, submit_btn, retry_btn]."""
    if not questions:
        status = "No quiz questions for this topic yet."
    else:
        status = f"Answer all {len(questions)} questions, then press *Submit quiz*. You need 80% right to pass."
    out = [questions, status]
    for i in range(QUIZ_QUESTIONS):
        if i < len(questions):
            out += [gr.update(visible=True), f"&nbsp;**Q{i + 1}:** {questions[i].question}",
                    gr.update(value="", interactive=True)]
        else:
            out += [gr.update(visible=False), "", gr.update(value="")]
    out += ["", gr.update(visible=bool(questions), interactive=True), gr.update(visible=False)]
    return out

def _practice_markdown(material) -> str:
    if not material.practice:
        return "No practice questions for this topic yet."
    return "### Practice\n\n" + "\n".join(
        f"{n}. {q.question}" for n, q in enumerate(material.practice, start=1))

def _answers_markdown(material) -> str:
    return "\n".join(f"{n}. `{q.answer}`" for n, q in enumerate(material.practice, start=1))

def _lesson_markdown(material) -> str:
    if material.error:
        return f"**Error:** {material.error}"
    
    parts = []
    if not material.lesson.verified and not material.verifier_issues:
        parts.append("> **Not verified.** This lesson was written by a small local model and has not "
                     "been fact-checked, so it may contain mistakes. Compare it with the sources. "
                     "**To verify lessons you need a Gemini API Key.**")
    
    if material.verifier_issues:
        parts.append("> **Verifier notes:**\n" + "\n".join(f"> - {i}" for i in material.verifier_issues))
    
    parts.append(material.lesson.content)
    return "\n\n".join(parts)

def verify_current_topic(concept_id, attempts):
    if not concept_id:
        return "", gr.update(visible=False), attempts

    attempts = attempts or []

    # A topic can only be verified once per session.
    if concept_id in attempts:
        material = get_topic_material(concept_id)
        return _lesson_markdown(material), gr.update(visible=False), attempts

    # Record the attempt before returning the result.
    attempts = attempts + [concept_id]

    material = verify_topic_material(concept_id)

    return (
        _lesson_markdown(material),
        gr.update(visible=False),
        attempts,
    )
def _make_loader(concept_id):
    """
    Button handler: generate the questions for one topic and reveal the first answer boxes.
    Returns values for: [questions_state, status_md, load_btn, progress_state, group_1, question_md_1, group_2, ...]
    """
    def load(progress):
        try:
            questions = get_questions(concept_id)
        except Exception as error:
            hidden = [gr.update(visible=False), ""] * QUESTIONS_PER_TOPIC
            return [[], f"**Could not generate questions:** {error}", gr.update(visible=True), progress, *hidden]

        if not questions:
            hidden = [gr.update(visible=False), ""] * QUESTIONS_PER_TOPIC
            return [[], "No questions available for this topic.", gr.update(visible=True), progress, *hidden]

        # A new round for this topic: old answers are cleared so they cannot mix with the new ones.
        progress = start_topic(progress, concept_id)

        slots = []
        for i in range(QUESTIONS_PER_TOPIC):
            if i < min(FIRST_QUESTIONS, len(questions)):
                slots += [gr.update(visible=True), f"**Q{i + 1}:** {questions[i].question}"]
            elif i < len(questions):
                # Prepared for later, shown only while the result is open.
                slots += [gr.update(visible=False), f"**Q{i + 1}:** {questions[i].question}"]
            else:
                slots += [gr.update(visible=False), ""]

        return [questions, "Answer the questions below.", gr.update(visible=False), progress, *slots]
    return load

def _make_checker(index):
    """
    Answer handler for question number `index` of a topic.
    Returns values for: [progress_state, result_md, check_btn, answer_box, group_1, group_2, ...]
    """
    def check(goal_id, progress, questions, answer):
        nothing = [gr.update()] * QUESTIONS_PER_TOPIC

        if index >= len(questions):
            return progress, "", gr.update(), gr.update(), *nothing

        step = submit_answer(goal_id, progress, questions[index], answer)

        # Empty answer: submit_answer hands the question back, so let the user try again.
        if step.question is not None:
            return step.progress, step.message, gr.update(), gr.update(), *nothing

        # The topic is still open (under 80% but 80% is reachable): show one more question.
        groups = nothing
        if step.topic_status == "untested":
            entry = step.progress.get(questions[index].concept_id)
            answered = len(entry.quiz_scores) if entry else 0
            shown = min(len(questions), max(FIRST_QUESTIONS, answered + 1))
            groups = [
                gr.update(visible=True) if i < shown else gr.update()
                for i in range(QUESTIONS_PER_TOPIC)
            ]

        # Answered: lock the box so one question cannot be scored twice.
        return step.progress, step.message, gr.update(interactive=False), gr.update(interactive=False), *groups
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

def _layout(node, depth=0, counter=None):
    """Give every node a column (x) and a row (depth): leaves side by side, parents centered above their children."""
    counter = counter if counter is not None else [0]
    if not node["children"]:
        x = float(counter[0])
        counter[0] += 1
        return {"id": node["id"], "depth": depth, "x": x, "children": []}
    kids = [_layout(child, depth + 1, counter) for child in node["children"]]
    return {"id": node["id"], "depth": depth, "x": (kids[0]["x"] + kids[-1]["x"]) / 2, "children": kids}

# Clicking a node writes its id into a hidden textbox and presses a hidden button (see build_ui).
CLICK_JS = (
    "var t=document.querySelector('#node-pick textarea,#node-pick input');"
    "t.value='{id}';t.dispatchEvent(new Event('input',{{bubbles:true}}));"
    "setTimeout(function(){{document.querySelector('#node-go').click()}},120)"
)
STATUS_MARK = {"known": "\u2713", "missing": "!", "untested": "?"}

def _tree_svg(tree, names, status_of) -> str:
    """
    The learning map as an SVG: circles for topics, lines for 'needs this first'. 
    Nodes are clickable.
    """
    
    root = _layout(tree)
    gap_x, gap_y, margin, top, radius = 150, 150, 90, 45, 28

    flat, edges = [], []
    def walk(node):
        flat.append(node)
        for child in node["children"]:
            edges.append((node, child))
            walk(child)
    walk(root)

    leaves = max(node["x"] for node in flat) + 1
    depth = max(node["depth"] for node in flat)
    width = max(320, int((leaves - 1) * gap_x + 2 * margin))
    height = int(top + depth * gap_y + 110)
    pos = lambda node: (margin + node["x"] * gap_x + (width - 2 * margin - (leaves - 1) * gap_x) / 2,
                        top + node["depth"] * gap_y)

    parts = [f'<svg class="tree-svg" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
             f'style="max-width:{width}px;width:100%;height:auto;display:block;margin:0 auto">']
    for parent, child in edges:
        (x1, y1), (x2, y2) = pos(parent), pos(child)
        parts.append(f'<line class="tree-edge" x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}"/>')

    for node in flat:
        x, y = pos(node)
        name = names.get(node["id"], node["id"].replace("_", " ").title())
        status = status_of(node["id"])
        click = html.escape(CLICK_JS.format(id=node["id"]), quote=True)
        label = "".join(
            f'<tspan x="{x:.0f}" dy="{0 if i == 0 else 15}">{html.escape(line)}</tspan>'
            for i, line in enumerate(textwrap.wrap(name, 16)[:3])
        )
        parts.append(
            f'<g class="tnode {status}" onclick="{click}">'
            f'<title>{html.escape(name)}</title>'
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{radius}"/>'
            f'<text class="tmark" x="{x:.0f}" y="{y + 7:.0f}" text-anchor="middle">{STATUS_MARK.get(status, "?")}</text>'
            f'<text class="tlabel" x="{x:.0f}" y="{y + radius + 20:.0f}" text-anchor="middle">{label}</text>'
            f'</g>'
        )
    parts.append("</svg>")
    return "".join(parts)

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

    response_text = ""

    return response_text, matched_goal.id

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Turbo Super Study Helper", css=css) as demo:
        with gr.Row():
            gr.Column(scale=1)  # Spacers for centering
            with gr.Column(scale=4):
                gr.Markdown("# Turbo Super Study Helper")
                gr.Markdown("Tell me what you want to learn. I find the gaps in your knowledge and teach them.")

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

                def ask_and_build_tree(user_message):
                    response_text, goal_id = ask_agent(user_message)
                    return response_text, goal_id or None

                # Saved progress from disk, so a restart continues where the user left off.
                demo.load(fn=get_progress, inputs=None, outputs=progress_state)

                ask_btn.click(
                    fn=ask_and_build_tree,
                    inputs=user_input,
                    outputs=[agent_output, goal_state],
                )

                topic_state = gr.State(None)      # topic open in the window
                quiz_state = gr.State([])         # questions of the current quiz attempt
                verified_attempts = gr.State([])

                # --- Topic window: opens when a topic is clicked, tabs Study material / Quiz ---
                with gr.Column(visible=False, elem_classes="topic-modal") as modal:
                    with gr.Row():
                        modal_title = gr.Markdown()
                        close_btn = gr.Button("Close", scale=0, min_width=100)
                    with gr.Tabs():
                        with gr.Tab("Study material"):
                            lesson_md = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
                            verify_btn = gr.Button("Verify lesson", variant="primary")
                            verify_btn.click(
                                fn=verify_current_topic,
                                inputs=[topic_state, verified_attempts],
                                outputs=[lesson_md, verify_btn, verified_attempts],
                            )
                            practice_md = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
                            
                            with gr.Accordion("Show practice answers", open=False):
                                answers_md = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
                        with gr.Tab("Quiz"):
                            quiz_status = gr.Markdown()
                            quiz_groups, quiz_mds, quiz_boxes, quiz_slots = [], [], [], []
                            for i in range(QUIZ_QUESTIONS):
                                with gr.Group(visible=False) as qgroup:
                                    qmd = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
                                    qbox = gr.Textbox(label="Your answer")
                                quiz_groups.append(qgroup)
                                quiz_mds.append(qmd)
                                quiz_boxes.append(qbox)
                                quiz_slots += [qgroup, qmd, qbox]
                            submit_btn = gr.Button("Submit quiz", variant="primary", visible=False)
                            quiz_result = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
                            retry_btn = gr.Button("Try again with new questions", visible=False)

                quiz_outputs = [quiz_state, quiz_status, *quiz_slots, quiz_result, submit_btn, retry_btn]

                def open_topic(concept_id, name):
                    # Fast step: show the window at once, the slow lesson is filled in by the next step.
                    return (gr.update(visible=True), concept_id, f"## {name}",
                            "Writing the lesson from the textbook sources, this can take a minute...",
                            "", "", *_quiz_updates([]))

                def load_topic(concept_id, attempts):
                    material = get_topic_material(concept_id)
                    if material.error:
                        gr.update(visible=concept_id not in (attempts or []))
                        return (f"## {material.concept.name}", _lesson_markdown(material), "", "",
                                *_quiz_updates([]))
                    questions = new_quiz(concept_id)
                    gr.update(visible=concept_id not in (attempts or []))
                    return (f"## {material.concept.name}", _lesson_markdown(material),
                            _practice_markdown(material), _answers_markdown(material),
                            *_quiz_updates(questions))

                topic_outputs = [modal, topic_state, modal_title, lesson_md, practice_md, answers_md, *quiz_outputs]
                load_outputs = [modal_title, lesson_md, practice_md, answers_md, *quiz_outputs]

                def submit_quiz(goal_id, progress, concept_id, questions, *answers):
                    result = grade_quiz(progress, concept_id, questions, list(answers))
                    lines = "\n".join(result.feedback)
                    if result.passed:
                        head = f"**Passed: {result.right}/{result.total} right.** The topic is now marked as known."
                    else:
                        head = (f"**Not passed: {result.right}/{result.total} right**, 80% is needed. "
                                "Check the answers below, read the lesson again and try with new questions.")
                    return (result.progress, f"{head}\n\n{lines}",
                            gr.update(interactive=False), gr.update(visible=not result.passed),
                            *[gr.update(interactive=False) for _ in quiz_boxes])

                def retry_quiz(concept_id, questions):
                    return _quiz_updates(new_quiz(concept_id, [q.question for q in questions]))

                submit_btn.click(
                    fn=submit_quiz,
                    inputs=[goal_state, progress_state, topic_state, quiz_state, *quiz_boxes],
                    outputs=[progress_state, quiz_result, submit_btn, retry_btn, *quiz_boxes],
                )
                retry_btn.click(fn=retry_quiz, inputs=[topic_state, quiz_state], outputs=quiz_outputs)
                close_btn.click(fn=lambda: gr.update(visible=False), outputs=modal)

                # --- Learning map: the goal on top, its prerequisites below. Click a node to open it. ---
                # Hidden bridge: the click in the SVG fills this textbox and presses this button.
                node_pick = gr.Textbox(elem_id="node-pick", elem_classes="bridge", show_label=False)
                node_go = gr.Button("open", elem_id="node-go", elem_classes="bridge")

                def open_by_id(concept_id):
                    names = {concept.id: concept.name for concept in list_goals()}
                    return open_topic(concept_id, names.get(concept_id, concept_id.replace("_", " ").title()))

                node_go.click(fn=open_by_id, inputs=node_pick, outputs=topic_outputs).then(
                    fn=load_topic, inputs=topic_state, outputs=load_outputs,
                )

                @gr.render(inputs=[goal_state, progress_state])
                def render_tree(goal_id, progress):
                    if not goal_id: return
                    tree = get_tree(goal_id)
                    if not tree:
                        gr.Markdown("No topics found for this goal.")
                        return

                    names = {concept.id: concept.name for concept in list_goals()}

                    def status_of(concept_id):
                        entry = (progress or {}).get(concept_id)
                        return entry.status if entry else "untested"

                    gr.Markdown(
                        "**Learning map.** The goal is on top and what you need to know first is below it. "
                        "Click a topic to open its study material and quiz. "
                        "Green = known, orange = gap, grey = not tested."
                    )
                    gr.HTML(_tree_svg(tree, names, status_of))
            gr.Column(scale=1)

    return demo

'''
subject_names = [
        concepts_by_id[concept_id].name
        for concept_id in prerequisite_ids
        if concept_id in concepts_by_id
    ]

Bullet point list of prerequisites
response_text = (
        f"Your learning goal: **{matched_goal.name}**\n\n"
        "Study these prerequisite subjects first:\n\n"
        + "\n".join(f"- {name}" for name in subject_names)
        + "\n\nThe assessment tabs below contain questions for each subject."
    )
'''
'''
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
groups = []
parts = []
for i in range(QUESTIONS_PER_TOPIC):
    with gr.Group(visible=False) as group:
        question_md = gr.Markdown(latex_delimiters=LATEX_DELIMITERS)
        answer_box = gr.Textbox(label="Your answer")
        check_btn = gr.Button("Check answer")
        result_md = gr.Markdown()
    groups.append(group)
    parts.append((check_btn, answer_box, result_md))
    slots += [group, question_md]

for i, (check_btn, answer_box, result_md) in enumerate(parts):
    gr.on(
        triggers=[check_btn.click, answer_box.submit],
        fn=_make_checker(i),
        inputs=[goal_state, progress_state, questions_state, answer_box],
        outputs=[progress_state, result_md, check_btn, answer_box, *groups],
    )

load_btn.click(
    fn=_make_loader(concept_id),
    inputs=progress_state,
    outputs=[questions_state, status_md, load_btn, progress_state, *slots],
)
'''