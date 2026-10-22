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
   AI Service (src/services/ai_service.py)
     ├─→ Retriever (RAG: source documents)
     ├─→ Memory (user knowledge map + quiz results)
     ├─→ Model Client → Ollama (local LLM, generates material)
     └─→ Verification Client → External API (e.g. Claude, fact-check)
```

> **Core Architectural Rule:** The user interface must NEVER communicate directly with the model client or Ollama. All interactions must pass through the service layer (`ai_service.py`).

## Model

- Model used: llama3.2 (3B) via Ollama
- Selection rationale: llama3.2 (3B) is the initial local baseline. Preliminary testing produced mathematical errors even with retrieved source material. A comparison of correctness, explanation clarity, and response time will be used to justify the final model selection.

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

Verification step (planned): A stronger external model could check generated lessons against the retrieved sources. This integration is not implemented in the current version. The verifier returns an unverified status and displays a notice that generated content may contain mathematical errors.

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

### 4a. Prepare the book data and RAG index (Windows)

Run the commands below from the project root with the Conda environment activated:

```bash
conda activate dev-ai-project
```

The current indexing script uses Windows `LOCALAPPDATA`. Other operating systems require a database path adjustment in `scripts/index_books.py` and a matching retrieval configuration.

#### Download the source books

Download both OpenStax repositories using **Code → Download ZIP**:

- https://github.com/openstax/osbooks-college-algebra-bundle
- https://github.com/openstax/osbooks-calculus-bundle

Extract the repository folders into `data/books/raw/`.

Check that these files exist directly at the following paths, without an extra nested repository folder:

- `data/books/raw/osbooks-college-algebra-bundle-main/collections/college-algebra-2e.collection.xml`
- `data/books/raw/osbooks-college-algebra-bundle-main/collections/precalculus-2e.collection.xml`
- `data/books/raw/osbooks-calculus-bundle-main/collections/calculus-volume-1.collection.xml`

Each repository folder must also contain its `modules` directory.

The project uses three books: **College Algebra 2e**, **Precalculus 2e**, and **Calculus Volume 1**.

#### Convert the books

Pandoc must be installed and available in the active environment:

```bash
pandoc --version
```

Convert each book:

```bash
python scripts/convert_book.py --book algebra
python scripts/convert_book.py --book precalculus
python scripts/convert_book.py --book calculus
```

The conversion script also requires `scripts/convert_module.py`.

The generated Markdown files contain LaTeX formulas and are saved in:

- `data/books/processed/college-algebra-2e/`
- `data/books/processed/precalculus-2e/`
- `data/books/processed/calculus-volume-1/`

Each folder includes `manifest.json` and `conversion_errors.json`. Check that the conversion reports zero failures.

#### Create the text chunks

Ensure that `.env` includes:

```env
CONCEPT_MAP_PATH=data/concepts.json
```

The concept map defines the skills, their prerequisites, and their source modules.

Run:

```bash
python scripts/chunk_books.py
```

This reads the source modules referenced in `data/concepts.json`, splits their text into chunks, and attaches skill IDs and source references.

Output: `data/rag/chunks.jsonl`.

Only modules referenced in the concept map are included in the RAG index.

#### Build the Chroma index

Run:

```bash
python scripts/index_books.py
```

The first run downloads the embedding model `intfloat/multilingual-e5-small`. The script generates embeddings on the CPU and stores the text chunks and metadata in a persistent Chroma database.

On Windows, the database is stored outside the project directory:

```text
%LOCALAPPDATA%\dev-ai-project\chroma
```

The collection name is `openstax_math_e5_v2`. Indexing and retrieval must use the same database path, collection name, and embedding model.

Each team member must build the index on their own computer. Repeating indexing with the same input does not create duplicate chunks. If the input changes, the script rejects the existing collection and it must be rebuilt.

#### Test retrieval

Run:

```bash
python scripts/search_books.py "ketjusääntö"
```

The results should include **The Chain Rule** from **Calculus Volume 1**, module `m53581`, with source references.

To test the retrieval function used by the application:

```bash
python -c "from src.capabilities.rag import retrieve; [print(c.book, c.section, c.source_url, sep='\n') for c in retrieve('chain_rule')]"
```

Retrieval works independently of Ollama. Generating study lessons requires Ollama and the configured language model.

#### Files excluded from Git

Keep the downloaded books, converted books, and generated RAG files out of Git. Ensure `.gitignore` contains:

```gitignore
/data/books/
/data/rag/
```

Commit the scripts, `data/concepts.json`, dependency configuration, and documentation.

#### Current limitations

- Skill tags are assigned at module level, so retrieved chunks may cover a broader topic than the requested skill.
- Images are represented by text descriptions, and some internal textbook references remain unresolved.
- Fraction material mostly comes from a section on rational expressions and can be too advanced for beginners.
- Generated lessons may contain mathematical errors despite using retrieved sources.
- Automatic content verification is not implemented. Lessons are displayed as unverified.

### 5. Run the application

Run the application from the root directory of the project:

```bash
python main.py
```
Or to use hot reaload run:
```bash
gradio main.py
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
