# Comprehensive Project Specification & Implementation Plan: AI-Driven Adaptive Multi-Agent Learning Platform

## 1. Executive Summary & Project Objectives

### 1.1. Executive Summary
This document establishes the official architectural blueprint, data communication contract, and four-week implementation master schedule for the **AI-Driven Adaptive Multi-Agent Learning Platform**. Moving away from traditional linear chatbots or static horizontal software silos, this platform leverages a stateful, decision-oriented multi-agent topography to deliver personalized, curriculum-grounded, age-appropriate, and continuously self-improving instruction.

The system decouples the heavy cognitive and generative operations into standalone, isolated worker modules wrapped around an asynchronous orchestration graph layer, while standardizing peripheral integrations via the Model Context Protocol (MCP). To achieve maximum developer velocity and ensure rigorous cross-training, a team of six engineers will operate across vertical, end-to-end feature slices—guaranteeing that every team member builds, tests, tunes, and optimizes core artificial intelligence systems, database ORMs, telemetry monitors, and generative client renderers.

### 1.2. Project Objectives & Educational Scope
The primary objective is the design and localized execution of an intelligent tutoring platform capable of hosting highly customized learning environments across three core subject domains:
* **Physical Sciences:** Concentrating on Newtonian Force systems, balanced/unbalanced vectors (F), momentum conservation, and equations of acceleration (a = F/m).
* **English Reading:** Concentrating on comprehension tracking, structural semantic textual analysis, vocabulary expansion scaffolding, and dense sentence deconstruction.
* **Math:** Concentrating on multi-dimensional Cartesian coordinates, vector arithmetic, and algebraic equation scaling across grade brackets.

The system is mathematically anchored to pedagogical optimization paradigms, explicitly mapping and tracking a student's **Zone of Proximal Development (ZPD)** and maintaining a strict **Mastery Learning Engine** threshold (>= 80%). The application must programmatically adapt vocabulary complexity, narrative framing configurations, hint density, and generative model temperatures based on continuous assessment signals, while systematically writing negative reinforcement constraint tokens to dynamically isolate and eliminate failed instructional strategies.

---

## 2. Platform Core Architecture & Multi-Agent Topology

The platform rejects fixed linear execution chains in favor of an event-driven, multi-tiered hybrid agent topology. Responsibilities are strictly partitioned across six independent layers to enforce separation of concerns, absolute environment isolation, and rapid debugging capabilities.

### 2.1. Architectural Layer Specifications

#### 1. LangGraph Orchestration Layer (Member 1)
Acts as the central master decision-state engine. Implemented in native Python via LangGraph, it manages the transactional lifecycle, graph edge routing conditions, state mutations, error limits, and hidden processing loops. It serves as the primary **MCP Client**, determining exactly when tool invocation is permissible and enforcing strict security barriers.

#### 2. Google ADK Specialization Layer
Serves as the high-performance execution runtime for specialized generative or structural worker agent nodes embedded inside LangGraph vertices. It leverages the Google GenAI SDK to interact directly with backend foundation models (gemini-2.5-pro and gemini-2.5-flash).

#### 3. LabModel Layer
The project-owned internal abstraction protocol that bifurcates LLM operations into two strictly decoupled operational roles:
* **LabModel-Worker:** The "Actor" role responsible for generating lessons, progressive hint configurations, diagnostic assessments, remediation branches, textual deconstructions, and dynamic roadmap schedules. It operates with a high latency budget and is programmatically barred from streaming directly to the client layer.
* **LabModel-Critic:** The "Reviewer" role tasked with evaluating Worker drafts independently. It grades outputs against rigid criteria parameters, covering curriculum alignment, retrieval grounding, cognitive load, hallucination risk, mathematical precision, and age-appropriateness constraints. It outputs structured JSON validation tokens and blocks any output that scores below a strict 80% evaluation mark.

#### 4. Model Context Protocol (MCP) Boundary (Member 6)
The standardized protocol layer powered by Python `FastMCP` that handles communications between internal cognitive agents and external system endpoints using JSON-RPC patterns over local stdio or Server-Sent Events (SSE). 

