"""
Seed script — creates the 'Vedhu' intermediate test user.

Profile:
  Name:        Vedhu
  Email:       vedhu@voxmentor.test
  Password:    Vedhu@2024
  Level:       Intermediate (Python + DSA focus)
  Streak:      14 days
  XP:          2 840
  Career goal: Crack coding interviews
  Strengths:   variables, loops, functions, sorting
  Weaknesses:  recursion, trees, DP

Inserts into: users, progress, skill_tree, sessions,
              journal, roadmaps, revision_queue
Skips insertion if a user with the same email already exists
unless --force is passed.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from passlib.context import CryptContext
from pymongo import MongoClient, ReplaceOne

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import MONGO_URI, DB_NAME

UTC = timezone.utc
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
rng = random.Random(42)   # deterministic so we can re-run safely

# ─── helpers ────────────────────────────────────────────────────────────────

def now_utc() -> datetime:
    return datetime.now(UTC)


def days_ago(n: int) -> datetime:
    return now_utc() - timedelta(days=n)


def rand_dt(days_back_min: int, days_back_max: int) -> datetime:
    return now_utc() - timedelta(
        days=rng.randint(days_back_min, days_back_max),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )


# ─── static topic data ───────────────────────────────────────────────────────

TOPICS = [
    # (topic_id, attempts, correct, mastery, time_per_attempt_min)
    # fundamentals — solid
    ("variables",     40, 37, 92.0, 2.1),
    ("data_types",    35, 31, 85.0, 2.5),
    ("operators",     30, 27, 88.0, 2.3),
    ("conditionals",  28, 24, 82.0, 3.0),
    ("loops",         45, 40, 90.0, 2.8),
    ("functions",     38, 33, 86.0, 3.2),
    # OOP — in progress
    ("classes",       20, 14, 62.0, 5.1),
    ("inheritance",   12,  7, 48.0, 6.5),
    # DSA — spread
    ("arrays",        32, 24, 70.0, 4.2),
    ("recursion",     22,  9, 38.0, 9.8),   # weak
    ("sorting",       18, 13, 66.0, 5.7),
    ("stacks_queues", 14,  9, 55.0, 6.2),
    ("linked_list",   10,  5, 40.0, 8.0),   # struggling
    ("trees",          5,  1, 18.0, 14.3),  # barely started
    ("dp",             3,  0, 8.0,  20.0),  # just touched
    ("complexity",    15, 10, 60.0, 5.0),
]


# ─── AI chat history ─────────────────────────────────────────────────────────

CHAT_SESSIONS = [
    {
        "topic": "arrays",
        "days_ago": 13,
        "messages": [
            ("user",      "Hey, I'm confused about two-pointer on sorted arrays. Can you explain?"),
            ("assistant", "Sure! The two-pointer technique keeps one pointer at the start and one at the end of a sorted array. You move them toward each other based on a condition — usually comparing their sum to a target.\n\nExample: finding a pair that sums to `target`:\n```python\ndef two_sum_sorted(arr, target):\n    l, r = 0, len(arr) - 1\n    while l < r:\n        s = arr[l] + arr[r]\n        if s == target:\n            return (l, r)\n        elif s < target:\n            l += 1\n        else:\n            r -= 1\n    return None\n```\nThe key insight: if the sum is too small, move left pointer right (bigger value). If too big, move right pointer left. O(n) time, O(1) space. Does that make sense?"),
            ("user",      "Yes! What about when the array isn't sorted?"),
            ("assistant", "Good question. When unsorted, you'd typically:\n1. **Sort first** then apply two-pointer — O(n log n) overall\n2. **Use a hashset** to check for the complement in O(n) but O(n) space\n\nFor most interview problems, the hashset approach is preferred on unsorted input:\n```python\ndef two_sum_unsorted(arr, target):\n    seen = {}\n    for i, num in enumerate(arr):\n        complement = target - num\n        if complement in seen:\n            return (seen[complement], i)\n        seen[num] = i\n    return None\n```\nWhich one are you working with?"),
            ("user",      "Got it. What's the sliding window pattern?"),
            ("assistant", "Sliding window is for contiguous subarrays/substrings with a constraint. You expand the window from the right and shrink from the left when the constraint is violated.\n\nFixed-size window:\n```python\ndef max_sum_window(arr, k):\n    window_sum = sum(arr[:k])\n    max_sum = window_sum\n    for i in range(k, len(arr)):\n        window_sum += arr[i] - arr[i - k]\n        max_sum = max(max_sum, window_sum)\n    return max_sum\n```\nVariable-size window (longest substring with at most k distinct chars):\n```python\ndef longest_k_distinct(s, k):\n    freq, l, best = {}, 0, 0\n    for r, ch in enumerate(s):\n        freq[ch] = freq.get(ch, 0) + 1\n        while len(freq) > k:\n            freq[s[l]] -= 1\n            if freq[s[l]] == 0:\n                del freq[s[l]]\n            l += 1\n        best = max(best, r - l + 1)\n    return best\n```\nThese two patterns cover almost all sliding-window interview questions."),
        ],
    },
    {
        "topic": "recursion",
        "days_ago": 12,
        "messages": [
            ("user",      "Recursion still confuses me. I understand the concept but I can't write recursive functions on my own."),
            ("assistant", "That's totally normal at the intermediate stage — the *idea* makes sense but translating it to code is hard. Let me give you a framework:\n\n**The 3-question method:**\n1. What is the simplest input? (base case)\n2. What does the function return for that input?\n3. How does a general case reduce to a smaller version?\n\nLet's do factorial together. Answer the 3 questions out loud."),
            ("user",      "Base case is n=0 or n=1, returns 1. General case... n * factorial(n-1)?"),
            ("assistant", "Exactly right. Now write it:\n```python\ndef factorial(n):\n    if n <= 1:          # base case\n        return 1\n    return n * factorial(n - 1)   # trust the recursion\n```\nThe hard mental shift: **trust that factorial(n-1) works**. You don't need to trace the full call stack. Just write the relationship.\n\nNow try this: sum of digits of a number (e.g. 123 → 6). Use the 3-question method."),
            ("user",      "Um... base case is single digit? So n < 10 return n. General case is n%10 + sum_digits(n//10)?"),
            ("assistant", "Perfect! Here it is:\n```python\ndef sum_digits(n):\n    if n < 10:\n        return n\n    return (n % 10) + sum_digits(n // 10)\n```\nYou just wrote it by thinking, not memorising. That's the skill. Next challenge — try binary search recursively. It's the same pattern."),
            ("user",      "Ok let me try... def binary_search(arr, target, l, r): if l > r return -1. mid = (l+r)//2. if arr[mid]==target return mid. elif arr[mid] < target return binary_search(arr, target, mid+1, r). else return binary_search(arr, target, l, mid-1)"),
            ("assistant", "That is *exactly* correct, well done:\n```python\ndef binary_search(arr, target, l=0, r=None):\n    if r is None:\n        r = len(arr) - 1\n    if l > r:\n        return -1\n    mid = (l + r) // 2\n    if arr[mid] == target:\n        return mid\n    elif arr[mid] < target:\n        return binary_search(arr, target, mid + 1, r)\n    else:\n        return binary_search(arr, target, l, mid - 1)\n```\nYou're getting it. The recursion mental block is breaking. Keep practising — do 2 recursive problems daily this week."),
        ],
    },
    {
        "topic": "sorting",
        "days_ago": 11,
        "messages": [
            ("user",      "What sorting algorithms should I know for interviews?"),
            ("assistant", "For interviews, focus on these 5:\n\n| Algorithm      | Best  | Avg     | Worst   | Space | Stable? |\n|----------------|-------|---------|---------|-------|---------|\n| Merge Sort     | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |\n| Quick Sort     | O(n log n) | O(n log n) | O(n²)  | O(log n) | No |\n| Heap Sort      | O(n log n) | O(n log n) | O(n log n) | O(1) | No |\n| Counting Sort  | O(n+k) | O(n+k) | O(n+k)  | O(k) | Yes |\n| Bubble Sort    | O(n)  | O(n²)  | O(n²)   | O(1) | Yes |\n\nMerge Sort is the most asked. Do you want me to walk through the implementation?"),
            ("user",      "Yes please, merge sort"),
            ("assistant", "Merge Sort = divide + conquer. Split in half recursively, then merge sorted halves.\n\n```python\ndef merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left  = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    return merge(left, right)\n\ndef merge(left, right):\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] <= right[j]:\n            result.append(left[i]); i += 1\n        else:\n            result.append(right[j]); j += 1\n    result.extend(left[i:])\n    result.extend(right[j:])\n    return result\n```\n\nTrace it mentally: `[3,1,4,1,5]` → split → `[3,1]` + `[4,1,5]` → merge → `[1,1,3,4,5]`.\n\nKey interview points: **stable**, **O(n log n) always**, but uses **O(n) extra space**. For linked lists, merge sort is actually preferred over quicksort."),
        ],
    },
    {
        "topic": "recursion",
        "days_ago": 10,
        "messages": [
            ("user",      "I tried to write a recursive fibonacci but it's super slow on large inputs. What's wrong?"),
            ("assistant", "Classic problem! Naive recursion recalculates the same subproblems exponentially. `fib(5)` calls `fib(4)` and `fib(3)`. `fib(4)` calls `fib(3)` again. This gives O(2^n) time.\n\nFix 1 — **Memoisation** (top-down DP):\n```python\nfrom functools import lru_cache\n\n@lru_cache(maxsize=None)\ndef fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)\n```\nNow each value is computed once — O(n) time, O(n) space.\n\nFix 2 — **Iterative** (bottom-up DP):\n```python\ndef fib(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for _ in range(2, n+1):\n        a, b = b, a + b\n    return b\n```\nO(n) time, O(1) space. This pattern — converting recursive to iterative with DP — is extremely common in interviews."),
            ("user",      "Oh! So this is related to dynamic programming?"),
            ("assistant", "Exactly — fibonacci is the gateway to DP. The two core DP ideas:\n1. **Optimal substructure**: solution to big problem = solutions to subproblems\n2. **Overlapping subproblems**: same subproblems recur (unlike divide & conquer)\n\nFibonacci hits both. Your memoised fib is literally DP. Next step after this: coin change problem. Want to try it?"),
        ],
    },
    {
        "topic": "classes",
        "days_ago": 9,
        "messages": [
            ("user",      "Can you explain __init__ vs __new__ in Python classes?"),
            ("assistant", "`__new__` creates the object (allocates memory), `__init__` initialises it. In 99% of code you only define `__init__`.\n\n```python\nclass MyClass:\n    def __new__(cls, *args, **kwargs):\n        print('Creating instance')     # called first\n        return super().__new__(cls)\n\n    def __init__(self, value):\n        print('Initialising instance') # called second\n        self.value = value\n\nobj = MyClass(42)\n# Output:\n# Creating instance\n# Initialising instance\n```\n\nYou override `__new__` only for singletons, immutable types (like subclassing `int`/`str`), or metaclass magic. For DSA interviews, focus entirely on `__init__`. Does this clear it up?"),
            ("user",      "Yes! Also how does inheritance work with super()?"),
            ("assistant", "`super()` gives you a proxy to the parent class. In `__init__`, you call it to run the parent's setup before your own:\n\n```python\nclass Animal:\n    def __init__(self, name):\n        self.name = name\n\n    def speak(self):\n        return f'{self.name} makes a sound'\n\nclass Dog(Animal):\n    def __init__(self, name, breed):\n        super().__init__(name)   # run Animal.__init__ first\n        self.breed = breed\n\n    def speak(self):\n        return f'{self.name} barks'\n\nd = Dog('Rex', 'Labrador')\nprint(d.speak())   # Rex barks\n```\n\nKey rules:\n- Always call `super().__init__()` in child `__init__` unless you deliberately want to skip parent init\n- Python uses MRO (Method Resolution Order) for multiple inheritance — `Dog.__mro__` shows the lookup chain"),
        ],
    },
    {
        "topic": "linked_list",
        "days_ago": 8,
        "messages": [
            ("user",      "I don't understand how to reverse a linked list in-place"),
            ("assistant", "Let me break it down step by step. We need to reverse the `next` pointers.\n\nFirst, the Node class:\n```python\nclass Node:\n    def __init__(self, val):\n        self.val = val\n        self.next = None\n```\n\nIterative reversal — 3 pointers:\n```python\ndef reverse_list(head):\n    prev = None\n    curr = head\n    while curr:\n        next_node = curr.next   # save next\n        curr.next = prev        # reverse the link\n        prev = curr             # move prev forward\n        curr = next_node        # move curr forward\n    return prev   # prev is new head\n```\n\nTrace: `1→2→3→None`\n- Step 1: prev=None, curr=1 → 1.next=None, prev=1, curr=2\n- Step 2: prev=1, curr=2 → 2.next=1, prev=2, curr=3\n- Step 3: prev=2, curr=3 → 3.next=2, prev=3, curr=None\n- Return prev=3 (new head): `3→2→1→None` ✓"),
            ("user",      "What about recursive reversal?"),
            ("assistant", "Recursive version is elegant but harder to visualise:\n```python\ndef reverse_recursive(head):\n    if not head or not head.next:\n        return head\n    new_head = reverse_recursive(head.next)  # reverse rest\n    head.next.next = head   # make next node point back\n    head.next = None        # cut old forward link\n    return new_head\n```\n\nThe key insight: `reverse_recursive(head.next)` returns the new head of the reversed rest. Then `head.next.next = head` adds `head` to the end.\n\nFor interviews, iterative is safer — easier to code under pressure and O(1) stack space vs O(n) recursive overhead. Practice the iterative version until it's muscle memory."),
        ],
    },
    {
        "topic": "trees",
        "days_ago": 7,
        "messages": [
            ("user",      "Can you introduce me to binary trees? I haven't done them yet"),
            ("assistant", "Great time to start! A binary tree is a node-based structure where each node has at most 2 children.\n\n```python\nclass TreeNode:\n    def __init__(self, val):\n        self.val = val\n        self.left = None\n        self.right = None\n```\n\nThe 3 DFS traversals — **memorise these**:\n```python\n# Inorder: left → root → right (gives sorted order in BST)\ndef inorder(root):\n    if not root: return []\n    return inorder(root.left) + [root.val] + inorder(root.right)\n\n# Preorder: root → left → right (useful for serialisation)\ndef preorder(root):\n    if not root: return []\n    return [root.val] + preorder(root.left) + preorder(root.right)\n\n# Postorder: left → right → root (useful for deletion)\ndef postorder(root):\n    if not root: return []\n    return postorder(root.left) + postorder(root.right) + [root.val]\n```\n\nAnd BFS (level-order) using a queue:\n```python\nfrom collections import deque\n\ndef bfs(root):\n    if not root: return []\n    q, result = deque([root]), []\n    while q:\n        node = q.popleft()\n        result.append(node.val)\n        if node.left:  q.append(node.left)\n        if node.right: q.append(node.right)\n    return result\n```\n\nThese 4 traversals are the foundation of almost every tree interview problem. Which one do you want to practice first?"),
            ("user",      "Inorder seems most useful. Can I practice?"),
            ("assistant", "Absolutely. Here's your challenge:\n\n**Problem:** Given a BST root, return the Kth smallest element.\n**Hint:** Remember that inorder of BST gives sorted order.\n\nTry writing it without looking at the traversal above. Post your solution and I'll review it."),
        ],
    },
    {
        "topic": "arrays",
        "days_ago": 6,
        "messages": [
            ("user",      "What's a prefix sum and when do I use it?"),
            ("assistant", "Prefix sum is a preprocessed array where `prefix[i]` = sum of all elements from index 0 to i-1.\n\n```python\ndef build_prefix(arr):\n    prefix = [0] * (len(arr) + 1)\n    for i, x in enumerate(arr):\n        prefix[i+1] = prefix[i] + x\n    return prefix\n\n# Range sum query in O(1) after O(n) preprocessing:\n# sum(arr[l..r]) = prefix[r+1] - prefix[l]\n```\n\n**When to use it:**\n- Range sum queries (many queries on the same array)\n- Subarray sum = k problems\n- Equilibrium index (left_sum == right_sum)\n- 2D prefix sums for matrix queries\n\nExample — count subarrays with sum k:\n```python\ndef subarray_sum_k(arr, k):\n    count, prefix_sum, seen = 0, 0, {0: 1}\n    for x in arr:\n        prefix_sum += x\n        count += seen.get(prefix_sum - k, 0)\n        seen[prefix_sum] = seen.get(prefix_sum, 0) + 1\n    return count\n```\nThis is O(n) using a hashmap of prefix sums. Extremely common in medium-hard array problems."),
        ],
    },
    {
        "topic": "dp",
        "days_ago": 5,
        "messages": [
            ("user",      "I want to start dynamic programming. Where do I begin?"),
            ("assistant", "Start with these 4 problems in order — each one teaches a new DP pattern:\n\n1. **Fibonacci** (memoisation basics — you already did this!)\n2. **Coin Change** (unbounded knapsack pattern)\n3. **Longest Common Subsequence** (2D DP table)\n4. **0/1 Knapsack** (classic capacity DP)\n\nLet's do Coin Change:\n**Problem:** minimum coins to make amount `n` from denominations `coins`.\n\n```python\ndef coin_change(coins, amount):\n    dp = [float('inf')] * (amount + 1)\n    dp[0] = 0\n    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a:\n                dp[a] = min(dp[a], dp[a - c] + 1)\n    return dp[amount] if dp[amount] != float('inf') else -1\n```\n\n`dp[a]` = minimum coins to make amount `a`. For each amount, try every coin.\n\nRecurrence: `dp[a] = min(dp[a - c] + 1)` for all valid coins `c`.\n\nTrace: coins=[1,2,5], amount=7 → dp[7]=2 (5+2). Try it!"),
            ("user",      "This is making sense but I'm struggling to come up with the recurrence relation myself"),
            ("assistant", "That's the hardest part of DP and it takes practice. Here's a systematic way to find recurrences:\n\n**Step 1 — Define state:** What does `dp[i]` (or `dp[i][j]`) represent in English?\n - Coin Change: `dp[i]` = min coins to make amount i\n\n**Step 2 — Think about the last decision:** What is the last thing that happened?\n - Coin Change: the last coin I picked was coin `c`\n\n**Step 3 — Express dp[i] in terms of smaller states:**\n - If I used coin `c` last, I needed `dp[i - c]` coins before it, plus 1\n - So `dp[i] = min over all c of (dp[i-c] + 1)`\n\n**Step 4 — Base case:** smallest valid state\n - `dp[0] = 0` (0 coins to make 0)\n\nPractice this 4-step approach on every new DP problem. After 10 problems it becomes automatic."),
        ],
    },
    {
        "topic": "stacks_queues",
        "days_ago": 4,
        "messages": [
            ("user",      "What are the must-know stack problems for interviews?"),
            ("assistant", "The top 5 stack interview patterns:\n\n**1. Valid Parentheses** (classic)\n```python\ndef is_valid(s):\n    stack, pairs = [], {')':'(', ']':'[', '}':'{'}\n    for ch in s:\n        if ch in '([{':\n            stack.append(ch)\n        elif not stack or stack[-1] != pairs[ch]:\n            return False\n        else:\n            stack.pop()\n    return not stack\n```\n\n**2. Monotonic Stack** — next greater element:\n```python\ndef next_greater(arr):\n    result = [-1] * len(arr)\n    stack = []\n    for i, x in enumerate(arr):\n        while stack and arr[stack[-1]] < x:\n            result[stack.pop()] = x\n        stack.append(i)\n    return result\n```\n\n**3. Min Stack** — O(1) min retrieval\n**4. Daily Temperatures** (monotonic stack variant)\n**5. Largest Rectangle in Histogram** (hard — monotonic stack)\n\nPatterns 1 and 2 cover 80% of stack interview questions. Do you want to practice the monotonic stack concept?"),
        ],
    },
    {
        "topic": "complexity",
        "days_ago": 3,
        "messages": [
            ("user",      "How do I analyse time complexity of recursive algorithms?"),
            ("assistant", "Great question. For recursion, use the **Recurrence Relation approach** or the **Master Theorem**.\n\n**Master Theorem** applies to divide-and-conquer: `T(n) = aT(n/b) + O(n^d)`\n- a = number of recursive calls\n- b = factor by which input shrinks\n- d = work per level outside recursion\n\nCases:\n```\nif log_b(a) < d:  T(n) = O(n^d)         # work dominates\nif log_b(a) = d:  T(n) = O(n^d log n)   # balanced\nif log_b(a) > d:  T(n) = O(n^log_b(a))  # recursion dominates\n```\n\nExamples:\n- Merge Sort: `T(n) = 2T(n/2) + O(n)` → a=2, b=2, d=1, log_2(2)=1=d → O(n log n)\n- Binary Search: `T(n) = T(n/2) + O(1)` → a=1, b=2, d=0, log_2(1)=0=d → O(log n)\n- Naive Fibonacci: `T(n) = 2T(n-1) + O(1)` → not divide-and-conquer, use tree method → O(2^n)\n\nFor non-D&C recursion, draw the recursion tree and count nodes × work per node."),
        ],
    },
    {
        "topic": "functions",
        "days_ago": 2,
        "messages": [
            ("user",      "What are Python decorators and how do they work?"),
            ("assistant", "A decorator is a function that takes a function and returns a modified version of it — essentially a wrapper.\n\n```python\ndef timer(func):\n    import time\n    def wrapper(*args, **kwargs):\n        start = time.time()\n        result = func(*args, **kwargs)\n        print(f'{func.__name__} took {time.time()-start:.4f}s')\n        return result\n    return wrapper\n\n@timer\ndef slow_sum(n):\n    return sum(range(n))\n\nslow_sum(10_000_000)   # prints timing\n```\n\n`@timer` is syntactic sugar for `slow_sum = timer(slow_sum)`.\n\nBuilt-in decorators you must know:\n```python\nclass MyClass:\n    @staticmethod\n    def static_method():         # no self/cls, just a namespaced function\n        pass\n\n    @classmethod\n    def class_method(cls):       # receives class, not instance\n        return cls()\n\n    @property\n    def computed(self):          # access like attribute, not method call\n        return self._value * 2\n```\n\nDecorators are everywhere in Python — Flask routes, FastAPI endpoints, Django views, pytest fixtures. Understanding them unlocks a lot of real-world code."),
            ("user",      "Can decorators take arguments?"),
            ("assistant", "Yes — you add another layer of nesting:\n```python\ndef repeat(n):\n    def decorator(func):\n        def wrapper(*args, **kwargs):\n            for _ in range(n):\n                result = func(*args, **kwargs)\n            return result\n        return wrapper\n    return decorator\n\n@repeat(3)\ndef greet(name):\n    print(f'Hello {name}!')\n\ngreet('Vedhu')  # prints 3 times\n```\n\nThe call chain: `repeat(3)` returns `decorator`, which wraps `greet`. When you call `greet()`, you're actually calling `wrapper()`.\n\nReal-world example: `@app.route('/path')` in Flask/FastAPI is a decorator factory — `app.route` returns a decorator."),
        ],
    },
    {
        "topic": "arrays",
        "days_ago": 1,
        "messages": [
            ("user",      "Quick question — in-place vs out-of-place algorithms. How do I know which one an interview wants?"),
            ("assistant", "The question or constraints usually hint at it:\n- 'Do not use extra space' or 'O(1) space' → in-place\n- 'Return a new array' → out-of-place is fine\n- No mention → either, but in-place is often preferred\n\n**In-place examples:**\n```python\n# Reverse array in-place\ndef reverse_inplace(arr):\n    l, r = 0, len(arr) - 1\n    while l < r:\n        arr[l], arr[r] = arr[r], arr[l]\n        l += 1; r -= 1\n\n# Remove duplicates from sorted array in-place (LeetCode 26)\ndef remove_duplicates(nums):\n    k = 1\n    for i in range(1, len(nums)):\n        if nums[i] != nums[i-1]:\n            nums[k] = nums[i]\n            k += 1\n    return k   # first k elements are unique\n```\n\nFor in-place: think two-pointers (one 'write' pointer, one 'read' pointer).\nFor out-of-place: just build a new list with a list comprehension or explicit loop.\n\nIn interviews, always state your approach before coding: 'I'll do this in-place with a two-pointer technique, O(n) time O(1) space.'"),
        ],
    },
    # today session — most recent
    {
        "topic": "recursion",
        "days_ago": 0,
        "messages": [
            ("user",      "Let me try the tree problem you gave me. def kth_smallest(root, k): result = inorder(root) return result[k-1]  def inorder(root): if not root return [] return inorder(root.left) + [root.val] + inorder(root.right)"),
            ("assistant", "Good attempt! Your logic is correct but there's a more efficient approach for interviews — stop as soon as you've found the Kth element instead of building the whole list:\n\n```python\ndef kth_smallest(root, k):\n    self_k = [k]   # mutable counter\n    self_res = [0]\n\n    def inorder(node):\n        if not node or self_k[0] == 0:\n            return\n        inorder(node.left)\n        self_k[0] -= 1\n        if self_k[0] == 0:\n            self_res[0] = node.val\n            return\n        inorder(node.right)\n\n    inorder(root)\n    return self_res[0]\n```\n\nOr the cleaner Pythonic version using a generator:\n```python\ndef kth_smallest(root, k):\n    def inorder(node):\n        if node:\n            yield from inorder(node.left)\n            yield node.val\n            yield from inorder(node.right)\n    return next(x for i, x in enumerate(inorder(root), 1) if i == k)\n```\n\nYour O(n) space solution is acceptable in interviews though. State the trade-off: 'I can also do this with O(h) stack space using early termination.' Ready for the next tree problem?"),
        ],
    },
]


# ─── journal entries ──────────────────────────────────────────────────────────

JOURNAL_ENTRIES = [
    {
        "days_ago": 13,
        "entry": "Started the two-pointer section today. Arrays are finally clicking! The sliding window pattern was confusing at first but after seeing 3 examples it made sense. I solved the 'max sum subarray of size k' on my own without looking at hints.",
        "mood": "motivated",
        "analysis": "Strong positive progress signal. Array fundamentals are consolidating well. Two-pointer pattern understood. Recommend progressing to hash-map based array problems.",
    },
    {
        "days_ago": 11,
        "entry": "Recursion is hard. I tried for an hour to write a function to flatten a nested list recursively and gave up and looked at the solution. I feel like I understand it after but I couldn't get there on my own.",
        "mood": "frustrated",
        "analysis": "Productive struggle signal. Recursion mental model is incomplete. Recommend explicit base-case/general-case framework drills. Suggest 5 easy recursive problems before moving on.",
    },
    {
        "days_ago": 9,
        "entry": "OOP session with the AI tutor was really helpful. I always confused __init__ and __new__ but now it makes sense. Implemented a Stack class using a list. Also learned about @property for the first time.",
        "mood": "satisfied",
        "analysis": "OOP fundamentals progressing well. Class design understanding improving. Properties and dunder methods newly acquired. Ready for inheritance and polymorphism deep-dive.",
    },
    {
        "days_ago": 7,
        "entry": "First exposure to binary trees today. The 4 traversal patterns were a lot to absorb in one session. Inorder and BFS made sense. Preorder and postorder I had to re-read twice. Going to write each one from memory tomorrow.",
        "mood": "overwhelmed",
        "analysis": "Tree data structure introduced. Cognitive load is high — 4 traversal patterns in one session. Recommend spaced review over 3 days. Active recall drill (write from memory) is the right strategy user identified.",
    },
    {
        "days_ago": 5,
        "entry": "Finally started DP! Coin change problem took me about 45 minutes with hints. The key insight was defining dp[i] in English first (minimum coins to make amount i). Once I had the state definition, the recurrence came naturally. This 4-step method is really helping.",
        "mood": "proud",
        "analysis": "Breakthrough moment with DP. State definition strategy is working. Template-based approach accelerating pattern recognition. Strong engagement signal.",
    },
    {
        "days_ago": 3,
        "entry": "Time complexity analysis — I can do O(n), O(n^2), O(log n) easily. But the Master Theorem for recursion is confusing. I need to practice identifying a, b, d in a recurrence. Going to do 5 examples manually tomorrow.",
        "mood": "focused",
        "analysis": "Complexity analysis foundations solid. Master Theorem conceptually understood but not yet automatised. Self-directed practice plan identified — good metacognitive awareness.",
    },
    {
        "days_ago": 1,
        "entry": "Did 4 LeetCode easy/medium problems today without any help. Solved: Two Sum (hashmap), Reverse Linked List (iterative), Valid Parentheses (stack), and Maximum Subarray (Kadane's). Kadane's was the hardest — I had to look up the approach but coded it myself after understanding.",
        "mood": "confident",
        "analysis": "Significant milestone — independent problem solving across 4 different patterns. Array, LL, stack, and DP all attempted. Kadane's algorithm exposure. Confidence is high. Ready to progress to medium-difficulty tree and graph problems.",
    },
]


# ─── main ─────────────────────────────────────────────────────────────────────

def main(force: bool = False) -> None:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5_000)
        client.admin.command("ping")
    except Exception as exc:
        print(f"[ERROR] Cannot connect to MongoDB: {exc}")
        sys.exit(1)

    db = client[DB_NAME]

    # ── check existing ──
    existing = db["users"].find_one({"email": "vedhu@voxmentor.test"})
    if existing and not force:
        print("[SKIP] User vedhu@voxmentor.test already exists. Use --force to recreate.")
        print(f"       user_id = {existing['user_id']}")
        sys.exit(0)

    user_id = existing["user_id"] if existing else str(uuid4())
    print(f"[INFO] Seeding user_id = {user_id}")

    today = now_utc()

    # ── 1. USER ──────────────────────────────────────────────────────────────
    user_doc = {
        "user_id": user_id,
        "name": "Vedhu",
        "email": "vedhu@voxmentor.test",
        "password_hash": pwd_ctx.hash("Vedhu@2024"),
        "preferred_language": "english",
        "career_goal": "Crack coding interviews",
        "skill_level": "intermediate",
        "xp": 2840,
        "streak": 14,
        "longest_streak": 14,
        "last_active": today,
        "last_mood": "confident",
        "badges": [
            "first_session",
            "week_streak",
            "array_master",
            "recursion_unlocked",
            "sorting_complete",
            "dp_intro",
        ],
        "teaching_style": "balanced",
        "created_at": days_ago(20),
    }
    db["users"].replace_one({"user_id": user_id}, user_doc, upsert=True)
    print("[OK]  users")

    # ── 2. PROGRESS ──────────────────────────────────────────────────────────
    topic_docs = []
    for (tid, attempts, correct, mastery, tpm) in TOPICS:
        topic_docs.append({
            "topic": tid,
            "mastery": mastery,
            "attempts": attempts,
            "correct": correct,
            "time_spent_minutes": round(tpm * attempts, 1),
            "last_practiced": rand_dt(0, 13),
        })

    weak_areas  = [t for (t, _, _, m, _) in TOPICS if m < 45]
    strong_areas = [t for (t, _, _, m, _) in TOPICS if m >= 80]

    progress_doc = {
        "user_id": user_id,
        "topics": topic_docs,
        "total_xp": 2840,
        "streak": 14,
        "longest_streak": 14,
        "total_sessions": len(CHAT_SESSIONS) + 5,   # a few extra implicit ones
        "total_time_minutes": round(sum(tpm * att for (_, att, _, _, tpm) in TOPICS), 1),
        "weak_areas": weak_areas,
        "strong_areas": strong_areas,
        "updated_at": today,
    }
    db["progress"].replace_one({"user_id": user_id}, progress_doc, upsert=True)
    print("[OK]  progress")

    # ── 3. SKILL TREE ─────────────────────────────────────────────────────────
    completed   = ["variables", "data_types", "operators", "conditionals",
                   "loops", "functions", "arrays", "sorting", "complexity"]
    in_progress = ["classes", "recursion", "stacks_queues", "linked_list"]
    unlocked    = completed + in_progress + ["inheritance", "trees"]

    skill_doc = {
        "user_id": user_id,
        "unlocked_nodes": unlocked,
        "in_progress_nodes": in_progress,
        "completed_nodes": completed,
        "updated_at": today,
    }
    db["skill_tree"].replace_one({"user_id": user_id}, skill_doc, upsert=True)
    print("[OK]  skill_tree")

    # ── 4. CHAT SESSIONS ──────────────────────────────────────────────────────
    db["sessions"].delete_many({"user_id": user_id})
    session_docs = []
    for s in CHAT_SESSIONS:
        created = now_utc() - timedelta(days=s["days_ago"], hours=rng.randint(8, 20))
        msgs = []
        for (role, content) in s["messages"]:
            msgs.append({
                "role": role,
                "content": content,
                "timestamp": created + timedelta(minutes=len(msgs) * 2),
            })
        session_docs.append({
            "user_id": user_id,
            "topic": s["topic"],
            "language": "python",
            "messages": msgs,
            "created_at": created,
            "updated_at": created + timedelta(minutes=len(msgs) * 2 + 1),
        })
    db["sessions"].insert_many(session_docs)
    print(f"[OK]  sessions ({len(session_docs)} created)")

    # ── 5. JOURNAL ────────────────────────────────────────────────────────────
    db["journal"].delete_many({"user_id": user_id})
    journal_docs = []
    for je in JOURNAL_ENTRIES:
        created = now_utc() - timedelta(days=je["days_ago"], hours=rng.randint(19, 22))
        journal_docs.append({
            "user_id": user_id,
            "entry": je["entry"],
            "mood": je["mood"],
            "analysis": je["analysis"],
            "tags": [je["mood"]],
            "created_at": created,
        })
    db["journal"].insert_many(journal_docs)
    print(f"[OK]  journal ({len(journal_docs)} entries)")

    # ── 6. ROADMAPS ───────────────────────────────────────────────────────────
    roadmap_docs = []
    for goal_key, weeks_milestones in {
        "crack interviews": [
            ["Arrays & Strings refresh", "Two-pointer and sliding window", "Practice 6 medium problems"],
            ["Hashing + Prefix sums", "Sorting patterns", "Mock interview round 1"],
            ["Trees + Graph traversal", "Dynamic Programming basics", "Timed problem set"],
            ["Systematic revision", "Mock interview round 2", "Behavioural + communication prep"],
        ],
        "dsa in 30 days": [
            ["Arrays + Strings", "Recursion basics", "Daily 2 easy problems"],
            ["Linked List + Stack/Queue", "Binary search", "Timed drills"],
            ["Trees + Graphs", "Greedy + two pointers", "Mock round"],
            ["Dynamic Programming intro", "Mixed revision", "Final mock interview"],
        ],
    }.items():
        weekly = [{"week": i+1, "milestones": ms, "status": "pending" if i > 1 else "in_progress"}
                  for i, ms in enumerate(weeks_milestones)]
        roadmap_docs.append({
            "user_id": user_id,
            "goal": goal_key,
            "weeks": weekly,
            "created_at": days_ago(rng.randint(3, 7)),
            "updated_at": today,
        })
    db["roadmaps"].delete_many({"user_id": user_id})
    db["roadmaps"].insert_many(roadmap_docs)
    print(f"[OK]  roadmaps ({len(roadmap_docs)} created)")

    # ── 7. REVISION QUEUE ────────────────────────────────────────────────────
    revision_topics = [
        {"topic": "recursion",    "mastery": 38, "accuracy_pct": 41.0, "priority": 1},
        {"topic": "trees",        "mastery": 18, "accuracy_pct": 20.0, "priority": 2},
        {"topic": "dp",           "mastery": 8,  "accuracy_pct": 0.0,  "priority": 3},
        {"topic": "linked_list",  "mastery": 40, "accuracy_pct": 50.0, "priority": 4},
        {"topic": "inheritance",  "mastery": 48, "accuracy_pct": 58.0, "priority": 5},
        {"topic": "classes",      "mastery": 62, "accuracy_pct": 70.0, "priority": 6},
    ]
    db["revision_queue"].delete_many({"user_id": user_id})
    db["revision_queue"].insert_one({
        "user_id": user_id,
        "queue": revision_topics,
        "updated_at": today,
    })
    print("[OK]  revision_queue")

    # ── summary ──────────────────────────────────────────────────────────────
    print("\n" + "─" * 48)
    print("  Test user 'Vedhu' seeded successfully")
    print("─" * 48)
    print(f"  Email    : vedhu@voxmentor.test")
    print(f"  Password : Vedhu@2024")
    print(f"  user_id  : {user_id}")
    print(f"  XP       : 2840  |  Streak: 14 days")
    print(f"  Sessions : {len(session_docs)} (14 topics, spanning 14 days)")
    print(f"  Journal  : {len(journal_docs)} entries")
    print(f"  Roadmaps : {len(roadmap_docs)}")
    print(f"  Skills   : {len(completed)} completed, {len(in_progress)} in-progress")
    print(f"  Strong   : {', '.join(strong_areas)}")
    print(f"  Weak     : {', '.join(weak_areas)}")
    print("─" * 48)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Vedhu test user")
    parser.add_argument("--force", action="store_true", help="Recreate even if already exists")
    args = parser.parse_args()
    main(force=args.force)
