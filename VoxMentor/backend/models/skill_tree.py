from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SkillNode(BaseModel):
    node_id: str
    title: str
    description: str
    category: str           # fundamentals / oop / dsa / web / ai
    prerequisites: list[str] = []   # list of node_ids
    xp_required: int = 0

class UserSkillTree(BaseModel):
    user_id: str
    unlocked_nodes: list[str] = ["variables", "data_types"]   # start unlocked
    in_progress_nodes: list[str] = []
    completed_nodes: list[str] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SkillUnlockRequest(BaseModel):
    user_id: str
    node_id: str

# The full skill tree definition (static data)
SKILL_TREE_NODES: list[dict] = [
    # ── Fundamentals ──────────────────────────────────────────
    {"node_id": "variables",     "title": "Variables & Types",   "category": "fundamentals", "prerequisites": [],              "xp_required": 0},
    {"node_id": "data_types",    "title": "Data Types",          "category": "fundamentals", "prerequisites": [],              "xp_required": 0},
    {"node_id": "operators",     "title": "Operators",           "category": "fundamentals", "prerequisites": ["variables"],   "xp_required": 50},
    {"node_id": "conditionals",  "title": "Conditionals",        "category": "fundamentals", "prerequisites": ["operators"],   "xp_required": 100},
    {"node_id": "loops",         "title": "Loops",               "category": "fundamentals", "prerequisites": ["conditionals"],"xp_required": 150},
    {"node_id": "functions",     "title": "Functions",           "category": "fundamentals", "prerequisites": ["loops"],       "xp_required": 200},
    # ── OOP ───────────────────────────────────────────────────
    {"node_id": "classes",       "title": "Classes & Objects",   "category": "oop",          "prerequisites": ["functions"],   "xp_required": 300},
    {"node_id": "inheritance",   "title": "Inheritance",         "category": "oop",          "prerequisites": ["classes"],     "xp_required": 400},
    {"node_id": "polymorphism",  "title": "Polymorphism",        "category": "oop",          "prerequisites": ["inheritance"], "xp_required": 500},
    # ── DSA ───────────────────────────────────────────────────
    {"node_id": "arrays",        "title": "Arrays & Lists",      "category": "dsa",          "prerequisites": ["loops"],       "xp_required": 250},
    {"node_id": "recursion",     "title": "Recursion",           "category": "dsa",          "prerequisites": ["functions"],   "xp_required": 350},
    {"node_id": "sorting",       "title": "Sorting Algorithms",  "category": "dsa",          "prerequisites": ["arrays"],      "xp_required": 450},
    {"node_id": "linked_list",   "title": "Linked Lists",        "category": "dsa",          "prerequisites": ["classes"],     "xp_required": 550},
    {"node_id": "stacks_queues", "title": "Stacks & Queues",     "category": "dsa",          "prerequisites": ["linked_list"], "xp_required": 650},
    {"node_id": "trees",         "title": "Trees & Graphs",      "category": "dsa",          "prerequisites": ["recursion","linked_list"], "xp_required": 750},
    # ── Advanced ──────────────────────────────────────────────
    {"node_id": "dp",            "title": "Dynamic Programming", "category": "dsa",          "prerequisites": ["recursion","arrays"], "xp_required": 900},
    {"node_id": "complexity",    "title": "Time & Space Complexity","category":"dsa",         "prerequisites": ["sorting"],     "xp_required": 600},
]
