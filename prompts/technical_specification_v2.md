# Technical Specification v2 — Modular 3-Agent MVP

**Supersedes:** `technical_specification.md` (v1 — single-file HTML app, monolithic content). This document defines the MVP architecture that splits v1's implicit "one HTML file does everything" design into three independently-specified agents plus a shared UI contract, so lesson/quiz content can be extended without touching orchestration code, and orchestration can be extended without touching content generation.
**Scope:** UI structure, agent responsibilities, data contracts, default content. Logging, persistence, auth, and backend storage remain explicitly out of scope, per the original request.

---

## 1. Why Split Into Three Agents

The v1 spec's biggest flagged gap (§11.2–11.3 of the v1 doc) was that lesson content was hardcoded into the same file as onboarding/navigation logic, so picking a different interest or quest node didn't actually change anything. Splitting the system into Root / Teaching / Assessment agents fixes this structurally, not just by adding more hardcoded branches:

| Concern | v1 (monolith) | v2 (modular) |
|---|---|---|
| Onboarding, screen routing, safety valves, breaks, admin | mixed into the same script as lesson content | **Root Agent** — owns this exclusively |
| Lesson generation (any subject/topic) | one hardcoded Newton's 3rd Law lesson | **Teaching Agent** — generic algorithm + swappable default content library |
| Quiz/checkpoint generation | one hardcoded diagnostic per lesson | **Assessment Agent** — reusable across lessons, subjects, and review cycles |
| Rendering format | ad hoc `innerHTML` templates per screen | **Shared UI contract** (`ui_prompt.md`) — every agent emits the same schema |

---

## 2. Architecture Overview

```
                     ┌────────────────────┐
   Student  ───────► │     Root Agent      │ ◄─── Teacher (admin/dashboard)
   (browser UI)       │ (root_agent_prompt) │
                     └─────────┬───────────┘
                        owns session state
                        runs critic gate
                        renders via ui_prompt.md
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
        generate_lesson(ctx)         generate_assessment(ctx)
                 │                           │
                 ▼                           ▼
     ┌─────────────────────┐      ┌───────────────────────┐
     │   Teaching Agent      │      │   Assessment Agent      │
     │ (teaching_agent_prompt)│      │ (assessment_agent_prompt)│
     │ - checks default lib   │      │ - grade-scaled quiz gen  │
     │ - else generates fresh │      │ - mistake genome map      │
     └──────────┬──────────┘      └───────────────────────┘
                │
     ┌──────────▼──────────────┐
     │ newtons_laws_lesson_library.md│  (demo default content, 12 records)
     └──────────────────────────┘
```

Both sub-agents are **stateless, synchronous, single-purpose**: they receive full context on every call and return a complete `LessonScreen` or `QuizItem[]` — no session memory, no follow-up questions to the student. This keeps them swappable/independently testable and is what "modular" means concretely here: you can replace the Teaching Agent's generation logic (e.g., swap in a different model or a human-curated CMS) without the Root Agent or Assessment Agent changing at all, because the contract (`ui_prompt.md`) is the only thing they share.

---

## 3. File Manifest

