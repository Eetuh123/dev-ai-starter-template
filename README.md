# Turbo super study helper ™

## Team members

- Member 1 Eetu Huotari (eetuh25@gmail.com)
- Member 2 Fei Raita (fei.raita@hotmail.com)
- Member 3 Lauri Raatikainen (lauri@raatikainen.fi)

## Problem

<img width="1272" height="655" alt="image" src="https://github.com/user-attachments/assets/d2fd0ed7-1622-4496-9b8d-a0fd6205eb97" />

Learning a difficult subject often requires prior knowledge from several different areas. To learn X, you may need to understand Y and Z, which can have their own prerequisites. Teachers help students navigate this knowledge, but every student has different strengths and knowledge gaps. When teaching many students, it is difficult to address everyone's individual needs. Students may therefore spend considerable time searching for suitable learning materials and explanations instead of focusing on studying.

Our idea is an AI study assistant that lets users specify what they want to learn. It assesses their prerequisite knowledge through questions and generates study material and quizzes for topics they have not yet mastered. In the picture, red nodes represent knowledge gaps and green nodes represent known topics. The top node is the learning goal, and the gaps below it represent prerequisites that may prevent the learner from reaching that goal.

We start with logic-based subjects such as mathematics and coding.

**TL;DR**: An AI study assistant that creates learning material based on the user's missing prerequisite knowledge.

### Intended users

Students and anyone who wants to learn a new subject.

### Problem statement

Difficult subjects often require prior knowledge from multiple areas, and every learner has different knowledge gaps. It can be difficult for teachers to address all these individual needs, leaving students to spend time searching for suitable learning materials and explanations.

### Why AI is appropriate

A conventional rule-based system would struggle to interpret open-ended learning goals, generate explanations, and adapt the learning process to individual knowledge gaps. AI enables more flexible interaction and supports the generation of personalized study material and quizzes.

## Solution

Our AI study assistant helps users focus on learning instead of searching for what to learn, where to find information, and which prerequisites to study first. Users specify a learning goal, the application identifies relevant prerequisites and assesses their knowledge, then provides study material and quizzes for topics they need to improve.

## Architecture

The application uses a layered architecture in which the Gradio user interface communicates with the AI service layer in `src/services/ai_service.py`. The service coordinates the language model, RAG retrieval, assessments, learning progress, and lesson verification.

The main components are:

- **Gradio UI:** Collects learning goals, displays prerequisite topics and assessment tabs, and presents study material, quizzes, and progress.
- **AI service:** Coordinates the application workflow and connects the user interface to the underlying capabilities.
- **Ollama model client:** Communicates with the locally running language model used to generate responses and study material.
- **RAG retriever:** Retrieves relevant textbook chunks from the Chroma vector database using embeddings from `intfloat/multilingual-e5-small`.
- **Concept map:** Defines mathematics skills, prerequisite relationships, and relevant textbook modules.
- **Learning progress:** Tracks assessment results and learning progress.
- **Lesson verification:** Provides lesson review against retrieved source material using the Gemini API.

The user interface should not communicate directly with the model client or Ollama. Application interactions should pass through the service layer.

See [`docs/architecture.md`](docs/architecture.md) for the detailed architecture and component relationships.

## Model

- Model used: qwen3.5:9b via Ollama
- Selection rationale: qwen3.5:9b was selected because it achieved the highest correctness and clarity scores in our model comparison. Although it had the longest response time, the selection prioritizes the quality of educational content over speed.

## Additional AI capability

The project implements retrieval-augmented generation (RAG) to ground learning materials in relevant source documents, integrates an external AI service for lesson verification, and uses persistent memory to track users’ skills and learning progress.

### Capability justification

RAG: Small local models can generate incorrect explanations. Retrieval-Augmented Generation (RAG) retrieves relevant sections from sources such as OpenStax mathematics textbooks to ground generated lessons and quizzes in reliable material. Showing sources also helps users check the content, although RAG does not guarantee correctness.

Memory: The application tracks users’ knowledge and learning progress by saving quiz results and topic statuses. This persistent storage helps identify known and missing prerequisite topics and allows users to continue learning across sessions.

Verification: The application includes an optional verification feature that checks generated lessons against retrieved sources. Users can trigger it with the Verify lesson button, and the application displays the result and any reported issues. Topic lessons are initially unverified, while a separate study-material flow verifies lessons automatically and can apply corrections. Verification can help identify errors but does not guarantee mathematical accuracy.

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
MODEL_NAME=qwen3.5:9b
```

### 4. Start Ollama

Make sure Ollama is installed and running locally, then pull your configured model:

```bash
ollama run qwen3.5:9b
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

