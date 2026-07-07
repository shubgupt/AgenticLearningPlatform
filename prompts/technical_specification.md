# Technical Specification — Adaptive Learning Avatar Demo (v3 HTML App)

**Source file:** `adaptive_learning_avatar_demo_v3.html`
**Governing behavior spec:** `system_prompt.md` (Adaptive Gamified Learning UI Orchestration Agent)
**Content source:** `demo_screens_prompt.md` output — 18 Newton's Laws scenarios (see §6)
**Scope:** UI structure, state model, screen logic, content data model, and guardrails only. Logging, persistence, auth, and backend storage are explicitly out of scope (see §12).

---

## 1. Purpose

This is a single-file, dependency-free HTML/CSS/JS application that demonstrates the adaptive, gamified learning UI described in `system_prompt.md`. It simulates one full session: energy check → avatar build → interest selection → learning-style recipe → quest map → an interactive physics lesson (Newton's Third Law, skateboard/chair push-off) → a diagnostic check with mistake-genome branching → student profile validation → a teacher-facing dashboard.

The spec below documents the app **as built**, then specifies how it should be extended so that the lesson content is data-driven across grade band × interest theme × law, using the 18 scenarios already authored, instead of the single hardcoded Newton's Third Law example currently in `copyByAge`.

---

## 2. Compliance Mapping to `system_prompt.md`

| System prompt principle | Where implemented in the app | Status |
|---|---|---|
| Academic Invariance (concept never watered down) | `getFormalConcept()`, `copyByAge` — same F(A→B) = −F(B→A) idea stated at 3 rigor levels | Implemented for Law 3 only; must extend to Laws 1–2 (§6) |
| Pedagogical Funnel (hook → discovery → concept → diagnostic → mistake trace → validate) | Screen order: `energy → grade → interest → recipe → quest → lesson → check → validate → dashboard` | Implemented |
| Anti-Fatigue Rule | `setLowDensity()`, `body.low-density` CSS, "Sleeping Potato"/"Low Battery" energy branches | Implemented |
| Blended Learning, not fixed labels | `learningStyleMix` object with weighted keys, never a single "you are an X learner" label | Implemented |
| Student-Owned Profile | `renderValidate()`, `renderPatchMenu()` | Implemented |
| Mistake Genome (diagnostic, not shaming) | `renderCheck()` → `renderMistake()`, `state.mistakeGenome[]` | Implemented for one checkpoint |
| Hint Ladder | "Give me a hint 💡" / "Tiny hint 💡" chain in lesson and mistake screens | Partially implemented (2 levels, not full 7-level ladder) |
| Break & Recovery Mode | `openBreak()`, `startBreak()`, `renderAfterBreak()`, break overlay modal | Implemented |
| Mini-Game Layer (optional, skippable, non-shaming) | `renderMiniGame()`, gated by `state.gamePositive \|\| state.interest === "gaming"` | Implemented |
| Teacher Dashboard (cautious language, no diagnostic labels) | `renderDashboard()` | Implemented, uses neutral phrasing |
| Hidden backend labels | `state.signals` object is shown in a JSON debug panel for demo purposes only | **Deviation** — see §11 |
| Persistent Safety Valves | `.safety-valves` bar, always visible, wired to `renderBored/renderTooMuchReading/renderSurprise/openBreak` | Implemented |
| Accessibility | `Reduce Motion` toggle, large tap targets (`--tap: 52–62px`) | Partial — see §10 |
| Privacy (no PII collection) | No form fields anywhere collect name/email/DOB/etc. | Implemented |

---

## 3. Architecture

- **Format:** single static HTML file, inline `<style>` and `<script>`. No build step, no external runtime dependencies (system font stack only; no CDN calls).
- **Pattern:** finite-state screen machine. `state.screen` holds the current screen id; `render()` dispatches to one of nine render functions via a lookup table (`renderers`).
- **Rendering:** each `render*()` function does a full `innerHTML` replace of `#screenRoot` (or reuses `mainCard()` helper), then calls `bindOptions()` to attach click handlers to freshly created `[data-action]` buttons. There is no virtual DOM / diffing — this is acceptable at this screen count and interaction complexity.
- **Sidebars:** `updateSidebars()` runs after every `render()` and repaints two persistent panels — "Learning Avatar Snapshot" (chips) and "Internal State Preview" (raw JSON) — from the live `state` object.
- **Modal:** the Break overlay (`#breakOverlay`) is a fixed-position layer outside the normal screen flow, toggled by class `.active`; it owns its own countdown timer (`timerInterval`) independent of the screen state machine.
- **No routing/URL state:** screen changes do not update the address bar; a full page reload always returns to `energy`.

### 3.1 Screen graph

```
energy → grade → interest → recipe → quest → lesson → check → validate → dashboard
                                         ↑        ↓
                                    (mistake) → check (retry loop)
                                         ↓
                                   mini-game → check
safety valves (bored/reading/surprise/break) are reachable from ANY screen
  and return to `quest` (bored/surprise/reading) or resume in place (break)
```

---

## 4. Global State Model

`state` (in-memory JS object, no persistence) — current shape and intended use:

| Field | Type | Set by | Consumed by |
|---|---|---|---|
| `screen` | string enum (9 values) | `setScreen()` | `render()` |
| `xp` | integer | `addXP()` | avatar stats panel, reward lines |
| `lowDensity` | boolean | `setLowDensity()` | `body.low-density` class, copy branching |
| `reducedMotion` | boolean | motion toggle | `body.reduced-motion` class (disables orb float) |
| `ageBand` | `"elementary"\|"middle"\|"high"\|"unknown"` | `renderGrade()` | `copyByAge`, `getFormalConcept()` |
| `energy` | free string (`"sleeping potato"`, `"low battery"`, `"steady"`, `"rocket"`) | `renderEnergy()` | dashboard confidence_signal, low-density trigger |
| `interest` | `"gaming"\|"sports"\|"stories"\|"science/building"\|"unknown"` | `renderInterest()` | mini-game gating; **not yet used for lesson content (§6 gap)** |
| `learningStyleMix` | object of weighted keys (0–1 floats) | `renderRecipe()` | shown in JSON panel; not yet used to alter lesson layout |
| `preferredBlend` | string[] | `renderRecipe()` | validate screen summary, dashboard |
| `subject` | string, currently always `"Physics"` | `renderQuest()` | dashboard/lesson labeling |
| `currentConcept` | string, currently always `"Newton's Third Law"` | `renderQuest()` | dashboard/lesson labeling |
| `fatigue` | `"high"\|"medium"\|"low"\|"unknown"` | `renderEnergy()` | not currently read anywhere downstream — reserved |
| `gamePositive` | boolean | `renderEnergy()`/`renderInterest()` | mini-game gate in `renderLesson()` |
| `profileConfidence` | float 0–1 | `updateProfile()` (+0.08 per call, capped 0.92), set to 0.85 on validation accept | dashboard, sidebar |
| `mistakeGenome` | array of trace objects | `renderCheck()` | dashboard `mistake_patterns` |
| `signals` | object, 11 named internal learner signals (attentionSpan, confusionSensitivity, revisionNeed, timeManagement, selfConfidence, processingPace, motivationDrivers[], chitchatTendency, distractionRisk, fatigueAndBreakNeeds, gameEngagementPreference) | various valve/energy/mini-game handlers | dashboard snapshot; **currently also shown in student-facing JSON panel — should be teacher-only (§11)** |

`updateProfile(patch)` is the single mutation entry point for profile fields; it merges a patch object and bumps `profileConfidence`. All screen handlers should continue routing state changes through it rather than mutating `state` directly, to keep confidence scoring consistent.

---

## 5. Screen-by-Screen Specification

Each entry lists: purpose, UI components, options and their state effects, XP reward, and the guardrail(s) it must satisfy per `system_prompt.md`.

### 5.1 `energy` — Welcome / Energy Check
- **Purpose:** first-touch mood/energy detection; sets reading density for the rest of the session.
- **Components:** avatar orb (booting), 4-option grid (`mainCard`), persistent safety valves.
- **Options → effects:** Sleeping Potato (fatigue=high, low-density on) · Low Battery (fatigue=medium, low-density on) · Steady Mode (fatigue=low, normal density) · Rocket Mode (fatigue=low, `gamePositive=true`).
- **XP:** +50 flat.
- **Guardrails:** exactly one primary question; no PII requested; tone matches "Sleeping Potato 🥔" style from system prompt verbatim.

### 5.2 `grade` — Age-Band Calibration
- **Purpose:** sets `ageBand`, which drives vocabulary/rigor everywhere downstream.
- **Components:** 4-option grid, each option labeled with its scaffold style as `<small>` subtext.
- **Options → effects:** all four map into 3 internal bands (`elementary`, `elementary`, `middle`, `high`) — 3rd–4th and 5th–6th both collapse to `elementary` today.
- **XP:** +75 flat.
- **Guardrails:** age-appropriate language per band; no exact birthday/grade-as-PII collected, only a band.

### 5.3 `interest` — Power Source / Theme Selection
- **Purpose:** sets `interest`, intended to drive which content pack (theme) is used in `lesson`.
- **Components:** 4-option grid — Gaming 🎮, Sports ⚽, Anime/Stories 🦸, Science/Building 🧪.
- **Options → effects:** sets `interest`; pushes into `signals.motivationDrivers`; Gaming also sets `gamePositive=true`.
- **XP:** +75 flat.
- **Guardrails / gap:** per system prompt §"Blended Learning Style Rule" and the demo-screens content brief, theme should be **gender-neutral by design where possible** and should visibly change lesson content, not just flavor text. See §6/§11 for the required content-selection wiring and the Barbie/Creative-Play theme gap.

### 5.4 `recipe` — Learning Recipe Mixer
- **Purpose:** captures blended learning style as weighted mix, never a single label.
- **Components:** 4-option grid (Visual+Steps, Story+Example, Practice+Hints, Chill+Recap).
- **Options → effects:** sets `preferredBlend` (array) and `learningStyleMix` (weighted object); Chill+Recap also forces low density.
- **XP:** +100 flat.
- **Guardrails:** satisfies "never force a single learning-style label" — confirmed compliant.

### 5.5 `quest` — Quest Map
- **Purpose:** curriculum as an explorable map, not a linear question list.
- **Components:** 4 quest nodes (`Fractions Forest`, `Force Lab`, `Memory Cave`, `Writing Workshop`), each with a status dot and two-line status/description.
- **Options → effects:** any node click currently routes to the same hardcoded lesson (`Force Lab` content) regardless of which node was clicked — see §11 gap.
- **XP:** +125 flat.
- **Guardrails:** status vocabulary (`Practice`, `Boss Fight Active`, `Recharge Needed`, `Discovered`) matches the non-shaming status taxonomy in the system prompt.

### 5.6 `lesson` — Learning Workspace / Interactive Sandbox
- **Purpose:** delivers the hook + interactive discovery + concept synthesis steps of the pedagogical funnel for the current concept (today: Newton's Third Law only).
- **Components:**
  - Left sim card: animated chair-push scene (`#chairScene`, two `.student-rig` actors, push-flash, force arrows, caption line), plus 4 controls: Start Push ▶️ / Replay Push 🔁 / Slow Explanation 🪜 / Try a check 🎯.
  - Right sim card: "What to notice" formal-concept text (age-scaled via `getFormalConcept()`), 4-step tag list, plus 4 controls: I noticed both moved ✅ / Give me a hint 💡 / Mini-game ⚡ / Take a break 🥔.
- **Animation sequence (`playChairPush`):** ready pose (120ms) → push flash + force arrows (650ms) → rig separation (960ms) → summary caption (1800ms). Timings are fixed, not user-adjustable; `reducedMotion` disables the orb float but **does not currently disable this sequence** (see §10).
- **XP:** +60 (Start Push), +25 (Replay/Hint/Slow Explanation), +75 (Try a check), +100 (I noticed both moved), +50 (Mini-game, if gated open).
- **Guardrails:** matches Pedagogical Funnel steps 1–3 (hook/discovery/concept synthesis); mini-game is correctly gated behind `gamePositive`/interest and offers a graceful decline path via `openBreak()`.

### 5.7 `check` — Formative Diagnostic
- **Purpose:** one low-pressure question per system prompt's "never jump directly into testing" + "one diagnostic" rule.
- **Components:** age-scaled prompt (`copyByAge[ageBand].checkText`), 4 options (1 correct, 2 mapped to named misconceptions, 1 direct hint request).
- **Options → effects:**
  - Correct → `mistakeGenome` entry `{result: "understood"}`, XP +180, → `validate`.
  - "Pushes less" → misconception `unequal_force_pair`, confidence 0.71, → `renderMistake()`.
  - "Does nothing" → misconception `one_way_force_only`, confidence 0.68, → `renderMistake()`.
  - Hint request → → `renderMistake()` with ladder-style hint, no misconception tag.
- **XP:** +180 correct / +40 incorrect (still rewarded — mistakes are data, not penalized to zero) / +30 hint.
- **Guardrails:** exactly matches `<MISTAKE_TRACE>` schema from system prompt (question_id analog, misconception id, recommended_support array, confidence float).

### 5.8 `renderMistake` (sub-screen, not in `screens[]`)
- **Purpose:** Mistake Genome Panel — reframes a wrong answer as a strategy patch, never a bare "wrong."
- **Components:** message text (non-judgmental, names the tricky step), 4 options: Show picture 🎨 (→ back to lesson) / Tiny hint 💡 (deepens in place) / Try easier one 🪜 (deepens in place) / Try again 🎯 (→ `check`).
- **XP:** +50/+30/+50/+70 respectively — all positive, consistent with "celebrate strategy, not just correctness."

### 5.9 `validate` — Student-Owned Profile Confirmation
- **Purpose:** required checkpoint before any profile is treated as final.
- **Components:** summary sentence built from live state (`preferredBlend`, `energy`, `interest`), 4 options.
- **Options → effects:** Accept → confidence=0.85, → `dashboard`. Change/Add → `renderPatchMenu()`. Try again → resets to `energy` (full restart of onboarding, not full state wipe — XP and mistakeGenome persist, which may be intentional or a bug; see §11).
- **XP:** +500 on accept, +150 entering patch menu.
- **Guardrails:** matches system prompt's exact button set `[Yep ✅] [Change one thing ✏️] [Try again 🔄] [Add something 🧩]`.

### 5.10 `renderPatchMenu` (sub-screen)
- **Purpose:** lets the student pick *what* to patch rather than redoing everything.
- **Options → effects:** Learning recipe → `recipe`; Hardest subject → `quest`; Motivation → `interest`; Break settings → `openBreak()`.

### 5.11 `dashboard` — Teacher Demo Dashboard
- **Purpose:** professional, non-clinical backend summary — demo-only, not part of the student's normal path (reached via "Teacher Dashboard" topbar button or after validation accept).
- **Components:** 6-metric grid (preferred blend, energy, recommended next move, profile confidence, game preference, mistake-trace count) + a raw JSON snapshot block + Restart/Back-to-Quest-Map buttons.
- **Guardrails:** uses only cautious phrasing (`recommended_next_move`, no student-facing shame labels) — compliant with system prompt's teacher-dashboard language rules. The raw JSON block is appropriate here (teacher-only screen) but the *same* signal data is also exposed on the student-facing sidebar at all times — see §11.

---

## 6. Content Data Model — Lesson Scenario Library

**Current state:** the app hardcodes exactly one concept (Newton's Third Law) with 3 age variants (`copyByAge`) and one theme (skateboard/rolling-chair push-off), regardless of the `interest` selected in §5.3. The quest map's other three nodes (`Fractions Forest`, `Memory Cave`, `Writing Workshop`) are decorative — clicking any of them opens the same Force Lab lesson.

**Required extension:** the 18 scenarios generated from `demo_screens_prompt.md` (Newton's Laws 1–3 × {3rd grade, high school} × {Soccer, Barbie/Creative Play, Anime/Stories}) should be normalized into a single content array and selected at runtime by `(ageBand, interest, concept)` instead of being hardcoded in `copyByAge`.

### 6.1 Scenario schema

```js
{
  id: "law1_3rd_soccer",              // {law}_{gradeBand}_{theme}
  law: "law1" | "law2" | "law3",
  ageBand: "elementary" | "high",      // extend to "middle" by interpolating tone
  theme: "soccer" | "creative_play" | "anime_stories" | "science_building" | "gaming",
  concept_label: "Newton's First Law (Inertia)",
  hook: {
    kicker: "Context anchor hook",
    text: "Your soccer ball is just sitting in the grass. It won't move by itself — someone has to give it a nudge!",
    options: ["See what happens ⚽"]
  },
  sandbox: {
    kicker: "Interactive discovery",
    prompt: "Tap the ball to give it a kick. Watch what it does after.",
    options: ["Soft Tap 👟", "Big Kick 🦵", "No Kick 🚫"],
    animation_ref: "ball_kick_scene"   // maps to a CSS/JS scene module, see 6.3
  },
  concept: {
    kicker: "Concept synthesis",
    elementary_text: "A resting ball stays resting. A rolling ball keeps rolling — until something like grass, a wall, or a foot stops it. That's called inertia.",
    high_text: "Newton's First Law: an object remains at rest or in uniform motion in a straight line unless acted upon by a net external force. On grass, friction is the net force that decelerates the ball; on a frictionless surface, it would roll forever."
  },
  diagnostic: {
    kicker: "Formative diagnostic",
    prompt_elementary: "If nobody touches the ball, what does it do?",
    prompt_high: "A ball rolls at constant velocity on ice with negligible friction. What is the net force acting on it?",
    options: [
      { label: "Stays still 🧍 / Zero N", correct: true },
      { label: "Moves by itself 🌀 / Equal to its weight", correct: false, misconception: "spontaneous_motion" },
      { label: "Not sure 🤔 / Depends on speed", correct: false, misconception: "force_scales_with_speed" }
    ]
  },
  mistake_genome: {
    spontaneous_motion: {
      message: "Tricky part: things don't move on their own — that's a great thing to double check!",
      recommended_support: ["show_picture", "retry_without_timer"]
    },
    force_scales_with_speed: {
      message: "This suggests 'moving = force is acting' — a common inverse mix-up. Constant velocity means net force is zero, even while moving.",
      recommended_support: ["force_diagram", "related_problem"]
    }
  }
}
```

### 6.2 Full combination matrix (18 entries, sourced from `demo_screens_prompt.md` run)

| id | Grade | Theme | Law | Status |
|---|---|---|---|---|
| law1_3rd_soccer | 3rd | Soccer ⚽ | 1st (Inertia) | authored |
| law2_3rd_soccer | 3rd | Soccer ⚽ | 2nd (F=ma) | authored |
| law3_3rd_soccer | 3rd | Soccer ⚽ | 3rd (Action-Reaction) | authored — closest match to app's existing hardcoded lesson |
| law1_3rd_creative_play | 3rd | Creative Play (Barbie) 👗 | 1st | authored |
| law2_3rd_creative_play | 3rd | Creative Play (Barbie) 👗 | 2nd | authored |
| law3_3rd_creative_play | 3rd | Creative Play (Barbie) 👗 | 3rd | authored |
| law1_high_soccer | High | Soccer ⚽ | 1st | authored |
| law2_high_soccer | High | Soccer ⚽ | 2nd | authored |
| law3_high_soccer | High | Soccer ⚽ | 3rd | authored |
| law1_high_creative_play | High | Creative Play (Barbie) 👗 | 1st | authored |
| law2_high_creative_play | High | Creative Play (Barbie) 👗 | 2nd | authored |
| law3_high_creative_play | High | Creative Play (Barbie) 👗 | 3rd | authored |
| law1_3rd_anime_stories | 3rd | Anime/Stories 🌀 | 1st | authored |
| law2_3rd_anime_stories | 3rd | Anime/Stories 🌀 | 2nd | authored |
| law3_3rd_anime_stories | 3rd | Anime/Stories 🌀 | 3rd | authored |
| law1_high_anime_stories | High | Anime/Stories 🌀 | 1st | authored |
| law2_high_anime_stories | High | Anime/Stories 🌀 | 2nd | authored |
| law3_high_anime_stories | High | Anime/Stories 🌀 | 3rd | authored |

Full screen copy (hook/sandbox/concept/diagnostic/mistake text) for all 18 rows is already written out in `newtons_laws_demo_screens.md` from the earlier run of `demo_screens_prompt.md`; this spec's job is to define how the app *consumes* that content, not to re-author it.

**Middle school** is not in the source matrix; interpolate using the system prompt's Middle School style guidance (quests/boss-fights/XP framing layered on top of the elementary conceptual content, examples kept simple) rather than re-running the generator, to avoid content drift from the two authored bands.

### 6.3 Theme → animation scene mapping

The app's existing chair-push scene (`#chairScene`, `.student-rig`, `.push-flash`, `.scene-arrow`) is the **Law 3** interaction-pair visual and is theme-agnostic by construction (two abstract rigs). Reuse it directly for all `law3_*` entries regardless of theme — only the caption text and surrounding copy needs to change per theme, not the rig geometry.

Laws 1 and 2 need two new lightweight scene modules, generalized (not theme-specific per-asset) so a single scene serves all three themes via a swappable emoji/label token:

- **`rolling_object_scene` (Law 1):** one block on a track, a "push" trigger, and a friction toggle; block coasts until it hits a wall or friction is enabled. Token swap: ⚽ (soccer) / 🚗 (creative play) / 🌀 (anime/stories) rendered inside `.block`.
- **`push_strength_scene` (Law 2):** same track, but push strength is a 3-way selector (Soft/Medium/Big) that visibly changes the block's acceleration (animate `transition-duration` inversely to force). Same token-swap approach.

This keeps the CSS/animation surface small (3 scene modules total, not 18) while the *copy* varies fully per the content array in §6.1.

### 6.4 Interest tag → theme mapping (resolves the §5.3 gap)

| App interest tag (existing) | Content theme (from §6.2) | Notes |
|---|---|---|
| `Sports ⚽` | `soccer` | direct match |
| `Anime/Stories 🦸` | `anime_stories` | direct match |
| `Gaming 🎮` | *(none authored yet)* | recommend authoring a `gaming` pack (e.g., platformer cart/launch mechanics) in a follow-up run of `demo_screens_prompt.md`; until then, fall back to `anime_stories` copy since both are quest/XP-framed |
| `Science/Building 🧪` | *(none authored yet)* | recommend a `science_building` pack (e.g., lab cart/rocket-sled framing); until then fall back to `soccer` copy (concrete, physical, non-fantastical) |
| *(missing)* | `creative_play` (Barbie) | **the interest picker has no option that maps to this authored theme.** Recommend adding a 5th chip, e.g. `Creative Play 👗🧩`, to `renderInterest()` so this content pack is reachable. This also restores the gender-inclusive intent from the original scenario brief (soccer + creative-play + anime/stories as three broadly-appealing, non-assumed themes). |

---

## 7. Persistent UI Elements

- **Topbar:** brand mark, "Restart Demo" (calls `restart()`, full state reset except it does not clear `document.title` or the break timer edge cases — verify `clearInterval` runs before reset, which it does), "Teacher Dashboard" (direct jump, bypasses validation — acceptable for demo purposes only, see §12), "Reduce Motion" (toggles `body.reduced-motion`, currently only affects `.avatar-orb` float keyframe).
- **Progress bar:** `progressFill` width = `(index of current screen in screens[] + 1) / 9 * 100%`. Sub-screens (`renderMistake`, `renderMiniGame`, `renderPatchMenu`, `renderAfterBreak`, valve screens) do not have their own index and silently keep whatever percentage the last top-level screen had — acceptable, but should not be read as literal completion percentage.
- **Safety valves bar:** always visible at the bottom of the stage, 4 buttons wired directly via `data-valve` regardless of current screen — matches the system prompt's "persistent safety valves" requirement exactly.
- **Sidebar — Learning Avatar Snapshot:** 7 chips (Energy, Age Mode, Interest, Blend, XP, Density, Profile confidence). Purely a debug/demo convenience; not part of the "official" student-facing UI described in the system prompt, which keeps backend signals hidden. Keep for demo, gate for production (§11).
- **Sidebar — Internal State Preview:** raw `JSON.stringify` of `student_profile`, `internal_learner_signals`, `mistake_genome`. Same caveat as above, stronger — this is explicitly the kind of backend tag the system prompt says must never be shown to the student.

---

## 8. Break & Recovery Mode

- **Trigger points:** energy=Sleeping Potato/Low Battery (indirect, via fatigue signal only — does not auto-open the modal), explicit "I need a break 🥔" safety valve, "Take a break 🥔" button in `lesson`, declined mini-game, "Break settings 🥔" patch option.
- **Modal contents:** fixed title/copy ("Recharge Mode 🥔" / "Good call. Breaks are part of the strategy, not a failure state."), optional override message (used once, for declined mini-games), countdown timer, 4 duration options (1/3/5 min or "ready now").
- **Timer behavior:** `setInterval` at 1s resolution; on completion or immediate "ready now," awards +100 XP and routes to `renderAfterBreak()`, a dedicated warm-re-entry screen with 4 low-pressure restart options — matches system prompt's "restart with one tiny win" requirement exactly.
- **Dismissal:** clicking the overlay backdrop (not the modal itself) closes without awarding XP or transitioning — this is a silent-cancel path with no confirmation, acceptable.

---

## 9. Mini-Game Engagement Layer

- **Gate:** only reachable from `lesson` via "Mini-game ⚡", and only actually renders if `state.gamePositive || state.interest === "gaming"`; otherwise it politely declines into `openBreak()` with a custom message — matches system prompt's "avoid when student dislikes games" rule via an implicit rather than explicit check (no direct "I don't like games" signal exists yet, only positive-preference inference).
- **Game:** single "press the red button" reflex tap (`renderMiniGame`), always skippable, awards XP for participation not accuracy, sets `signals.gameEngagementPreference = "mini_game_positive"` on press — consistent with "never treat mini-game performance as intelligence or attention ability."
- **Exit paths:** press (→ `check` after 600ms auto-advance), "Back to lesson," or "Skip" — three low-friction exits, no forced completion.

---

## 10. Accessibility — Current State vs. Requirement

| Requirement (system prompt) | Current implementation | Gap |
|---|---|---|
| Large tap targets | `--tap: 52px` (62px in low-density mode) | Meets WCAG 2.5.5 minimum (44px) |
| Reduced motion option | `motionBtn` toggles `.reduced-motion` | Only suppresses the orb float animation; does **not** suppress the chair-push sequence, push-flash, or mini-game button transform — should be extended to short-circuit or fast-forward `playChairPush()`'s timed sequence when `state.reducedMotion` is true |
| Keyboard navigation | All interactive elements are real `<button>`s | Should work via default tab order; not explicitly tested/verified in this spec pass — recommend a manual tab-through pass |
| Screen reader compatibility | No `aria-live` region on `#screenRoot`, so screen transitions are silent to assistive tech; `role="dialog" aria-modal="true"` is present on the break overlay | Add `aria-live="polite"` to `#screenRoot` or the `.copy h2` so screen changes are announced |
| High contrast / no-color-only meaning | Force-pair arrows use both color (`--good`/`--danger`) and position (left/right) to convey meaning, and captions describe them in text | Compliant |
| Captions for audio / audio replay | No audio mode is implemented yet; `renderTooMuchReading()`'s "🔊 Audio" option currently just shows placeholder text explaining what audio mode *would* do | Not implemented — flagged as future work, not a regression, since text is honest about the placeholder |
| Dyslexia-friendly reading mode | Not implemented | Recommend a font-toggle (e.g., increased letter-spacing / OpenDyslexic) alongside the existing motion toggle |

---

## 11. Deviations From `system_prompt.md` (Flag for Product Decision)

1. **Backend signals visible to student.** The "Internal State Preview" JSON panel and several chip labels (e.g., raw `learningStyleMix`, `internal_learner_signals`) are shown in the main student-facing layout at all times. The system prompt requires these be routed internally and hidden from the student. In this build they exist for demo/reviewer visibility. **Recommendation:** keep for the internal/teacher demo build; add a `?mode=student` flag that hides both sidebar panels for any build meant to be shown to an actual student.
2. **Interest selection does not change lesson content.** All four interest options funnel into the same hardcoded Newton's Third Law / skateboard lesson. §6 specifies the fix (data-driven scenario array keyed by ageBand × interest × concept).
3. **Quest map nodes are decorative.** Clicking any of the four nodes opens the same lesson. Recommend wiring `state.currentConcept` + a `law` field per node so `Fractions Forest`, `Memory Cave`, and `Writing Workshop` either open distinct content or are visually marked "Coming soon" rather than silently substituting Force Lab content.
4. **No theme option maps to the authored "Creative Play" (Barbie) content pack.** See §6.4 — recommend adding a 5th interest chip.
5. **"Try again 🔄" on the validate screen restarts onboarding but does not reset `xp` or `mistakeGenome`.** Decide whether a "try again" on profile validation should be a full state reset (matching `restart()`) or a soft onboarding-only reset (current behavior). Not a correctness bug, but the two exits ("Restart Demo" button vs. "Try again 🔄" on validate) currently behave inconsistently and that inconsistency isn't documented anywhere else in the code.
6. **Reduced-motion toggle is incomplete** — see §10.

None of these are launch-blocking for a demo; all are called out because the governing system prompt is explicit enough (see its "Final Non-Negotiable Rules") that they should be resolved before this build is used with real students rather than as an internal/investor demo.

---

## 12. Out of Scope (Per Request)

The following are intentionally **not** specified here, per instruction:
- Persistent storage / database schema for student profiles across sessions
- Authentication, account creation, or session management
- Server-side logging, analytics pipelines, or event tracking
- Real teacher-login gating for the dashboard (currently reachable by any user via the topbar button)
- Localization/i18n beyond the English copy shown

If any of these become in-scope later, the `state` object in §4 is the natural seam to persist — it is already a single serializable object.

---

## 13. Critic Checklist (Per `system_prompt.md` §"Critic Agent Feedback Loop")

Applied against the current build as a whole:

| Check | Result | Note |
|---|---|---|
| Academic integrity | Pass (for the one implemented law) | Extend once §6 content is wired in |
| Age-appropriateness | Pass | `copyByAge` + `getFormalConcept` both scale correctly |
| Cognitive load | Pass | Low-density mode reduces text and enlarges buttons |
| Student safety | Pass | No PII collected; no self-harm handling path exists yet — **not tested**, out of scope for this UI-only spec but should be a hard requirement before real deployment |
| UI clarity | Pass | One primary action per screen throughout |
| Gamification balance | Pass | Mini-game is opt-in and skippable; XP is uniformly positive-only (no XP loss anywhere in the codebase) |
| Backend labels hidden from student | **Fail** | See §11.1 |
| Differentiated from generic chatbot/quiz app | Pass | Sandbox animation, quest map, avatar orb, and non-linear valve system all differentiate it |

---

## Appendix: File Cross-Reference

- `system_prompt.md` — governing behavior/tone/guardrail spec (this document implements against it)
- `demo_screens_prompt.md` — the reusable prompt used to generate scenario content
- `newtons_laws_demo_screens.md` — the 18 authored scenarios referenced in §6.2 (full hook/sandbox/concept/diagnostic copy per combination)
- `adaptive_learning_avatar_demo_v3.html` — the application this spec describes
