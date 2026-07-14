# Comprehensive Project Specification & Implementation Plan: AI-Driven Adaptive Multi-Agent Learning Platform

> **Revision note:** This version adds Section 4.3 (domain-specific node
> behavior for Reading and Math -- previously only Physics had a worked
> example, despite Section 1.2 naming three subject domains), Section 7
> (Teacher Dashboard & Classroom Management -- previously implied by the
> MCP permitted-domains list but never designed), Section 8.4 (Pedagogical
> Efficacy Validation -- the highest-priority gap from review: this spec
> previously measured model output quality but never whether students
> actually learn more), and Section 11 (Known Shortcomings & Future Work
> -- an honest list of what still isn't addressed). Sections 7 onward from
> the prior draft are renumbered accordingly (old 7 -> 8, old 8 -> 9, old
> 9 -> 10). Everything else is unchanged from the original draft.

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

#### 1. LangGraph Orchestration Layer
Acts as the central master decision-state engine. Implemented in native Python via LangGraph, it manages the transactional lifecycle, graph edge routing conditions, state mutations, error limits, and hidden processing loops. It serves as the primary **MCP Client**, determining exactly when tool invocation is permissible and enforcing strict security barriers.

#### 2. Google ADK Specialization Layer
Serves as the high-performance execution runtime for specialized generative or structural worker agent nodes embedded inside LangGraph vertices. It leverages the Google GenAI SDK to interact directly with backend foundation models (gemini-2.5-pro and gemini-2.5-flash).

#### 3. LabModel Layer
The project-owned internal abstraction protocol that bifurcates LLM operations into two strictly decoupled operational roles:
* **LabModel-Worker:** The "Actor" role responsible for generating lessons, progressive hint configurations, diagnostic assessments, remediation branches, textual deconstructions, and dynamic roadmap schedules. It operates with a high latency budget and is programmatically barred from streaming directly to the client layer.
* **LabModel-Critic:** The "Reviewer" role tasked with evaluating Worker drafts independently. It grades outputs against rigid criteria parameters, covering curriculum alignment, retrieval grounding, cognitive load, hallucination risk, mathematical precision, and age-appropriateness constraints. It outputs structured JSON validation tokens and blocks any output that scores below a strict 80% evaluation mark.

#### 4. Model Context Protocol (MCP) Boundary
The standardized protocol layer powered by Python `FastMCP` that handles communications between internal cognitive agents and external system endpoints using JSON-RPC patterns over local stdio or Server-Sent Events (SSE). 

* **Permitted MCP Domains:** Accessing local workspace configuration files, reading teacher-uploaded curriculum documentation, syncing student Learning Management System (LMS) rosters, lookups within localized assessment banks, executing text searches across semantic knowledge structures, routing browser voice dictation arrays, and pushing output fields to dedicated metrics export files.
* **Banned MCP Domains:** MCP tools are strictly prohibited from performing internal graph state transitions, executing basic prompt formatting routines, evaluating interior Actor-Critic compliance scores, routing intent classifications, or updating core semantic and episodic student memory frames. MCP tools can never bypass the primary Policy Engine, safety checks, or final streaming clearance barriers.

#### 5. Project VectorDB & Storage Layer
A unified, local multi-model storage instance running a localized disk-backed SQLite engine via SQLAlchemy ORM alongside a separate, disk-persistent Qdrant Vector Client collection node.

#### 6. Renderer Client Layer
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

### 4.3. Domain-Specific Node Behavior (Physical Sciences / English Reading / Math)
Section 1.2 names three subject domains, but every worked example prior to
this revision was Physical Sciences only -- Reading and Math were named,
never designed. This section gives each domain the same node-level
treatment Physics already had, so a team member picking up either domain
has something concrete to build against rather than "the same as Physics,
presumably."

Each domain reuses the identical six-layer architecture and AgentState
contract from Sections 2-3 unchanged -- only what the nodes *check for*
changes per domain.

**Physical Sciences (unchanged from the original draft)**
* **Standards family:** Next Generation Science Standards (NGSS), e.g. `3-PS2-1`.
* **GraphRAG Lite prerequisite graph:** concept vertices are physical laws (e.g. `law_1_inertia -> law_2_f_equals_ma`); edges represent "must understand law_1 before law_2 is well-posed."
* **Self-RAG / CRAG grounding target:** retrieved formulas and constants (e.g. `a = ΣF/m`) must match the ground-truth ConceptDefinition exactly -- CRAG activates on a low retrieval-confidence score, not on a wrong formula reaching the student uncorrected.
* **Worked example:** a 10 kg box, two opposing 50 N forces, ΣF = 0, a = 0 m/s² -- the Worker states the law, the Critic checks the arithmetic is internally consistent with the stated forces and mass.

**English Reading (new in this revision)**
* **Standards family:** Common Core ELA (`CCSS.ELA-LITERACY.RL/RI.*`), e.g. `CCSS.ELA-LITERACY.RI.4.2` (determine the main idea of a text).
* **GraphRAG Lite prerequisite graph:** concept vertices are reading skills, not facts (e.g. `vocabulary_in_context -> main_idea_identification -> inference_from_evidence`) -- edges represent skill dependency, not factual dependency, a materially different graph shape than Physics' law-dependency graph and should not be built by copying it.
* **Self-RAG / CRAG grounding target:** retrieved *passage text* must be the actual student-assigned excerpt (from teacher-uploaded curriculum documentation, Section 2.1.4's Permitted MCP Domains), not a paraphrase or a different passage on the same topic -- CRAG activating here means "re-fetch the correct excerpt," a different repair action than Physics' "rewrite the query."
* **Worked example:** given a 3rd-grade passage about a character solving a problem, Router classifies a student question ("why did she do that?") as Deconstruction, not Hint; GraphRAG Lite confirms `inference_from_evidence` is unlocked (student has passed `vocabulary_in_context`); Worker generates a scaffolded question sequence (not a direct answer) pointing back to specific sentences in the passage; Critic checks every scaffold question cites an actual sentence in the retrieved passage -- a text-grounding hallucination check, distinct from Physics' arithmetic-consistency check.

**Math (new in this revision)**
* **Standards family:** Common Core Math (`CCSS.MATH.CONTENT.*`), e.g. `CCSS.MATH.CONTENT.5.G.A.1` (the Cartesian coordinate plane).
* **GraphRAG Lite prerequisite graph:** concept vertices are operations/representations (e.g. `plotting_ordered_pairs -> vector_addition -> algebraic_equation_scaling`) -- procedurally dependent, closer in shape to the Physics graph than to Reading's skill graph.
* **Self-RAG / CRAG grounding target:** retrieved worked solutions must be independently re-derivable -- the Critic's "mathematical precision" check (already named in Section 2.1.3) means literally re-computing the Worker's stated answer via a symbolic/numeric check (e.g. `sympy`), not a text-similarity plausibility check the way Reading's would be.
* **Worked example:** a student plots point (3, 4) and is asked for the vector to (7, 1). Worker computes `(7-3, 1-4) = (4, -3)`. Critic independently recomputes the subtraction rather than trusting the Worker's stated result -- this is the one domain where the Critic can be a **deterministic checker**, not just an LLM judgment call, and should be built that way for cost and reliability reasons.

**Why this matters for MVP scope:** Reading and Math each require their
own GraphRAG Lite prerequisite graph and their own domain-specific Critic
grounding checks -- these are not drop-in reuses of the Physics
implementation. Section 9 (Milestones) still only schedules a Physics
build in the 4-week window; treat Reading and Math as sequential
follow-on builds using this section as their spec, not as parallel Week-1
work for a 6-person team already scoped tightly around one domain.

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

### 6.1. Voice Audio Input/Output Sync Pipeline
Utilizes native Web Audio API wrappers to handle voice ingestion and speech playbacks. Transcribes vocal waveforms into text strings for the Router Agent, and prompt-tunes server text-to-speech rendering outputs to map matching cadences for specific persona types.

### 6.2. Generative Vector Canvas Renderer
The presentation client acts as an interactive vector art consumer. It parses incoming layout data coordinates (x, y, vector arrows) and paints them directly inside an inline HTML SVG viewport canvas using hardware-accelerated matrix transformations.

---

## 7. Teacher Dashboard & Classroom Management

Section 2.1.4 already grants MCP tools permission to read "teacher-uploaded
curriculum documentation" and sync "student Learning Management System
(LMS) rosters" -- implying teachers are part of this system -- but no
prior version of this document designed any teacher-facing surface, any
student-to-teacher linkage mechanism, or any access model. This section
closes that gap.

### 7.1. How a student joins a teacher's classroom
A student does not pick a teacher from a list; they enter a **class code**
a teacher generates and shares (the same mental model as Google Classroom
or Kahoot), at onboarding, before session creation:

1. Teacher creates a class in the Teacher Dashboard (7.2), receiving a
   short alphanumeric `class_code` (e.g. `FRC-9K2`).
2. Student enters `class_code` on the onboarding screen, alongside the
   existing profile fields (Section 3.1's telemetry inputs).
3. The Router Agent resolves `class_code` to a `teacher_id` via the LMS
   roster sync MCP tool (already permitted, Section 2.1.4) and, if the
   teacher has uploaded curriculum overrides for that class, the Teaching
   Agent's content-lookup path (GraphRAG Lite / MCP content retrieval)
   prefers the teacher's uploaded material over the platform default
   library for any concept the teacher has overridden.
4. If no `class_code` is entered, the student proceeds on the platform
   default curriculum with no teacher attached -- this must remain a valid
   path (not every student has a teacher account set up yet), and no
   progress data is exposed to any teacher dashboard in that case.

**AgentState addition:**
```python
class_code: Optional[str] = Field(None, description="Links this session to a teacher's roster; None if unattached.")
```

### 7.2. Teacher Dashboard surface
A teacher-facing web view (separate route/app from the student Renderer
Client Layer, Section 2.1.6), gated by its own authentication (see Section
11 -- authentication itself is *not* designed in this revision, only the
data model and access rule that depend on it existing). Three views:

* **Roster view:** every student whose session `class_code` matches this
  teacher's class(es). Per student: name, grade band, last-active
  timestamp, current XP (`score_xp`, Section 3.1), and a mastery indicator
  per concept the class has covered.
* **Per-student progress + feedback view:** the same
  `attempt_history`/`evaluation_feedback` fields already in AgentState
  (Section 3.1), rendered as a timeline, plus every Negative Reinforcement
  Constraint Token the Auditor Agent (Section 4.1) has written for that
  student (Section 5.1) -- this exposes data the system already collects,
  not new data collection, which keeps this addition cheap.
* **Class-aggregate view:** which concepts most commonly trigger the
  Auditor Agent across the whole roster -- a concept with a
  disproportionate Negative-Reinforcement-Token rate across many students
  is a signal the *content* is broken (a bad analogy, an ambiguous
  question), not that many students independently struggled, and should
  be surfaced to the teacher as a content-quality flag, not buried in
  individual student views.

### 7.3. Access scoping (functional requirement, not a full privacy policy)
A teacher's dashboard queries are scoped to `class_code`s they created --
enforced at the MCP/storage boundary (Section 2.1.5), not just hidden in
the UI, so a teacher account cannot enumerate another teacher's roster by
guessing IDs. This is a necessary *access-control* rule, distinct from
(and narrower than) full student-data privacy/compliance, which Section 11
flags as still entirely unaddressed.

### 7.4. Scope note
This section is a design addition, not a Week 1-4 deliverable -- the
existing 6-person/4-week matrix (Section 9) has no team member allocated
to building a second, teacher-facing application surface on top of an
already-tight physics-only MVP. Treat this as the immediate next phase
after the student-facing MVP ships, not as work to compress into the
current timeline.

---

## 8. Capstone Optimization, Post-Training, & Evaluation Loops

To satisfy the core academic criteria of the Capstone project, the system implements two advanced optimization workflows: programmatic few-shot prompt compilation (DSPy) and parameter-level alignment optimization (GRPO & RLVR).

### 8.1. DSPy Prompt Compilation Workflow
Manual prompt engineering in the `teaching_agent` and `evaluator_agent` is entirely replaced with declarative **DSPy Signatures** and **Modules**.
* **Prompt Signatures:** Defined as class boundaries capturing inputs, reasoning paths, and target output schemas.
* **The Compilation Loop:** In Week 3, Member 2 and Member 5 compile these signatures using `dspy.teleprompt.BootstrapFewShot` or `MIPROv2`.
* **Dataset & Validation:** The optimization runs against a localized validation corpus of 50 student query-response pairs.
* **Measurement:** The project will measure and report the exact performance delta (win rate/accuracy) comparing the compiled DSPy output against handwritten baseline prompts.

### 8.2. GRPO & RLVR Post-Training Pipeline
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

### 8.3. Stub/Mock Unit Testing Loops
A localized scenario simulation testing suite is built inside `tests/` using `pytest-mock` to guarantee the entire multi-agent orchestration tree can run in isolation.
* **Stub Class Models:** All Gemini API targets, network voice gateways, and database reads are simulated with predefined mock responses.
* **Offline Scenario Testing:** This allows developers to run complete mock classroom scenario loops, verifying state transitions and Edge routing conditions instantly without executing real model requests.

### 8.4. Pedagogical Efficacy Validation (Learning Outcome Measurement)
**This is the highest-priority gap identified in review of the original
draft, and the one most specific to this being an *education* product
rather than a generic agentic application.** Sections 8.1-8.3 measure
whether the AI's *output* is good -- DSPy's win-rate delta against a
hand-written baseline, GRPO's reward function, mock scenario-loop
coverage. None of them measure whether a student who used this system
*learned more* than one who didn't. Passing the Mastery Learning Engine's
80% threshold (Section 1.2) on one task, once, is not evidence of learning
-- it's evidence of momentary task completion, which decays without
retrieval practice over time.

**1. Pre/Post Delta per Concept.** Before a student's first exposure to a
concept, the Assessment Agent administers one cold, ungraded diagnostic
item for that concept (no hint, no scaffold) and logs the score. After the
student reaches the Mastery Learning threshold on that concept, the same
(or an isomorphic, randomized-value) diagnostic item is re-administered.
The delta between cold-start and post-mastery score is the actual learning
signal -- not the 80% threshold itself, which only measures the end state.

**2. Retention Check (Spaced Re-Assessment).** 7-14 days after a student
reaches Mastery on a concept, the Assessment Agent silently re-inserts one
diagnostic item for that concept into a later session, without warning or
review beforehand. A student who scores well on the *immediate* post-test
but poorly on the *retention* check indicates the system produced
short-term task completion, not durable learning -- a case the prior draft
had no way to detect at all. Log this as a `retention_score` per (student,
concept, days_elapsed) tuple; extend `attempt_history` (Section 3.1) or
add a parallel `retention_history: Dict[str, List[RetentionCheck]]` field
to AgentState.

**3. Adaptive-vs-Control Comparison.** To claim the *adaptivity itself*
(not just "an AI tutor" generically) improves outcomes, a subset of
sessions should run a control path: same content library, same diagnostic
items, but Softmax Temperature Scaling and the Adaptive Hint Ladder
(Section 4.2) disabled -- fixed grade-band-default temperature and a
single non-adaptive hint per task instead. Comparing pre/post delta and
retention scores between the adaptive and control groups is the only
design in this document that can actually support the claim "adaptive
instruction works better than static," which the Executive Summary
(Section 1.1) implicitly claims without a way to test it.

**4. What this does NOT solve.** This section defines a *measurement*
design, not a guarantee of efficacy -- it will not tell you the platform
teaches well, only whether it's possible to find out. A real pilot (a
small number of actual classrooms, IRB/school-district approval if data is
used for any research claim, and enough students for the adaptive-vs-control
comparison to be statistically meaningful) is out of scope for a 4-week,
6-person capstone MVP and should be treated as a distinct, later
initiative -- see Section 11.

---

## 9. 4-Week MVP Milestones & Work Distribution

### 9.1. 6-Member Project Master Matrix

| Week | Member 1: Orchestrator | Member 2: Teaching Agent | Member 3: Presentation UI | Member 4: Voice I/O | Member 5: Evaluator Agent | Member 6: Data MCP Server |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Week 1** | FastAPI wrapper setup; configure Arize Phoenix tracers. | Model curriculum schema template definitions. | Code webpage outer container using placeholder SVGs. | Build microphone signal capture scripts. | Configure base OpenTelemetry span metrics tracking rules. | Initialize SQLite database schemas via SQLAlchemy ORM. |
| **Week 2** | Code central LangGraph routing state graphs. | Define DSPy Signatures for the Teaching Agent nodes. | Update client JS code to parse raw server JSON layout streams. | Integrate speech-to-text translation pipelines. | Connect evaluation signatures to active LangSmith dashboards. | Embed documents in Qdrant; expose tools via FastMCP. |
| **Week 3** | Implement backend RL Reward calculations. | Execute DSPy compilation loop using localized datasets. | Refactor visual viewports for dynamic SVG canvas generation. | Connect text-to-speech voice streams to Web Audio API. | Orchestrate local GRPO/RLVR small model fine-tuning loops. | Build database analytics tables inside SQLite to track rewards. |
| **Week 4** | Convert routes to persistent local WebSockets. | Run final prompt regression tests to prevent validation failures. | Link WebSocket events to dynamic vector visual animations. | Hook voice toggles directly over persistent communication lines. | Execute final validation sweeps across post-trained models. | Establish optimization database indexing on SQLite columns. |

### 9.2. Weekly Evolutionary Deliverables & Demo Protocols
* **Week 1 Demo (Foundations & Tracing):** Complete registration on the webpage. Data writes down to the SQLite database. Open Arize Phoenix to show OpenTelemetry tracking database spans.
* **Week 2 Demo (AI Agents & Knowledge):** Client layout copy parameters turn fluid, displaying narrative sequences, text strings, and quizzes dynamically generated by Gemini via LangGraph and FastMCP. Traces are logged in LangSmith.
* **Week 3 Demo (RL and Generative Art):** Choose Pikachu during onboarding. Client UI dynamically draws inline SVG Pikachu vectors. Intentionally click off the tab—the backend logs focus loss, and the DSPy-optimized engine automatically simplifies language on the next slide.
* **Week 4 Demo (Connected System Ecosystem):** Complete sandbox workspace running live over WebSockets. Speak into the microphone; audio transcribes, evaluates via post-trained small model, updates score parameters in SQLite, and fires a particle explosion animation on the frontend.

---

## 10. Future Production Scaling: AWS Serverless Mapping

Because the architecture standardizes on clean JSON-in/JSON-out primitive structures passing through local uv repositories, the codebase translates perfectly into cloud equivalents later:
* **FastAPI Backend Router** -> Amazon API Gateway + AWS Lambda Functions
* **SQLite Storage Layer** -> Amazon Aurora Serverless (PostgreSQL Connection String override)
* **LangGraph Agent Vertices** -> Isolated AWS Lambda Functions running the Google GenAI SDK
* **Qdrant Vector Engine** -> Hosted Qdrant Cloud Serverless endpoints
* **Presentation HTML UI Client** -> Simple Amazon S3 Bucket paired with Amazon CloudFront distribution channels.

---

## 11. Known Shortcomings & Future Work

An honest accounting of what this specification still does not address,
identified during a gap-analysis review and deliberately left unresolved
in this revision -- either because fixing them requires product/legal
decisions this document can't make unilaterally, or because they are real,
larger efforts than "add a section":

* **Child data privacy & compliance (COPPA, FERPA, parental consent).**
  This platform explicitly serves Kindergarten-through-college users and
  collects affective-state telemetry (stress, tiredness, motivation) and
  behavioral telemetry (click latency, tab-focus loss) on minors. Zero
  privacy, consent, retention, or compliance design exists anywhere in
  this document, including Section 7 (Teacher Dashboard), which only
  specifies access *scoping* between teachers (7.3), not the underlying
  legal basis for collecting or retaining this data on children in the
  first place. This is the single largest blocker to any real classroom
  deployment and should be the next thing designed -- ahead of anything
  else in this list.

* **Student-input safety escalation.** The Policy Engine (Section 4.1)
  screens *generated* content for age-appropriateness. Nothing screens
  *student* input for signs of distress, self-harm, abuse, or bullying
  disclosure, despite the system already tracking a `stress` score. No
  escalation path to a human (teacher, counselor) exists.

* **Authentication.** Section 7's Teacher Dashboard assumes teacher
  accounts and login exist; this document does not design them. Student
  session identity (`user_id`, Section 3.1) also has no authentication
  model -- anyone with a `session_id` can currently act as that student.

* **Cost and latency budget.** A single student turn can traverse Router
  -> Policy -> Self-RAG -> CRAG (conditional) -> GraphRAG Lite -> Worker ->
  Critic -> Auditor (conditional) -- up to eight model-touching hops. No
  target latency (a K-2 student will not wait indefinitely for a hint) or
  per-student cost ceiling is defined anywhere in this document.

* **MVP concurrency ceiling.** Section 2.1.5 specifies SQLite for the MVP
  storage layer; SQLite's single-writer model means the 4-week MVP itself,
  not just a hypothetical future scale, cannot reliably serve more than
  one active student session at a time. Section 10 (AWS Scaling) describes
  a later swap to Aurora Serverless but no bridge plan for testing with
  more than one concurrent user before that migration happens.

* **Accessibility and multi-language / ELL support.** Not addressed for a
  platform serving the full K-12 population, where both are standard
  requirements, not edge cases -- particularly relevant given English
  Reading (Section 4.3) is one of the three core subject domains and
  therefore inherently assumes English-language literacy.

* **Model lifecycle & versioning.** Once a DSPy program is compiled
  (Section 8.1) or a GRPO checkpoint is fine-tuned (Section 8.2), no
  process exists for versioning, rolling back, or re-validating that
  artifact as the content library or grade-band coverage grows. A
  "successful" optimization run today has no guardrail against silently
  regressing a domain nobody re-tested.

* **Human-in-the-loop content review.** Section 7's Teacher Dashboard is
  read-only in this revision (view progress and feedback). It does not
  let a teacher review or override AI-generated content before a student
  sees it, or flag bad output for correction -- likely necessary for any
  early real-classroom pilot, not just a nice-to-have.
