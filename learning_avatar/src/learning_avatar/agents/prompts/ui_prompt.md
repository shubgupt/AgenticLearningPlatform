# UI Prompt — Shared Rendering Contract

**Role:** not an agent — a shared schema/style contract that the Root, Teaching, and Assessment agents all emit content against, so a single rendering shell (the HTML app) can display any agent's output without per-agent custom code.
**Consumed by:** `root_agent_prompt.md`, `teaching_agent_prompt.md`, `assessment_agent_prompt.md`
**Source of truth for style tokens:** `adaptive_learning_avatar_demo_v3.html` `:root` CSS variables (unchanged in MVP — see `technical_specification_v2.md` §4).

---

## 1. Design Tokens (reference only, not owned by any agent)

Color roles: `--accent` (cyan, primary interactive), `--accent2` (violet, secondary), `--accent3` (amber, reward/XP), `--good` (force-pair positive/correct), `--danger` (force-pair negative — **never used to mean "wrong answer," only as one half of a directional pair**), `--muted`/`--soft` (text hierarchy). Radius, spacing, and tap-target tokens (`--tap: 52–62px`) are fixed; agents do not emit styling, only content + component type.

---

## 2. Screen-Level Envelope

Every agent response that will become a screen must be wrapped in this envelope (mirrors `system_prompt.md`'s `<UI_RENDER>` block):

```json
{
  "screen_id": "string",
  "layout": "centered_avatar_card | adaptive_split_view | single_card_focus | visual_card_grid | quest_map_grid",
  "density": "low | normal",
  "motion": "gentle | none",
  "components": [ /* Component objects, §3 */ ],
  "reward": "string, e.g. '+150 XP · Chair Push Animation Active'"
}
```

`density: low` must be honored by the renderer exactly as `body.low-density` is in the v1 app (larger tap targets, ≥65% less body text). Any agent emitting content into a `lowDensity` session (flagged in the Root Agent's delegation call) must pre-shorten its own text rather than relying on the renderer to truncate.

---

## 3. Component Library

### 3.1 `choice_buttons`
```json
{ "type": "choice_buttons", "prompt": "string, 1-2 sentences max", "options": [
  { "label": "string incl. one emoji", "sublabel": "optional <small> text", "value": "machine key" }
] }
```
2–4 options. Exactly one `choice_buttons` component may be the primary interactive element per screen (system prompt's "one primary action" rule).

### 3.2 `sandbox_scene`
```json
{ "type": "sandbox_scene", "scene_ref": "rolling_object_scene | push_strength_scene | force_pair_rig_scene", "token": "emoji or short label swapped into the scene, e.g. '⚽'", "controls": ["string labels, become choice_buttons"], "caption_sequence": ["string", "string", "..."] }
```
`scene_ref` must be one of the pre-built animation modules (§5 of `technical_specification_v2.md`); agents choose a scene, not author new CSS/animation. `caption_sequence` entries display sequentially during the animation, mirroring the v1 `playChairPush()` timed-caption pattern.

### 3.3 `concept_card`
```json
{ "type": "concept_card", "kicker": "string", "text": "string, formally correct, grade-scaled", "tags": ["short reinforcement phrases, 3-5 words each"] }
```

### 3.4 `image_block`
```json
{ "type": "image_block", "image_prompt": "string, used if an image-generation tool is available", "image_alt": "required, describes the image for screen readers", "fallback_emoji": "single emoji or short glyph shown if no image renders" }
```
Every `image_block` **must** include `image_alt` even when no image tool is wired up in MVP — the fallback path (emoji/CSS scene) still needs the alt text for consistency once images are added later (see `teaching_agent_prompt.md` §5).

### 3.5 `diagnostic_check`
```json
{ "type": "diagnostic_check", "prompt": "string", "options": [
  { "label": "string", "correct": true, "value": "key" },
  { "label": "string", "correct": false, "value": "key", "misconception": "misconception_id" }
] }
```

### 3.6 `mistake_genome_panel`
```json
{ "type": "mistake_genome_panel", "misconception": "misconception_id", "message": "non-judgmental, names the tricky step", "recommended_support": ["show_picture", "tiny_hint", "easier_version", "retry"] }
```

### 3.7 `quest_map`
```json
{ "type": "quest_map", "nodes": [
  { "label": "string", "status": "Locked | Discovered | Practicing | Almost Mastered | Mastered | Needs Review | Boss Fight Active | Recharge Needed", "subjectContext": { "subject": "...", "topic": "...", "concept": "..." } }
] }
```

### 3.8 `safety_valves` (persistent, Root-owned, not emitted per-screen)
Always rendered by the shell, not by any agent: `Bored, change topic! 🔄` · `Too much reading! 🎨` · `Surprise me! 🎲` · `I need a break 🥔`.

### 3.9 `metric_grid` (teacher dashboard only)
```json
{ "type": "metric_grid", "metrics": [ { "label": "string", "value": "string" } ] }
```

---

## 4. Lesson & Quiz Schemas (used by Teaching / Assessment agents)

### 4.1 `LessonScreen` (Teaching Agent output — one per concept)
```json
{
  "id": "string, e.g. law1_3rd_soccer",
  "subject": "string",
  "topic": "string",
  "concept": "string",
  "gradeBand": "elementary | middle | high",
  "theme": "string",
  "hook": { "kicker": "string", "text": "string, 2-3 sentences", "options": ["string"] },
  "sandbox": { "kicker": "string", "prompt": "string", "scene_ref": "string", "token": "emoji", "options": ["string"] },
  "concept_screen": { "kicker": "string", "text_by_grade": { "elementary": "string", "middle": "string", "high": "string" } },
  "diagnostic": { "kicker": "string", "prompt_by_grade": { "elementary": "string", "high": "string" }, "options": [ /* per §3.5 */ ] },
  "mistake_genome": { "misconception_id": { "message": "string", "recommended_support": ["string"] } },
  "image_prompt": "string, optional",
  "image_alt": "string, required if image_prompt present"
}
```

### 4.2 `QuizItem` (Assessment Agent output)
```json
{
  "id": "string",
  "prompt": "string",
  "gradeBand": "string",
  "difficulty": "warmup | steady | challenge",
  "options": [ { "label": "string", "correct": true|false, "misconception": "string|null" } ],
  "hint_ladder": ["tiny nudge", "visual clue", "keyword reminder", "similar example", "step-by-step", "full explanation"]
}
```

---

## 5. Accessibility Requirements Every Emitted Screen Must Satisfy

- Every `image_block` has non-empty `image_alt`.
- Every `sandbox_scene` conveys its force-pair or cause-effect meaning through **text caption + shape/position**, never color alone (matches v1's arrow-direction + color-and-text pattern).
- No screen may emit more than one primary `choice_buttons`/`diagnostic_check` block.
- All option labels are ≤ 8 words so they render inside the fixed tap-target button width at any density setting.
