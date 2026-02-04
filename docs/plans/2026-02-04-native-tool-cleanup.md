# Native Tool Calling Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove unused legacy streaming/JSON envelope artifacts and keep cognition exports clean after native tool calling migration.

**Architecture:** Delete dead modules (`response_classifier`, `stream_buffer`) and their exports; confirm no remaining references via ripgrep. No behavior change beyond removal of unused code paths.

**Tech Stack:** Python 3.12, ripgrep, pytest (if needed)

### Task 1: Remove unused cognition stream/response utilities

**Files:**
- Delete: `src/aeiva/cognition/response_classifier.py`
- Delete: `src/aeiva/cognition/stream_buffer.py`
- Modify: `src/aeiva/cognition/__init__.py`

**Step 1: Verify no active references**

Run: `rg "ResponseClassifier|StreamBuffer" src/`  
Expected: references only in the two files and `__init__.py`

**Step 2: Delete dead modules**

Run: `rm src/aeiva/cognition/response_classifier.py src/aeiva/cognition/stream_buffer.py`

**Step 3: Update cognition exports**

Edit `src/aeiva/cognition/__init__.py` to remove `ResponseClassifier` and `StreamBuffer` from imports/`__all__`.

**Step 4: Sanity check**

Run: `rg "ResponseClassifier|StreamBuffer" src/`  
Expected: no matches

**Step 5: Optional quick test**

Run: `pytest tests/llm/test_native_tool_loop.py -v`  
Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add src/aeiva/cognition/__init__.py
# (deleted files will be staged automatically)
git commit -m "chore: remove unused cognition stream utilities"
```