* **Permitted MCP Domains:** Accessing local workspace configuration files, reading teacher-uploaded curriculum documentation, syncing student Learning Management System (LMS) rosters, lookups within localized assessment banks, executing text searches across semantic knowledge structures, routing browser voice dictation arrays, and pushing output fields to dedicated metrics export files.
* **Banned MCP Domains:** MCP tools are strictly prohibited from performing internal graph state transitions, executing basic prompt formatting routines, evaluating interior Actor-Critic compliance scores, routing intent classifications, or updating core semantic and episodic student memory frames. MCP tools can never bypass the primary Policy Engine, safety checks, or final streaming clearance barriers.

#### 5. Project VectorDB & Storage Layer (Member 6)
A unified, local multi-model storage instance running a localized disk-backed SQLite engine via SQLAlchemy ORM alongside a separate, disk-persistent Qdrant Vector Client collection node.

#### 6. Renderer Client Layer (Member 3)
The front-end UI visual consumption node (presentation_ui). Implemented using pixel-perfect vanilla JavaScript, CSS micro-animations, and responsive HTML frameworks, it captures user telemetry metrics (click speeds, input latency, window tab-focus losses) and pipes them over bi-directional sockets to the orchestrator while operating as a high-fidelity vector puppeteer.

---

## 3. Composable Data Contract: State Design

To ensure total package composability and prevent development gridlocks across the six vertical feature slices, all communication boundaries utilize standard primitive schemas traveling through an immutable central Pydantic contract object.

### 3.1. LangGraph Orchestrator Central State Specification (state.py)
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentState(BaseModel):
    # --- 1. CORE SESSION IDENTITY CONTROLS ---
    user_id: str = Field(..., description="Unique user verification identifier.")
    session_id: str = Field(..., description="Unique UUID tracking the sandbox session.")
    character_hook: str = Field(..., description="Active hook persona wrapper.")
    grade_band: str = Field(..., description="Target NGSS curriculum development tier.")
    current_subject: str = Field('science', description='Active operational track.')
    current_mode: str = Field('onboarding', description='Active screen visual layout layout.')
    current_index: int = Field(0, description='Active global pointer index tracking progress.')
    
    # --- 2. ACTIVE INTERACTION TELEMETRY MATRIX ---
    focus_loss_count: int = Field(0, description='Counter tracking user tab-switching occurrences.')
    click_latency_ms: int = Field(0, description='Delta time between slide render and action.')
    attention_score: int = Field(9, ge=0, le=10, description='Calculated metric scoring user focus.')
    motivation_score: int = Field(8, ge=0, le=10, description='Derived scalar metric computing engagement.')
    score_xp: int = Field(1200, description='Persistent points written to SQLite.')
    attempt_history: Dict[int, int] = Field(default_factory=dict, description='Tracking exercise attempts.')
    rl_reward_metric: float = Field(0.0, description='Optimization feedback coefficient passed downstream.')
    
    # --- 3. DYNAMIC GENERATIVE PRESENTATION PAYLOADS ---
    generated_slides: List[Dict[str, Any]] = Field(default_factory=list, description='Visual card structures array.')
    active_task: Dict[str, Any] = Field(default_factory=dict, description='Dynamic question parameters.')
    evaluation_feedback: Dict[str, Any] = Field(default_factory=dict, description='Grading results vector.')
    trace_parent_id: Optional[str] = Field(None, description='OpenTelemetry context anchor pointer.')
