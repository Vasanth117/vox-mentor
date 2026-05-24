"""
Visualization Router
POST /api/visualize — ask AI to generate step-by-step algorithm animation data
GET  /api/visualize/presets — list of built-in algorithms
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.ai_engine import generate_visualization
import json

router = APIRouter(prefix="/api/visualize", tags=["visualization"])


class VisualizeRequest(BaseModel):
    algorithm: str
    language: str = "python"
    user_id: str = ""
    custom_input: str = ""
    custom_target: str = ""


# Built-in presets that get richer AI-generated data
PRESETS = [
    {"id": "bubble_sort",     "label": "Bubble Sort",      "type": "sorting",    "category": "Sorting"},
    {"id": "selection_sort",  "label": "Selection Sort",   "type": "sorting",    "category": "Sorting"},
    {"id": "insertion_sort",  "label": "Insertion Sort",   "type": "sorting",    "category": "Sorting"},
    {"id": "merge_sort",      "label": "Merge Sort",       "type": "sorting",    "category": "Sorting"},
    {"id": "binary_search",   "label": "Binary Search",    "type": "array",      "category": "Searching"},
    {"id": "linked_list",     "label": "Linked List",      "type": "linked_list","category": "Data Structures"},
    {"id": "bfs",             "label": "BFS Traversal",    "type": "graph",      "category": "Graphs"},
    {"id": "dfs",             "label": "DFS Traversal",    "type": "graph",      "category": "Graphs"},
    {"id": "factorial_recursion","label":"Factorial (Recursion)","type":"recursion","category":"Recursion"},
    {"id": "fibonacci_recursion","label":"Fibonacci (Recursion)","type":"recursion","category":"Recursion"},
    {"id": "stack_push_pop",  "label": "Stack Push/Pop",   "type": "stack",      "category": "Data Structures"},
    {"id": "queue_enqueue",   "label": "Queue Operations", "type": "queue",      "category": "Data Structures"},
]

PRESET_LOOKUP = {preset["id"]: preset for preset in PRESETS}
PRESET_ALIASES = {
    "queue_operations": "queue_enqueue",
    "queue": "queue_enqueue",
    "stack": "stack_push_pop",
    "factorial": "factorial_recursion",
    "fibonacci": "fibonacci_recursion",
}


def _normalize_preset_id(value: str) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _parse_number_list(custom_input: str, default_values: list[int]) -> list[int]:
    text = (custom_input or "").strip()
    if not text:
        return default_values
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            numbers = [int(x) for x in parsed]
            if numbers:
                return numbers
    except Exception:
        pass
    parts = [p.strip() for p in text.replace("|", ",").split(",") if p.strip()]
    numbers = []
    for part in parts:
        try:
            numbers.append(int(part))
        except Exception:
            continue
    return numbers or default_values


def _sorting_steps(values: list[int], mode: str) -> list[dict]:
    arr = values[:]
    steps: list[dict] = [
        {
            "step_number": 1,
            "action": f"Start {mode.replace('_', ' ')} on input array",
            "state": {"array": arr[:]},
            "highlight_indices": [],
            "comparison": {"left": None, "right": None},
            "swap": False,
        }
    ]
    step_number = 2

    if mode == "selection_sort":
        n = len(arr)
        for i in range(n):
            min_index = i
            for j in range(i + 1, n):
                steps.append({
                    "step_number": step_number,
                    "action": f"Compare index {j} with current min index {min_index}",
                    "state": {"array": arr[:]},
                    "highlight_indices": [min_index, j],
                    "comparison": {"left": min_index, "right": j},
                    "swap": False,
                })
                step_number += 1
                if arr[j] < arr[min_index]:
                    min_index = j
            if min_index != i:
                arr[i], arr[min_index] = arr[min_index], arr[i]
                steps.append({
                    "step_number": step_number,
                    "action": f"Swap min element into position {i}",
                    "state": {"array": arr[:]},
                    "highlight_indices": [i, min_index],
                    "comparison": {"left": i, "right": min_index},
                    "swap": True,
                })
                step_number += 1
    elif mode == "insertion_sort":
        for i in range(1, len(arr)):
            key = arr[i]
            j = i - 1
            steps.append({
                "step_number": step_number,
                "action": f"Insert element at index {i} into sorted left partition",
                "state": {"array": arr[:]},
                "highlight_indices": [i],
                "comparison": {"left": i, "right": j},
                "swap": False,
            })
            step_number += 1
            while j >= 0 and arr[j] > key:
                arr[j + 1] = arr[j]
                steps.append({
                    "step_number": step_number,
                    "action": f"Shift element at index {j} to the right",
                    "state": {"array": arr[:]},
                    "highlight_indices": [j, j + 1],
                    "comparison": {"left": j, "right": j + 1},
                    "swap": True,
                })
                step_number += 1
                j -= 1
            arr[j + 1] = key
            steps.append({
                "step_number": step_number,
                "action": f"Place key at index {j + 1}",
                "state": {"array": arr[:]},
                "highlight_indices": [j + 1],
                "comparison": {"left": j + 1, "right": None},
                "swap": False,
            })
            step_number += 1
    else:
        n = len(arr)
        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                steps.append({
                    "step_number": step_number,
                    "action": f"Compare adjacent elements at {j} and {j + 1}",
                    "state": {"array": arr[:]},
                    "highlight_indices": [j, j + 1],
                    "comparison": {"left": j, "right": j + 1},
                    "swap": False,
                })
                step_number += 1
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swapped = True
                    steps.append({
                        "step_number": step_number,
                        "action": "Swap because left element is greater than right",
                        "state": {"array": arr[:]},
                        "highlight_indices": [j, j + 1],
                        "comparison": {"left": j, "right": j + 1},
                        "swap": True,
                    })
                    step_number += 1
            if not swapped:
                break

    steps.append({
        "step_number": step_number,
        "action": "Array is sorted",
        "state": {"array": arr[:]},
        "highlight_indices": list(range(len(arr))),
        "comparison": {"left": None, "right": None},
        "swap": False,
    })
    return steps


def _binary_search_steps(custom_input: str, custom_target: str = "") -> tuple[list[dict], str, str]:
    values = _parse_number_list(custom_input, [1, 3, 5, 7, 9, 11, 13])
    values = sorted(values)
    target = values[len(values) // 2] if values else 0
    if (custom_target or "").strip():
        try:
            target = int((custom_target or "").strip())
        except Exception:
            pass
    elif "|" in (custom_input or ""):
        parts = (custom_input or "").split("|", 1)
        values = sorted(_parse_number_list(parts[0], values or [1, 3, 5]))
        try:
            target = int(parts[1].strip())
        except Exception:
            pass

    left, right = 0, len(values) - 1
    step_number = 1
    steps: list[dict] = []
    while left <= right:
        mid = (left + right) // 2
        steps.append({
            "step_number": step_number,
            "action": f"Check middle index {mid} with value {values[mid]}",
            "state": {"array": values[:], "target": target, "left": left, "right": right},
            "highlight_indices": [left, mid, right],
            "comparison": {"left": mid, "right": None},
            "swap": False,
        })
        step_number += 1
        if values[mid] == target:
            steps.append({
                "step_number": step_number,
                "action": f"Target {target} found at index {mid}",
                "state": {"array": values[:], "target": target, "left": left, "right": right},
                "highlight_indices": [mid],
                "comparison": {"left": mid, "right": None},
                "swap": False,
            })
            return steps, "O(log n)", "O(1)"
        if values[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    steps.append({
        "step_number": step_number,
        "action": f"Target {target} not found",
        "state": {"array": values[:], "target": target, "left": left, "right": right},
        "highlight_indices": [],
        "comparison": {"left": None, "right": None},
        "swap": False,
    })
    return steps, "O(log n)", "O(1)"


def _recursion_steps(name: str, custom_input: str) -> tuple[list[dict], str, str]:
    n = 5
    try:
        n = int((custom_input or "").strip() or "5")
    except Exception:
        n = 5
    n = max(0, min(n, 12))

    steps: list[dict] = []
    if "fibonacci" in name:
        stack = []
        step_number = 1

        def _fib(x: int) -> int:
            nonlocal step_number
            stack.append(f"fib({x})")
            steps.append({
                "step_number": step_number,
                "action": f"Call fib({x})",
                "state": {"call_stack": stack[:]}
            })
            step_number += 1
            if x <= 1:
                result = x
            else:
                result = _fib(x - 1) + _fib(x - 2)
            steps.append({
                "step_number": step_number,
                "action": f"Return {result} from fib({x})",
                "state": {"call_stack": stack[:]}
            })
            step_number += 1
            stack.pop()
            return result

        _fib(n)
        return steps, "O(2^n)", "O(n)"

    stack = []
    step_number = 1

    def _fact(x: int) -> int:
        nonlocal step_number
        stack.append(f"fact({x})")
        steps.append({
            "step_number": step_number,
            "action": f"Call fact({x})",
            "state": {"call_stack": stack[:]}
        })
        step_number += 1
        if x <= 1:
            result = 1
        else:
            result = x * _fact(x - 1)
        steps.append({
            "step_number": step_number,
            "action": f"Return {result} from fact({x})",
            "state": {"call_stack": stack[:]}
        })
        step_number += 1
        stack.pop()
        return result

    _fact(n)
    return steps, "O(n)", "O(n)"


def _graph_steps(mode: str, custom_input: str) -> tuple[list[dict], str, str]:
    default_nodes = ["A", "B", "C", "D", "E"]
    default_edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "E")]
    start = "A"

    text = (custom_input or "").strip()
    if text:
        try:
            payload = json.loads(text)
            nodes = payload.get("nodes") or default_nodes
            edge_pairs = payload.get("edges") or default_edges
            start = payload.get("start") or nodes[0]
            default_nodes = [str(n) for n in nodes]
            default_edges = [(str(e[0]), str(e[1])) for e in edge_pairs if isinstance(e, (list, tuple)) and len(e) >= 2]
        except Exception:
            pass

    adjacency: dict[str, list[str]] = {n: [] for n in default_nodes}
    for u, v in default_edges:
        if u in adjacency:
            adjacency[u].append(v)
        if v in adjacency:
            adjacency[v].append(u)

    node_coords = []
    edges_coords = []
    radius = 90
    center_x, center_y = 260, 120
    for i, node_id in enumerate(default_nodes):
        angle = (2 * 3.14159265 * i) / max(1, len(default_nodes))
        x = center_x + radius * __import__("math").cos(angle)
        y = center_y + radius * __import__("math").sin(angle)
        node_coords.append({"id": node_id, "x": x, "y": y})
    coord_lookup = {n["id"]: n for n in node_coords}
    for u, v in default_edges:
        if u in coord_lookup and v in coord_lookup:
            edges_coords.append({
                "x1": coord_lookup[u]["x"],
                "y1": coord_lookup[u]["y"],
                "x2": coord_lookup[v]["x"],
                "y2": coord_lookup[v]["y"],
            })

    steps: list[dict] = []
    visited = []

    if mode == "dfs":
        stack = [start]
        step_number = 1
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.append(node)
            for neighbor in reversed(adjacency.get(node, [])):
                if neighbor not in visited:
                    stack.append(neighbor)
            steps.append({
                "step_number": step_number,
                "action": f"Visit {node} and push unvisited neighbors",
                "state": {
                    "visited": visited[:],
                    "current": node,
                    "stack": stack[:],
                    "nodes": node_coords,
                    "edges": edges_coords,
                },
            })
            step_number += 1
        return steps, "O(V + E)", "O(V)"

    queue = [start]
    step_number = 1
    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.append(node)
        for neighbor in adjacency.get(node, []):
            if neighbor not in visited and neighbor not in queue:
                queue.append(neighbor)
        steps.append({
            "step_number": step_number,
            "action": f"Visit {node} and enqueue unvisited neighbors",
            "state": {
                "visited": visited[:],
                "current": node,
                "queue": queue[:],
                "nodes": node_coords,
                "edges": edges_coords,
            },
        })
        step_number += 1
    return steps, "O(V + E)", "O(V)"


def _linked_list_steps(custom_input: str) -> tuple[list[dict], str, str]:
    values = _parse_number_list(custom_input, [10, 20, 30, 40])
    steps = []
    for i in range(1, len(values) + 1):
        steps.append({
            "step_number": i,
            "action": f"Linked list built through node {i}",
            "state": {"array": values[:i]}
        })
    return steps, "O(n)", "O(n)"


def _stack_or_queue_steps(mode: str, custom_input: str) -> tuple[list[dict], str, str]:
    ops = [p.strip() for p in (custom_input or "").split(",") if p.strip()]
    if not ops:
        ops = ["push 5", "push 10", "push 15", "pop"] if mode == "stack" else ["enqueue 5", "enqueue 10", "dequeue", "enqueue 15"]

    container: list[int] = []
    steps = []
    step_number = 1
    for op in ops:
        lower = op.lower()
        if mode == "stack":
            if lower.startswith("push"):
                try:
                    value = int(op.split()[1])
                    container.append(value)
                except Exception:
                    pass
            elif lower.startswith("pop") and container:
                container.pop()
            steps.append({
                "step_number": step_number,
                "action": f"Apply operation: {op}",
                "state": {"stack": container[:]}
            })
        else:
            if lower.startswith("enqueue"):
                try:
                    value = int(op.split()[1])
                    container.append(value)
                except Exception:
                    pass
            elif lower.startswith("dequeue") and container:
                container.pop(0)
            steps.append({
                "step_number": step_number,
                "action": f"Apply operation: {op}",
                "state": {"queue": container[:]}
            })
        step_number += 1
    return steps, "O(n)", "O(n)"


def _generate_preset_visualization(preset_id: str, preset: dict, custom_input: str, custom_target: str = "") -> dict:
    if preset_id in {"bubble_sort", "selection_sort", "insertion_sort", "merge_sort"}:
        values = _parse_number_list(custom_input, [5, 1, 4, 2, 8])
        mode = "bubble_sort" if preset_id == "merge_sort" else preset_id
        steps = _sorting_steps(values, mode)
        return {
            "algorithm": preset["label"],
            "type": "sorting",
            "category": preset["category"],
            "description": f"Local deterministic visualization for {preset['label']}",
            "steps": steps,
            "time_complexity": "O(n²)" if preset_id != "merge_sort" else "O(n log n)",
            "space_complexity": "O(1)" if preset_id != "merge_sort" else "O(n)",
        }

    if preset_id == "binary_search":
        steps, t, s = _binary_search_steps(custom_input, custom_target)
        return {
            "algorithm": preset["label"],
            "type": "array",
            "category": preset["category"],
            "description": "Binary search over sorted input.",
            "steps": steps,
            "time_complexity": t,
            "space_complexity": s,
        }

    if preset_id in {"factorial_recursion", "fibonacci_recursion"}:
        steps, t, s = _recursion_steps(preset_id, custom_input)
        return {
            "algorithm": preset["label"],
            "type": "recursion",
            "category": preset["category"],
            "description": "Recursion call stack progression.",
            "steps": steps,
            "time_complexity": t,
            "space_complexity": s,
        }

    if preset_id in {"bfs", "dfs"}:
        steps, t, s = _graph_steps(preset_id, custom_input)
        return {
            "algorithm": preset["label"],
            "type": "graph",
            "category": preset["category"],
            "description": "Graph traversal walkthrough.",
            "steps": steps,
            "time_complexity": t,
            "space_complexity": s,
        }

    if preset_id == "linked_list":
        steps, t, s = _linked_list_steps(custom_input)
        return {
            "algorithm": preset["label"],
            "type": "linked_list",
            "category": preset["category"],
            "description": "Linked list node progression.",
            "steps": steps,
            "time_complexity": t,
            "space_complexity": s,
        }

    if preset_id in {"stack_push_pop", "queue_enqueue"}:
        mode = "stack" if preset_id == "stack_push_pop" else "queue"
        steps, t, s = _stack_or_queue_steps(mode, custom_input)
        return {
            "algorithm": preset["label"],
            "type": mode,
            "category": preset["category"],
            "description": f"{mode.title()} operations walkthrough.",
            "steps": steps,
            "time_complexity": t,
            "space_complexity": s,
        }

    return {
        "algorithm": preset["label"],
        "type": preset["type"],
        "category": preset["category"],
        "description": f"Visualization for {preset['label']}",
        "steps": [],
        "time_complexity": "O(?)",
        "space_complexity": "O(?)",
    }


@router.get("/presets")
async def get_presets():
    categories = {}
    for p in PRESETS:
        cat = p["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p)
    return {"presets": PRESETS, "by_category": categories}


@router.post("/")
async def visualize(req: VisualizeRequest):
    normalized = _normalize_preset_id(req.algorithm)
    preset_id = PRESET_ALIASES.get(normalized, normalized)
    preset = PRESET_LOOKUP.get(preset_id)
    algorithm_name = preset["label"] if preset else req.algorithm

    if preset:
        local = _generate_preset_visualization(preset_id, preset, req.custom_input, req.custom_target)
        if local.get("steps"):
            return local

    prompt_algorithm = algorithm_name
    if req.custom_input.strip() or req.custom_target.strip():
        prompt_algorithm = f"{algorithm_name} with input: {req.custom_input.strip()}"
        if req.custom_target.strip():
            prompt_algorithm += f" and target: {req.custom_target.strip()}"
    data = await generate_visualization(prompt_algorithm, req.language)

    if not isinstance(data, dict):
        data = {
            "algorithm": algorithm_name,
            "description": "Unable to generate visualization.",
            "steps": [],
            "time_complexity": "O(?)",
            "space_complexity": "O(?)",
        }

    if preset:
        data.setdefault("algorithm", preset["label"])
        data.setdefault("type", preset["type"])
        data.setdefault("category", preset["category"])
    else:
        data.setdefault("algorithm", algorithm_name)
        data.setdefault("type", "unknown")

    data.setdefault("description", f"Visualization for {data['algorithm']}")
    data.setdefault("steps", [])
    data.setdefault("time_complexity", "O(?)")
    data.setdefault("space_complexity", "O(?)")
    return data