Install Conda-forge package channel:

```bash
conda install conda-forge::conda
```

Install Pandoc using conda-forge in the active environment:

```bash
conda install -c conda-forge pandoc
```

Check that Pandoc is installed:

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

Download Chromadb using Conda-forge:

```bash
conda install conda-forge::chromadb
```

Ensure that SentenceTransformers downloaded. If not, run:

```bash
conda install conda-forge::sentence-transformers
```

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

#### Verify lessons

Lesson verification requires Google's Generative AI package. Install the package and python-dotenv if they are not already installed:

```bash
conda install -c conda-forge google-genai python-dotenv
```

Obtain an API key from Google AI Studio:
https://aistudio.google.com/

Add your API key and the supported Gemini model name used by your implementation to .env:

```env
GEMINI_REVIEW_MODEL=gemini-3.8-flash
GEMINI_API_KEY=YOUR_API_KEY
```

Replace YOUR_API_KEY with your actual API key. Keep the key private and do not commit your .env file to Git.

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
- Fraction material can be too advanced for beginners.
- Generated lessons may contain mathematical errors despite using retrieved sources.
- Verification has not been evaluated sufficiently to establish how reliably it detects mathematical errors.

### 5. Run the application

Run the application from the project root:

```bash
python main.py
```

Then open your browser at `http://localhost:7860`.

### 6. Run automated tests

```bash
pytest
```

## Evaluation

The application was evaluated using nine test cases covering study material generation, retrieval-augmented generation (RAG), mathematical correctness, and error handling. The tests included preliminary manual UI testing, manual reviews of generated lessons, manual retrieval tests, and automated pytest tests.

Each test case included an expected behavior, an actual result, and a status of pass, fail, or partial. Of the nine test cases, six passed, two failed, and one partially passed.

The preliminary UI test demonstrated that the application could generate prerequisite study lessons, practice questions, and OpenStax source references using Llama 3.2. This was an earlier test and should not be interpreted as a test of the final selected model, qwen3.5:9b. The retrieval tests also showed that the system could retrieve relevant Chain Rule material and recognize the Finnish term ketjusääntö. Automated tests confirmed that unknown concepts and invalid top_k values were rejected before the Chroma collection was accessed.

However, manual reviews identified mathematical errors in two generated lessons. The derivative rules lesson contained an incorrect differentiation example, while the functions lesson incorrectly used the area formula for a square to describe a triangle. The fraction retrieval test partially passed because, although some relevant material was returned, the first result was too advanced for a beginner.

Overall, the evaluation showed that the main generation and retrieval functionality worked in the tested cases, but generated mathematical content was not always reliable. The evaluation was limited to nine test cases, and response times were not measured during the preliminary UI tests. The results should therefore be considered an initial assessment rather than a comprehensive measure of system reliability.

See [`evaluation/README.md`](evaluation/README.md) for more details.

## Known limitations

- **Mathematical correctness:** The language model can generate incorrect formulas, worked examples, and explanations. Successful lesson generation does not guarantee correctness.
- **Retrieval relevance:** Retrieved content can be relevant to a topic but still be too advanced for the intended learner.
- **Limited evaluation coverage:** Only nine test cases were evaluated, so the results do not cover all supported topics or possible user inputs.
- **Manual testing:** Several tests relied on manual inspection, which may be subjective and does not provide fully repeatable measurements.
- **Performance measurements:** Response times were not recorded during the preliminary UI tests.
- **Error-handling coverage:** Automated tests cover unknown concepts and invalid retrieval result counts, but the current test results do not establish how the application behaves during connection failures or other service errors.
- **Verification coverage:** The current test cases do not establish how reliably the lesson verification mechanism detects mathematical errors.

## Future improvements

- **Improve mathematical validation:** Add automated checks for common mathematical rules and worked examples, and expand tests to cover known correct and incorrect answers.
- **Strengthen lesson verification:** Evaluate the verification mechanism against lessons containing known mathematical errors and measure whether it identifies them reliably.
- **Improve retrieval quality:** Refine source selection and retrieval ranking so that beginner queries return simpler, more relevant explanations and numerical examples.
- **Expand test coverage:** Add cases for empty inputs, ambiguous learning goals, unsupported topics, malformed model responses, and unavailable Ollama or Gemini services.
- **Automate regression testing:** Turn repeatable evaluation cases into automated tests so that changes to prompts, retrieval, or generation can be checked consistently.
- **Measure performance:** Record response times for lesson generation and retrieval to identify bottlenecks and evaluate the user experience.
- **Improve multilingual support:** Test additional Finnish mathematical terms and alternative phrasings to assess how reliably the application recognizes learning goals across languages.
