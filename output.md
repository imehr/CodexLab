# CodexLab — Lab Submission Output

## Task 1: Understand the Codebase

### Repository Overview

This is a minimal task manager API built with **FastAPI**. It stores tasks in a local JSON file and exposes endpoints for listing, creating, and completing tasks.

### Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | Defines HTTP API routes (`GET /tasks`, `GET /tasks/{id}`, `POST /tasks`, `POST /tasks/{id}/complete`, `GET /health`) |
| `app/schemas.py` | Pydantic models — `Task`, `TaskCreate`, `TaskStatus` (open/done), `TaskPriority` (low/medium/high) |
| `app/service.py` | Business logic — `list_tasks()`, `get_task()`, `create_task()`, `complete_task()` |
| `app/store.py` | JSON persistence — `load_tasks()`, `save_tasks()`, `next_task_id()` reading/writing `data/tasks.json` |
| `data/tasks.json` | Sample data: 4 tasks (3 open, 1 done) |

### GET /tasks Data Flow

1. `main.py:read_tasks()` receives optional `status` and `q` query parameters
2. Calls `service.py:list_tasks(status=status, q=q)`
3. `list_tasks()` calls `store.py:load_tasks()` which reads `data/tasks.json`
4. Iterates tasks, applying status filter and search filter
5. Returns filtered list to route handler
6. FastAPI serializes via Pydantic `Task` model

---

## Task 2: Find and Fix Bugs

### Bug A: Status Filtering is Broken

**Reproduction:**
```bash
curl http://127.0.0.1:8765/tasks          # Returns all 4 tasks
curl "http://127.0.0.1:8765/tasks?status=open"  # Returns [] (empty!)
```

**Root Cause:**
In `app/service.py` line 17, the comparison used the literal string `"status"` instead of the variable `status`:
```python
# BUG: compares against the literal string "status"
if status and task["status"] != "status":
    continue
```

Since no task has a status literally equal to the word "status", every task hits `continue` and is excluded.

**Fix:**
```python
if status and task["status"] != status:
    continue
```

**Verification:**
```
GET /tasks?status=open  → 3 tasks (IDs: 1, 3, 4)
GET /tasks?status=done  → 1 task  (ID: 2)
```

### Bug B: Completing a Task Does Not Persist

**Reproduction:**
```bash
curl -X POST http://127.0.0.1:8765/tasks/1/complete  # Response shows status=done ✓
curl http://127.0.0.1:8765/tasks/1                     # Still shows status=open ✗
```

**Root Cause:**
In `app/service.py`, `complete_task()` created a shallow copy with `dict(task)`, modified the copy, and returned it — but never updated the original task in the list or called `save_tasks()`. The response looked correct, but the disk never saw the change.

```python
# BUG: modifies a copy, never saves
updated_task = dict(task)
updated_task["status"] = "done"
updated_task["completed_at"] = datetime.now(timezone.utc).isoformat()
return updated_task  # original list unchanged, save_tasks() never called
```

**Fix:**
Mutate the task in-place and persist:
```python
for i, task in enumerate(tasks):
    if task["id"] == task_id:
        task["status"] = "done"
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
        save_tasks(tasks)
        return task
```

**Verification:**
```
POST /tasks/3/complete  → status=done, completed_at=2026-04-01T23:34:33.339880Z
GET  /tasks/3           → status=done, completed_at=2026-04-01T23:34:33.339880Z ✓ (persisted)
```

---

## Task 3: Add Search Support (q parameter)

**Requirement:** Add case-insensitive text search across `title` and `description` fields via the `q` query parameter on `GET /tasks`. Must compose with the existing `status` filter.

**Implementation:**
The route in `main.py` already accepted `q` and passed it to `list_tasks()`. Added filtering logic in `service.py`:

```python
if q:
    query = q.lower()
    if query not in task["title"].lower() and query not in task["description"].lower():
        continue
```

Placed after the status filter so both compose naturally — a task must pass both checks to be included.

**Verification:**
```
GET /tasks?q=launch              → 1 task: "Write launch recap" (matched in title)
GET /tasks?q=report              → 1 task: "Archive weekly report" (matched in title)
GET /tasks?status=open&q=plan    → 1 task: "Plan workshop agenda" (status=open AND "plan" in title)
```

---

## Task 4: Clean Commit

### Pre-commit Check
- `data/tasks.json` was modified by runtime testing (completing task 3 during verification)
- Restored with `git checkout -- data/tasks.json` before committing
- Final diff is scoped to `app/service.py` only (1 file changed, 11 insertions, 13 deletions)

### Diff
```diff
diff --git a/app/service.py b/app/service.py
index 8022b93..91777b2 100644
--- a/app/service.py
+++ b/app/service.py
@@ -12,13 +12,14 @@ def list_tasks(status: str | None = None, q: str | None = None) -> list[dict[str
     filtered: list[dict[str, Any]] = []

     for task in tasks:
-        # Instructor note: intentional bug for the lab.
-        # This uses the literal string "status" instead of the query parameter value.
-        if status and task["status"] != "status":
+        if status and task["status"] != status:
             continue

-        # Instructor note: partial feature for the lab.
-        # The route already accepts `q`, but search is not implemented yet.
+        if q:
+            query = q.lower()
+            if query not in task["title"].lower() and query not in task["description"].lower():
+                continue
+
         filtered.append(task)

     return filtered
@@ -51,14 +52,11 @@ def complete_task(task_id: int) -> dict[str, Any] | None:
     """Mark a task as completed."""
     tasks = load_tasks()

-    for task in tasks:
+    for i, task in enumerate(tasks):
         if task["id"] == task_id:
-            updated_task = dict(task)
-            updated_task["status"] = "done"
-            updated_task["completed_at"] = datetime.now(timezone.utc).isoformat()
-
-            # Instructor note: intentional bug for the lab.
-            # The updated task is returned, but the stored list is never updated or saved.
-            return updated_task
+            task["status"] = "done"
+            task["completed_at"] = datetime.now(timezone.utc).isoformat()
+            save_tasks(tasks)
+            return task

     return None
```

### Git Commands
```bash
git checkout -b codex/lab-fixes
git add app/service.py
git commit -m "Fix task bugs and add search filter"
git push origin codex/lab-fixes
```

### Branch
`codex/lab-fixes` pushed to `https://github.com/imehr/CodexLab`

---

## Final Verification Checklist

| Check | Result |
|-------|--------|
| `GET /tasks?status=open` returns only open tasks | ✓ 3 tasks (IDs 1, 3, 4) |
| `GET /tasks?status=done` returns only done tasks | ✓ 1 task (ID 2) |
| `POST /tasks/3/complete` persists | ✓ status=done, completed_at set |
| `GET /tasks/3` confirms persistence | ✓ status=done, completed_at non-null |
| `GET /tasks?q=launch` searches correctly | ✓ 1 task matched |
| `GET /tasks?status=open&q=plan` composes filters | ✓ Correct results |
| `data/tasks.json` restored before commit | ✓ Only code changes in diff |
| Final diff is reviewable and scoped | ✓ 1 file, 11 insertions, 13 deletions |

---

## Repository URL

https://github.com/imehr/CodexLab

Branch: `codex/lab-fixes`
