# Turbo super study helper tm

Starter template for the **Development of AI Applications** course final group project.

## Team members

- Member 1 Eetu Huotari (eetuh25@gmail.com)
- Member 2 Fei Raita (fei.raita@hotmail.com)
- Member 3 Lauri Raatikainen (lauri@raatikainen.fi)

## Problem

<img width="1272" height="655" alt="image" src="https://github.com/user-attachments/assets/d2fd0ed7-1622-4496-9b8d-a0fd6205eb97" />

Learning a difficult subject usually requires prior knowledge from several different areas. To learn X, you need to know Y and Z, and those have their own prerequisites. A teacher acts as an interface to that knowledge, but when teaching many students, each student has different knowledge gaps. To fill them, students have to search for information from different sources and teachers, which takes time and effort that could be spent on actually studying.

Our idea is an AI that you tell what you want to learn. It asks questions about closely related prerequisite knowledge to assess your level, then creates study material and quizzes for the knowledge you're missing. In the picture, red nodes are what you don't know and green nodes are what you know. The top node is your learning goal, which the gaps below it are preventing you from reaching.

We will start with logic-based subjects such as coding and math.

**TL;DR:** An AI that creates study material for you based on your missing knowledge.

### Intended users

Students and anyone who wants to learn a new subject.

### Problem statement

Difficult subjects require prior knowledge from many areas, and every student has different gaps. A teacher can't adapt to all of them, so students waste time searching for material and teachers instead of actually learning.

### Why AI is appropriate

Traditional, deterministic software can't take a request like "I want to learn X," find relevant study material, and turn it into a personalized study plan and quizzes.

## Solution

Our AI study assistant lets you focus on learning instead of searching for what to learn, where, from whom, and how. You tell it your goal, it finds your knowledge gaps, gathers study material, and turns it into a step-by-step plan with quizzes.

## Architecture

Below is the initial starter architecture. As your project evolves with additional capabilities, replace or extend this diagram in [`docs/architecture.md`](docs/architecture.md).

```text
User
  ↓
Gradio UI (app/ui.py)
  ↓
Application / AI Service (src/services/ai_service.py)
  ↓
Model Client (src/models/model_client.py)
  ↓
Ollama (Local LLM Server)
```

> **Core Architectural Rule:** The user interface must NEVER communicate directly with the model client or Ollama. All interactions must pass through the service layer (`ai_service.py`).

## Model

- Model used: llama3.2 (3B) via Ollama
- Selection rationale: It is lightweight enough to run locally on normal student laptops, which keeps the app free and private. It is good enough for generating explanations and quiz questions from provided material. If quality is not sufficient, we will test a larger model such as qwen2.5:7b and compare results in our evaluation.

## Additional AI capability

Select at least one additional capability to implement for your final project:

- [x] RAG (Retrieval-Augmented Generation)
- [x] Tools / External API integration
- [ ] Model Context Protocol (MCP)
- [ ] Agentic workflow (Model-selected actions based on observations)
- [x] Memory / Persistent state
- [ ] Multimodal interaction (Text + Images)
- [ ] Other: ______________________

### Capability justification
RAG: A small local model can produce incorrect or made-up explanations, which is a serious problem in a study tool. With RAG, study material and quizzes are generated from retrieved source documents (e.g. course material or open textbooks) instead of the model's own memory, and every piece of material can show its source. This makes the content more reliable and checkable.

Memory: The core idea of the app is to know what the user already knows and what they are missing. Persistent state stores the user's knowledge map (known and missing prerequisite topics) and quiz results between sessions, so the assistant does not have to re-test the user every time and can continue from their current gaps.

Verification step: After the local model generates study material and quizzes, the content is sent to a more capable external model (e.g. Claude via API) that fact-checks it against the retrieved sources and flags or corrects errors before the material is shown to the user. This combines the low cost and privacy of a local model with the accuracy of a stronger model, which is important because incorrect study material would teach the user wrong things.

## Setup

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
```

### 2. Activate the environment

```bash
conda activate dev-ai-project
```

### 3. Configure environment variables

Copy `.env.example` to create your local `.env` configuration file:

On Linux / macOS:
```bash
cp .env.example .env
```

On Windows (Command Prompt / PowerShell):
```powershell
copy .env.example .env
```

Ensure `.env` contains valid values for `OLLAMA_BASE_URL` and `MODEL_NAME`:
```env
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.2
```

### 4. Start Ollama

Make sure Ollama is installed and running locally, then pull your configured model:

```bash
ollama run llama3.2
```

### 5. Run the application

Run the application from the root directory of the project:

```bash
python -m app.main
```

Then open your browser at `http://localhost:7860`.

### 6. Run automated tests

```bash
pytest
```

## Evaluation

Describe your evaluation methodology and summarize key results. Starter test cases can be found in [`evaluation/test_cases.json`](evaluation/test_cases.json).

Refer to [`evaluation/README.md`](evaluation/README.md) for guidelines on defining success, edge cases, and failure scenarios.

## Known limitations

- Highlight known system limitations, unhandled edge cases, or boundaries of current capabilities.

## Future improvements

- List planned feature enhancements, architectural refactorings, or future capabilities.