```

---

## 4. Algorithmic Modules & AI Decision Tree Nodes

Every student action initiates an asynchronous non-linear routing pass supervised by the LangGraph execution tree. The orchestration loop evaluates metrics at key junctions.

### 4.1. Key Operational Nodes
* **Router Agent Node:** The mandatory entry checkpoint. Classifies intent into standard execution states: Instruction, Hint, Assessment, Deconstruction, Clarification, or Safe Redirect. Parses frustration and confusion sub-signals.
* **Policy Engine Node:** A regulatory safety gate mapping content safety levels: Fully Appropriate, Needs Simplification, Needs Context Restriction, Requires Adult Context, or Not Appropriate.
* **Self-RAG Evaluator Node:** Validates whether retrieval text is sufficient, contains background context information, or risks inducing model hallucinations.
* **CRAG (Corrective RAG) Repair Agent:** Activates automatically whenever retrieval score lands between 0.50 and 0.80. Executes query rewrites and pulls wider parent context frames.
* **GraphRAG Lite Reasoner:** Uses a concept vertex system with dependency edges to map prerequisites and inject background knowledge review components chronologically.
* **Auditor Agent Node:** Activates immediately when a student scores below 80% on tasks. Isolates broken analogies and writes Negative Reinforcement tokens to permanent storage.

### 4.2. Algorithmic Guardrails
* **Softmax Temperature Scaling:** Modulates model decoding parameters based on user demographics: Younger/Concrete learners use T=0.85; Collegiate/Technical learners use T=0.15.
* **Adaptive Hint Ladder:** Enforces sequential scaffolding rungs: Nudge -> Concept Reminder -> Partial Step -> Structured Scaffold -> Full Explanation.

---

## 5. Memory & Knowledge Base Infrastructure

### 5.1. Memory Architecture Layers
* **Persistent Semantic Memory:** Handles long-term parameters (student age, grade-band profiles, concept mastery history indexes).
* **Session-Based Episodic Memory:** Logs recent active interactions, recent assessment streaks, and successful instruction methods.
* **Negative Reinforcement Constraint Tokens:** Structured tokens written by the Auditor to explicitly block reuse of broken metaphors (e.g., 'Do not explain fractions using pizza slices for this student').

### 5.2. Parent-Child Chunking Protocols
* **Child Chunks (~50 Tokens):** Fine fragments optimized for semantic search lookups.
* **Parent Chunks (~500 Tokens):** Complete textbook context files pulled dynamically when a child matches to provide structural background reconstruction data.

---

## 6. Perceptual Multi-Modal Subsystems

### 6.1. Voice Audio Input/Output Sync Pipeline (Member 4)
Utilizes native Web Audio API wrappers to handle voice ingestion and speech playbacks. Transcribes vocal waveforms into text strings for the Router Agent, and prompt-tunes server text-to-speech rendering outputs to map matching cadences for specific persona types.

### 6.2. Generative Vector Canvas Renderer (Member 3)
The presentation client acts as an interactive vector art consumer. It parses incoming layout data coordinates (x, y, vector arrows) and paints them directly inside an inline HTML SVG viewport canvas using hardware-accelerated matrix transformations.

---

## 7. Capstone Optimization, Post-Training, & Evaluation Loops

To satisfy the core academic criteria of the Capstone project, the system implements two advanced optimization workflows: programmatic few-shot prompt compilation (DSPy) and parameter-level alignment optimization (GRPO & RLVR).

### 7.1. DSPy Prompt Compilation Workflow (Members 2 & 5)
Manual prompt engineering in the `teaching_agent` and `evaluator_agent` is entirely replaced with declarative **DSPy Signatures** and **Modules**.
* **Prompt Signatures:** Defined as class boundaries capturing inputs, reasoning paths, and target output schemas.
* **The Compilation Loop:** In Week 3, Member 2 and Member 5 compile these signatures using `dspy.teleprompt.BootstrapFewShot` or `MIPROv2`.
* **Dataset & Validation:** The optimization runs against a localized validation corpus of 50 student query-response pairs.
* **Measurement:** The project will measure and report the exact performance delta (win rate/accuracy) comparing the compiled DSPy output against handwritten baseline prompts.

### 7.2. GRPO & RLVR Post-Training Pipeline (Member 5)
The grading and feedback engine is optimized by fine-tuning a narrow, localized model (**Qwen-2.5-7B-Instruct** or **Llama-3-8B-Instruct**) using **Group-Relative Policy Optimization (GRPO)** paired with **Reward Learning with Verification and Reasoning (RLVR)**.

#### 1. Verifiable Reward Function ($R$)
The training compiler enforces a strict, programmatic reward function:
$$R = w_1 \cdot R_{\text{format}} + w_2 \cdot R_{\text{accuracy}} + w_3 \cdot R_{\text{pedagogy}}$$

* **JSON Format Reward ($R_{\text{format}}$):** Programmable validation checks if output parses to a valid JSON schema.
* **Academic Accuracy Reward ($R_{\text{accuracy}}$):** Validates accuracy against gold-standard responses retrieved from Qdrant via FastMCP.
* **Pedagogical Scaffold Reward ($R_{\text{pedagogy}}$):** Rewards completions that provide progressive hints and penalizes responses that give away answers prematurely.

#### 2. Group Advantage Calculation
For each training input, the pipeline generates a batch of $G = 4$ completions. It computes relative advantage metrics:
$$A_i = \frac{R_i - \mu_R}{\sigma_R}$$
This advantage is used to perform policy updates, enabling the small, constrained model to deliver enterprise-grade performance with minimal latency.

### 7.3. Stub/Mock Unit Testing Loops
A localized scenario simulation testing suite is built inside `tests/` using `pytest-mock` to guarantee the entire multi-agent orchestration tree can run in isolation.
* **Stub Class Models:** All Gemini API targets, network voice gateways, and database reads are simulated with predefined mock responses.
* **Offline Scenario Testing:** This allows developers to run complete mock classroom scenario loops, verifying state transitions and Edge routing conditions instantly without executing real model requests.

---

## 8. 4-Week MVP Milestones & Work Distribution

### 8.1. 6-Member Project Master Matrix

| Week | Member 1: Orchestrator | Member 2: Teaching Agent | Member 3: Presentation UI | Member 4: Voice I/O | Member 5: Evaluator Agent | Member 6: Data MCP Server |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Week 1** | FastAPI wrapper setup; configure Arize Phoenix tracers. | Model curriculum schema template definitions. | Code webpage outer container using placeholder SVGs. | Build microphone signal capture scripts. | Configure base OpenTelemetry span metrics tracking rules. | Initialize SQLite database schemas via SQLAlchemy ORM. |
| **Week 2** | Code central LangGraph routing state graphs. | Define DSPy Signatures for the Teaching Agent nodes. | Update client JS code to parse raw server JSON layout streams. | Integrate speech-to-text translation pipelines. | Connect evaluation signatures to active LangSmith dashboards. | Embed documents in Qdrant; expose tools via FastMCP. |
| **Week 3** | Implement backend RL Reward calculations. | Execute DSPy compilation loop using localized datasets. | Refactor visual viewports for dynamic SVG canvas generation. | Connect text-to-speech voice streams to Web Audio API. | Orchestrate local GRPO/RLVR small model fine-tuning loops. | Build database analytics tables inside SQLite to track rewards. |
| **Week 4** | Convert routes to persistent local WebSockets. | Run final prompt regression tests to prevent validation failures. | Link WebSocket events to dynamic vector visual animations. | Hook voice toggles directly over persistent communication lines. | Execute final validation sweeps across post-trained models. | Establish optimization database indexing on SQLite columns. |

### 8.2. Weekly Evolutionary Deliverables & Demo Protocols
* **Week 1 Demo (Foundations & Tracing):** Complete registration on the webpage. Data writes down to the SQLite database. Open Arize Phoenix to show OpenTelemetry tracking database spans.
* **Week 2 Demo (AI Agents & Knowledge):** Client layout copy parameters turn fluid, displaying narrative sequences, text strings, and quizzes dynamically generated by Gemini via LangGraph and FastMCP. Traces are logged in LangSmith.
* **Week 3 Demo (RL and Generative Art):** Choose Pikachu during onboarding. Client UI dynamically draws inline SVG Pikachu vectors. Intentionally click off the tab—the backend logs focus loss, and the DSPy-optimized engine automatically simplifies language on the next slide.
* **Week 4 Demo (Connected System Ecosystem):** Complete sandbox workspace running live over WebSockets. Speak into the microphone; audio transcribes, evaluates via post-trained small model, updates score parameters in SQLite, and fires a particle explosion animation on the frontend.

---

## 9. Future Production Scaling: AWS Serverless Mapping

Because the architecture standardizes on clean JSON-in/JSON-out primitive structures passing through local uv repositories, the codebase translates perfectly into cloud equivalents later:
* **FastAPI Backend Router** -> Amazon API Gateway + AWS Lambda Functions
* **SQLite Storage Layer** -> Amazon Aurora Serverless (PostgreSQL Connection String override)
* **LangGraph Agent Vertices** -> Isolated AWS Lambda Functions running the Google GenAI SDK
* **Qdrant Vector Engine** -> Hosted Qdrant Cloud Serverless endpoints
* **Presentation HTML UI Client** -> Simple Amazon S3 Bucket paired with Amazon CloudFront distribution channels.
