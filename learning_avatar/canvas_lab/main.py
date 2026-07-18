"""
Socratic Hybrid Canvas — FastAPI backend.

Serves the static SPA and a single prefetch endpoint that returns the
full lesson module in one shot: content, evaluation type, the character
library, and the asset manifest. Everything except the actual image bytes
is prefetched here — background/character art is only fetched by the
browser on demand, when a step referencing it actually mounts.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import pipeline

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Socratic Hybrid Canvas", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

LESSON_PAYLOAD = {
    "lesson_id": "sci-forces-01",
    "subject": "Science",
    "topic": "Operational Dynamics",
    "total_steps": 5,

    "user_profile": {
        "name": "Alex",
        "grade": "Gr 7",
        "avatar": "🧑‍🎓",
        "starting_xp": 1185,
    },

    "character_library": [
        {"id": "sparky", "label": "Sparky", "kit_color": "#facc15", "trim_color": "#ef4444"},
        {"id": "ironclad", "label": "Ironclad", "kit_color": "#f97316", "trim_color": "#7c2d12"},
        {"id": "maestro", "label": "Maestro", "kit_color": "#38bdf8", "trim_color": "#1d4ed8"},
    ],

    "asset_manifest": {
        "bg.stadium": "/static/mock-assets/backgrounds/scene_stadium.png",
        "bg.warehouse": "/static/mock-assets/backgrounds/scene_force.png",
        "bg.launchpad": "/static/mock-assets/backgrounds/scene_launchpad.png",
    },

    "steps": [
        # ---- Step 1: force duel (interactive_scene, multiple_choice) ----
        {
            "step_index": 1,
            "content_type": "interactive_scene",
            "standards": ["MS-PS2-1"],
            "scenario_text": "A 10 kg box: your kicker pushes RIGHT, the rival pushes LEFT. Dial in each side's force and hit Kick to see what happens.",
            "scene": {
                "background": "bg.stadium",
                "uses_character_picker": True,
                "objects": [
                    {
                        "id": "player",
                        "kind": "character",
                        "character_source": "selected_character",
                        "default_pos": {"x": 14, "y": 52},
                        "arrow": {"control_ref": "leftForce", "toward": "ball", "max_control": 100},
                    },
                    {
                        "id": "rival",
                        "kind": "character",
                        "character_source": {"id": "rival", "label": "Rival Striker", "kit_color": "#1e293b", "trim_color": "#475569"},
                        "default_pos": {"x": 82, "y": 52},
                        "arrow": {"control_ref": "rightForce", "toward": "ball", "max_control": 100},
                    },
                    {
                        "id": "ball",
                        "kind": "ball",
                        "default_pos": {"x": 50, "y": 58},
                    },
                ],
                "controls": [
                    {"id": "leftForce", "type": "slider", "label": "Your Force", "min": 0, "max": 100, "step": 5, "default": 50},
                    {"id": "rightForce", "type": "slider", "label": "Rival Force", "min": 0, "max": 100, "step": 5, "default": 50},
                    {"id": "kick", "type": "button", "label": "Kick!"},
                ],
                "behaviors": [
                    {
                        "trigger": {"on": "click", "control": "kick"},
                        "rules": [
                            {"if": "leftForce - rightForce > 0", "then": [{"action": "move", "target": "ball", "axis": "x", "toward": "right", "magnitude_expr": "leftForce - rightForce"}]},
                            {"if": "leftForce - rightForce < 0", "then": [{"action": "move", "target": "ball", "axis": "x", "toward": "left", "magnitude_expr": "rightForce - leftForce"}]},
                            {"if": "leftForce - rightForce == 0", "then": [{"action": "stop", "target": "ball"}]},
                        ],
                    }
                ],
            },
            "evaluation": {
                "type": "multiple_choice",
                "question": "When Net Force equals 0 N on the 10 kg box, what is its acceleration?",
                "hint": "F = ma. If Net Force (F) is zero, what is the acceleration (a)?",
                "options": [
                    {"id": "A", "text": "a = 5 m/s² — each force accelerates it"},
                    {"id": "B", "text": "a = 0 m/s² — zero net force = no acceleration", "is_correct": True},
                    {"id": "C", "text": "a = 10 m/s² — mass × force"},
                    {"id": "D", "text": "a = 1 m/s² in a random direction"},
                ],
            },
        },

        # ---- Step 2: crate & friction (interactive_scene, free_text) ----
        {
            "step_index": 2,
            "content_type": "interactive_scene",
            "standards": ["MS-PS2-1", "MS-PS2-2"],
            "scenario_text": "A warehouse crate is pushed while friction resists the motion. Click each force zone to inspect it, then work out the net force.",
            "scene": {
                "background": "bg.warehouse",
                "uses_character_picker": False,
                "objects": [
                    {"id": "crate", "kind": "click_zone", "prop": "crate", "label": "Applied Force (80 N)", "default_pos": {"x": 30, "y": 60}, "size": {"width_pct": 12, "height_pct": 18}},
                    {"id": "friction", "kind": "click_zone", "label": "Friction Force (20 N)", "default_pos": {"x": 55, "y": 68}, "size": {"width_pct": 14, "height_pct": 6}},
                ],
                "controls": [],
                "behaviors": [],
            },
            "evaluation": {
                "type": "free_text",
                "question": "A crate is pushed with 80 N while friction resists with 20 N. What is the net force, in newtons?",
                "hint": "Net force is the vector sum: subtract the opposing force from the applied force.",
                "accepted_answers": ["60", "60n", "60 n"],
            },
        },

        # ---- Step 3: rocket thrust (interactive_scene, dropdown) ----
        {
            "step_index": 3,
            "content_type": "interactive_scene",
            "standards": ["MS-PS2-1"],
            "scenario_text": "A 5 kg rocket fires 200 N of thrust upward while 50 N of gravity pulls it down. Click each force zone, then classify what's happening.",
            "scene": {
                "background": "bg.launchpad",
                "uses_character_picker": False,
                "objects": [
                    {"id": "thrust", "kind": "click_zone", "prop": "rocket", "label": "Thrust (200 N)", "default_pos": {"x": 20, "y": 48}, "size": {"width_pct": 11, "height_pct": 34}},
                    {"id": "gravity", "kind": "click_zone", "label": "Gravity (50 N)", "default_pos": {"x": 20, "y": 84}, "size": {"width_pct": 11, "height_pct": 8}},
                ],
                "controls": [],
                "behaviors": [],
            },
            "evaluation": {
                "type": "dropdown",
                "question": "Thrust and gravity are unequal here, so the net force is unbalanced and points upward. Which term describes the rocket's resulting motion?",
                "hint": "Find net force first (thrust minus gravity), then divide by mass: a = F_net / m. An unbalanced net force always means acceleration.",
                "choices": [
                    "Equilibrium (balanced forces)",
                    "Accelerating upward (unbalanced net force)",
                    "Terminal velocity",
                    "Free fall",
                ],
                "correct_choice": "Accelerating upward (unbalanced net force)",
            },
        },

        # ---- Step 4: slideshow (multiple_choice) ----
        {
            "step_index": 4,
            "content_type": "slideshow",
            "standards": ["MS-PS2-2"],
            "scenario_text": "A quick walkthrough of Newton's First Law before the next challenge.",
            "slides": [
                {"image": "bg.stadium", "caption": "Newton's First Law: an object at rest stays at rest, and an object in motion stays in motion, unless acted on by an unbalanced force."},
                {"image": "bg.warehouse", "caption": "A heavier crate needs more force to reach the same acceleration — that resistance to change in motion is inertia."},
                {"image": "bg.launchpad", "caption": "Once a rocket clears the pad, only an unbalanced force — like thrust overcoming gravity — changes its motion further."},
            ],
            "evaluation": {
                "type": "multiple_choice",
                "question": "Which statement is Newton's First Law (the Law of Inertia)?",
                "hint": "Think about what happens when the net force on an object is exactly zero.",
                "options": [
                    {"id": "A", "text": "Force equals mass times acceleration"},
                    {"id": "B", "text": "An object's motion stays unchanged unless an unbalanced force acts on it", "is_correct": True},
                    {"id": "C", "text": "Every action has an equal and opposite reaction"},
                ],
            },
        },

        # ---- Step 5: story mode (multiple_choice) ----
        {
            "step_index": 5,
            "content_type": "story",
            "standards": ["MS-PS2-1"],
            "scenario_text": "Debrief with your coach after the force-duel challenge.",
            "panels": [
                {"speaker": "Coach", "text": "Nice kick! Notice how the ball barely moved when both forces matched?"},
                {"speaker": "Alex", "text": "Right — net force was zero, so there was no acceleration, just like Newton said."},
                {"speaker": "Coach", "text": "Exactly. Now let's see what happens the moment those forces stop being equal."},
            ],
            "evaluation": {
                "type": "multiple_choice",
                "question": "In the story, why did the ball barely move when both kickers used equal force?",
                "hint": "Two equal, opposite forces sum to what net force?",
                "options": [
                    {"id": "A", "text": "The ball was too heavy to move at all"},
                    {"id": "B", "text": "Equal and opposite forces summed to zero net force, so there was no acceleration", "is_correct": True},
                    {"id": "C", "text": "Friction from the grass cancelled both kicks"},
                ],
            },
        },
    ],
}


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/api/lessons/load")
async def load_lesson():
    return LESSON_PAYLOAD


# ---------------------------------------------------------------------------
# LLM-generated lessons (backend-first slice — see
# docs/llm-lesson-generation-spec.md). Registration UI and /admin views are
# deferred; these are the real API routes a future UI would call into.
# ---------------------------------------------------------------------------


class StudentIn(BaseModel):
    name: str
    age: int | None = None
    grade: str | None = None
    favorite_sport: str | None = None
    favorite_character: str | None = None
    friend_names: str | None = None


class LessonRequestIn(BaseModel):
    student_id: int
    skill: str
    modality: str
    mastery_pct: float | None = None
    prereq_threshold: float | None = None
    negative_constraint_token: str | None = None


@app.post("/api/students")
async def create_student(student: StudentIn):
    with db.get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO students (name, age, grade, favorite_sport, favorite_character, friend_names)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                student.name,
                student.age,
                student.grade,
                student.favorite_sport,
                student.favorite_character,
                student.friend_names,
            ),
        )
        return {"id": cursor.lastrowid}


@app.post("/api/lesson-requests")
async def create_lesson_request(req: LessonRequestIn, background_tasks: BackgroundTasks):
    with db.get_conn() as conn:
        student = conn.execute("SELECT id FROM students WHERE id = ?", (req.student_id,)).fetchone()
        if student is None:
            raise HTTPException(status_code=404, detail=f"student {req.student_id} not found")

        cursor = conn.execute(
            """INSERT INTO lesson_requests
               (student_id, skill, modality, mastery_pct, prereq_threshold, negative_constraint_token, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (
                req.student_id,
                req.skill,
                req.modality,
                req.mastery_pct,
                req.prereq_threshold,
                req.negative_constraint_token,
            ),
        )
        request_id = cursor.lastrowid

    background_tasks.add_task(pipeline.run, request_id)
    return {"id": request_id, "status": "pending"}


@app.get("/api/lesson-requests/{request_id}")
async def get_lesson_request(request_id: int):
    with db.get_conn() as conn:
        req = conn.execute("SELECT * FROM lesson_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            raise HTTPException(status_code=404, detail=f"lesson request {request_id} not found")
        result = dict(req)

    if result["status"] == "ready":
        result["lesson"] = pipeline.get_ready_lesson_payload(request_id)

    return result