| File | Owns | Consumed by |
|---|---|---|
| `root_agent_prompt.md` | Orchestration, onboarding, session state, admin, safety escalation, critic gate | — |
| `ui_prompt.md` | Shared rendering schema (screen envelope, component library, `LessonScreen`, `QuizItem`) | Root, Teaching, Assessment |
| `teaching_agent_prompt.md` | Lesson generation logic, `ConceptDefinition` schema, lesson-plan override, image use, subject extensibility | Root (calls it) |
| `assessment_agent_prompt.md` | Quiz/assessment generation logic, difficulty scaling, mistake-genome mapping | Root (calls it) |
| `newtons_laws_lesson_library.md` | Default, pre-authored content — **12 lesson records for this demo** (physics, Newton's 3 Laws, 2 grade bands `grade5`/`high`, 2 themes `soccer`/`creative_play`) | Teaching Agent |
| `system_prompt.md` (v1, legacy) | Original monolithic tone/guardrail spec — still authoritative for voice and non-negotiable rules; all three v2 prompts are scoped subsets/extensions of it | Root, Teaching, Assessment (by reference) |
| `demo_screens_prompt.md` | Reusable prompt used to originally author the full 18-record content set (3 themes); also doubles as the spec for the Teaching Agent's §4 generation algorithm when producing *new* content beyond Newton's Laws | Content authors / Teaching Agent's internal process |
| `newtons_laws_demo_screens.md` | Prose archive of all 18 originally-authored records, including the 6 `anime_stories` ones dropped from this demo's active library — source to restore full theme coverage later | Content authors (reference only) |
| `adaptive_learning_avatar_demo_v3.html` | The rendering shell (unchanged CSS/animation tokens; JS state machine to be refactored per §4 below) | End user |

---

## 4. Refactor Plan for the HTML Shell

The existing `adaptive_learning_avatar_demo_v3.html` remains the rendering shell but its JS needs four structural changes to become "the Root Agent's renderer" rather than a monolith. **For this demo build, onboarding is also intentionally narrowed to only the covered combinations** so no path dead-ends into missing content:

1. **Extract `copyByAge` and `getFormalConcept()`.** Replace with a call into the content resolution described in `teaching_agent_prompt.md` §3 — on entering `lesson`, look up `(subject, topic, concept, gradeBand, theme)` in `newtons_laws_lesson_library.md`'s 12 demo records first; if no match, this is where a live Teaching Agent call would go (demo can stub this as "content not available yet" per Root Agent §5).
2. **Narrow `renderGrade()` to 2 options for the demo:** `5th–6th Grade 🌟 → gradeBand: "grade5"` and `High School+ 🎓 → gradeBand: "high"`. Drop the `3rd–4th Grade` and `Middle School` chips from the demo build (they remain valid in the general `system_prompt.md`/`root_agent_prompt.md` taxonomy — this is a demo-scope UI cut, not a spec change).
3. **Narrow `renderInterest()` to 2 options for the demo:** `Sports ⚽ → theme: "soccer"` and a **new `Creative Play 👗 → theme: "creative_play"` chip** replacing `Gaming`/`Anime-Stories`/`Science-Building` in this build (those three remain valid options in the full taxonomy — see `teaching_agent_prompt.md` §6 — just not populated with content for this demo, so they're hidden rather than left as dead ends).
4. **Wire `quest` nodes to real `subjectContext`.** `Force Lab 🧪` → `{subject: physics, topic: newtons_laws_of_motion, concept: <cycles through law_1/2/3>}`; the other three nodes (`Fractions Forest`, `Memory Cave`, `Writing Workshop`) should render `Locked`/`Coming soon` for this demo, rather than silently opening the Force Lab content (fixes v1 §11.3).

The chair-push animation (`#chairScene`, `.student-rig`, etc.) becomes the concrete implementation of the `force_pair_rig_scene` referenced in `ui_prompt.md` §3.2 — it is already theme-agnostic (abstract rigs, swappable caption text) and needs no rework, only a rename/generalization in code comments. Two new, similarly lightweight scene modules are needed for Law 1 and Law 2 (`rolling_object_scene`, `push_strength_scene`) — see `technical_specification.md` (v1) §6.3 for their behavior spec; that section is unchanged by this refactor.

---

## 5. Content Coverage at Demo Launch

| Subject | Topic | Grade bands | Themes | Concepts | Source |
|---|---|---|---|---|---|
| Physics | Newton's Three Laws of Motion | `grade5` (5th grade), `high` | Soccer, Creative Play (Barbie) | Law 1 (Inertia), Law 2 (F=ma), Law 3 (Action-Reaction) | `newtons_laws_lesson_library.md`, 12 pre-authored records |

This is a deliberate cut-down from the fuller 18-combination set (2 grades × 3 themes × 3 laws, which also included `Anime/Stories` and the `elementary`/3rd-grade register). Those 6 additional records already exist in `newtons_laws_demo_screens.md` and can be reintroduced by appending them to the JSON array in `newtons_laws_lesson_library.md` — no change to the Teaching Agent, Root Agent, or UI contract is required to widen coverage back up later.

Everything outside the demo's 12-record table (middle-school register, other subjects, other themes) is **not pre-authored** — it falls through to the Teaching Agent's default generation algorithm (`teaching_agent_prompt.md` §4), which is included in this spec precisely so the system doesn't break when a student picks an uncovered combination; it degrades to live generation rather than failing. For the demo build specifically, the onboarding UI is narrowed (§4 above) so students can't actually reach an uncovered combination in the first place.

Academic content correctness is guaranteed the same way across both pre-authored and generated content: every record — authored or generated — must trace back to a `ConceptDefinition` (`teaching_agent_prompt.md` §2.1) whose `formal_statement` doesn't change between grade bands or themes. The three physics `ConceptDefinition`s used for the demo's 12-record library are listed at the top of `newtons_laws_lesson_library.md`.

---

## 6. Interest-Tag & Grade-Tag Resolution (Demo Scope)

| App interest chip (demo) | Content theme | Coverage |
|---|---|---|
| Sports ⚽ | `soccer` | Full (6 records: 2 grades × 3 laws) |
| Creative Play 👗 *(new chip, required for demo)* | `creative_play` | Full (6 records) |

`Gaming 🎮`, `Anime/Stories 🦸`, and `Science/Building 🧪` are **hidden from the onboarding UI in this demo build** rather than left as fallback dead ends — they remain valid in the full taxonomy (`teaching_agent_prompt.md` §6) and can be re-enabled with their original fallback behavior (Gaming → `anime_stories` copy, Science/Building → `soccer` copy) whenever the 18-combination library is restored.

| App grade chip (demo) | Content `gradeBand` | Coverage |
|---|---|---|
| 5th–6th Grade 🌟 | `grade5` | Full (6 records: 2 themes × 3 laws) |
| High School+ 🎓 | `high` | Full (6 records) |

`3rd–4th Grade 🎒` and `Middle School 🚀` chips are hidden from the demo's onboarding UI for the same reason. Note `grade5` here is a **content-library register key**, distinct from the Root Agent's broader `ageBand` onboarding category (`elementary`) — the demo's "5th–6th Grade" chip should set both `profile.ageBand: "elementary"` (for Root Agent tone/density logic, unchanged) and `subjectContext.gradeBand: "grade5"` (for library lookup).

Adding the `Creative Play` chip and narrowing both option grids to 2 entries each is a small, contained change to `renderGrade()` and `renderInterest()`'s option grids in the HTML shell — flagged here as the concrete demo-scope UI change.

---

## 7. Images — Demo Scope

No image-generation tool is wired into the demo. Every lesson record in `newtons_laws_lesson_library.md` still carries `image_prompt` + `image_alt` per `teaching_agent_prompt.md` §5, so:
- The schema is future-proof — plugging in an image tool later requires no content rewrite, only a renderer change to fetch/display `image_prompt` results.
- Accessibility is not regressed in the meantime — `image_alt` text can be used today as supplementary descriptive copy under the CSS/emoji scene, even with no actual image rendered.

---

## 8. Build Plan (Demo Milestones)

1. **M1 — Contract freeze.** Finalize `ui_prompt.md` schemas (envelope, `LessonScreen`, `QuizItem`) — everything else depends on these not changing shape mid-build.
2. **M2 — Root Agent refactor.** Extract onboarding/navigation/admin logic per §4 above; stub Teaching/Assessment calls to return static JSON from the two library files (no live generation yet).
3. **M3 — Content wiring.** Narrow `renderGrade()`/`renderInterest()` to the 2×2 demo option set (§6), wire quest nodes to real `subjectContext`, swap `copyByAge`/`getFormalConcept()` for library lookups against the 12-record file.
4. **M4 — Scene generalization.** Build `rolling_object_scene` and `push_strength_scene` (Law 1/2 visuals) alongside the existing Law 3 chair-push rig; confirm all 12 demo records render correctly end to end.
5. **M5 — Assessment Agent wiring.** Add a standalone checkpoint call after the `Force Lab` boss-fight node, using `assessment_agent_prompt.md`'s contract against the same 3 `ConceptDefinition`s.
6. **M6 — Guardrail pass.** Run the Critic Checklist (v1 spec §13, still valid) against all 12 rendered demo lessons; fix the backend-signals-visible-to-student deviation (v1 §11.1) by hiding the debug sidebar behind a `?mode=teacher` flag.
7. **M7 (stretch, post-demo) — Widen coverage.** Re-add the 6 `anime_stories`/elementary records already authored in `newtons_laws_demo_screens.md`, and/or smoke-test the Teaching Agent's §4 generation algorithm against one uncovered combination (e.g., `middle` grade band) to confirm live generation works before the demo scope expands.

---

## 9. Acceptance Criteria

- All 12 demo lesson records render through the same shell code path (no per-record special casing).
- Selecting each of the 2 interest chips and each of the 2 grade chips changes the lesson content shown for `Force Lab`, verified against §6's resolution table.
- Every rendered diagnostic's incorrect options map to a real entry in the corresponding record's `mistake_genome`.
- No screen (in the Root, Teaching, or Assessment output) shows more than one primary interactive component, per `ui_prompt.md` §5.
- Teacher Dashboard (`renderDashboard`) correctly labels each shown lesson `generated: false` (from library) vs. `true` (live-generated), once M7 is implemented.
- Removing/renaming a record in `newtons_laws_lesson_library.md`, or widening the demo back to 18 records, does not require any change to `root_agent_prompt.md` or `ui_prompt.md` — proves the modularity goal.

---

## 10. Carried-Forward Gaps (from v1, still open)

- Reduced-motion toggle doesn't yet suppress the timed sandbox-scene animation sequence (v1 §10).
- No `aria-live` region announces screen transitions to assistive tech (v1 §10).
- Self-harm/safety escalation path (Root Agent §7) is specified but not yet implemented/tested in the HTML shell.
- "Try again 🔄" on `validate` vs. "Restart Demo" in the topbar still have inconsistent reset scope (v1 §11.5) — needs a product decision, not just an engineering fix.
