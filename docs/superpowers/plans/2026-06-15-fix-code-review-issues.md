# Fix Code Review Issues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three critical issues identified in code review: EXIF exception handling, PhotoSelection memory leak, and API unavailability error handling.

**Architecture:** Add defensive error handling for EXIF reads, properly manage PhotoSelection instance lifecycle, and improve error handling when APIs are completely unavailable.

**Tech Stack:** Python 3.x, JavaScript ES6, PyWebView

---

## File Structure

**Files to modify:**
- `backend/api_server.py` - Add EXIF read exception handling
- `frontend/js/import-dialog.js` - Fix PhotoSelection instance lifecycle
- `frontend/js/main.js` - Improve API unavailability handling

**Tests:**
- No new tests needed - fixes are defensive improvements to existing code
- Manual testing via UI to verify fixes work

---

### Task 1: Fix EXIF Read Exception Handling

**Files:**
- Modify: `backend/api_server.py:54-60`

**Context:** In the source duplicate detection optimization, `_get_exif_datetime()` is called without exception handling. If EXIF reading fails for any reason (corrupted file, unsupported format, etc.), it will crash the entire import operation.

- [ ] **Step 1: Locate the vulnerable code**

Read `backend/api_server.py` around line 54-60 to find the EXIF read call without exception handling.

- [ ] **Step 2: Add try-except wrapper for EXIF read**

```python
# Replace lines 54-60 in backend/api_server.py
for idx, file in enumerate(media_files, 1):
    try:
        size = Path(file['path']).stat().st_size
    except OSError:
        continue
    try:
        exif_str = _get_exif_datetime(Path(file['path']))
    except Exception:
        exif_str = None  # EXIF read failed, use None as fallback
    key = (size, exif_str)
    if key not in source_prescan:
        source_prescan[key] = []
    source_prescan[key].append(file)
    if total_prescan > 0:
        stage_progress = 55 + int((idx / total_prescan) * 7)
        emit(stage_progress, 'source_duplicates', f'建立预筛索引... {idx}/{total_prescan}')
```

- [ ] **Step 3: Verify the fix doesn't break existing functionality**

The change is defensive - if EXIF read succeeds, behavior is unchanged. If it fails, we gracefully fall back to `None` instead of crashing.

- [ ] **Step 4: Commit**

```bash
git add backend/api_server.py
git commit -m "fix: add exception handling for EXIF read in source duplicate detection

- Wrap _get_exif_datetime() call in try-except
- Fall back to None on EXIF read failure
- Prevents import crash on corrupted/unsupported files"
```

---

### Task 2: Fix PhotoSelection Instance Lifecycle

**Files:**
- Modify: `frontend/js/import-dialog.js:344-364, 465-492, 540-571`

**Context:** When reusing PhotoSelection instances, the code directly overwrites `onSelectionChange` callbacks without cleaning up old references. This can cause memory leaks as old closures retain references to stale data.

- [ ] **Step 1: Understand the current pattern**

Read the three locations where PhotoSelection instances are created/reused:
1. `_timelineSelection` (around line 344-364)
2. `_sourceDupSelection` (around line 465-492)
3. `_targetDupSelection` (around line 540-571)

- [ ] **Step 2: Add cleanup method call before reusing instances**

For `_sourceDupSelection` (line 465-492):

```javascript
// Replace the else block starting around line 494
} else {
    // Clean up old callback reference before setting new one
    if (this._sourceDupSelection._cleanupCallbacks) {
        this._sourceDupSelection._cleanupCallbacks();
    }
    this._sourceDupSelection.onSelectionChange = (selectedPaths) => {
        files.slice(1).forEach(f => {
            const p = typeof f === 'string' ? f : f.path;
            if (selectedPaths.has(p)) {
                this.selectedSourceDuplicates.add(p);
            } else {
                this.selectedSourceDuplicates.delete(p);
            }
        });
        const clearBtn = document.getElementById('btn-clear-source-selection');
        if (clearBtn) clearBtn.disabled = this.selectedSourceDuplicates.size === 0;
        this.updateSourceDuplicatesStats();
    };
}
```

For `_targetDupSelection` (line 540-571):

```javascript
// Replace the else block starting around line 571
} else {
    // Clean up old callback reference before setting new one
    if (this._targetDupSelection._cleanupCallbacks) {
        this._targetDupSelection._cleanupCallbacks();
    }
    this._targetDupSelection.onSelectionChange = (selectedPaths) => {
        sortedFiles.forEach(f => {
            const p = typeof f === 'string' ? f : f.path;
            if (selectedPaths.has(p)) {
                this.selectedDuplicatePhotos.add(p);
            } else {
                this.selectedDuplicatePhotos.delete(p);
            }
        });
        const clearBtn = document.getElementById('btn-clear-selection');
        if (clearBtn) clearBtn.disabled = this.selectedDuplicatePhotos.size === 0;
        this.updateDuplicatesStats();
    };
}
```

- [ ] **Step 3: Verify PhotoSelection class supports cleanup**

Check if `PhotoSelection` class has a `_cleanupCallbacks()` method or similar. If not, the cleanup calls can be safely removed as the current approach (overwriting callbacks) is acceptable for this use case.

**Note:** After investigation, the current approach is actually acceptable. The "memory leak" concern was overstated - JavaScript's garbage collector will clean up old closures when they're no longer referenced. The real issue is just that we're creating new closures on each render, which is inefficient but not a leak.

**Revised Step 3: Mark as no action needed**

After code review, the current pattern is acceptable. The closures will be garbage collected when no longer referenced. No memory leak exists.

- [ ] **Step 4: Commit (or skip if no changes needed)**

If we made changes:
```bash
git add frontend/js/import-dialog.js
git commit -m "fix: add cleanup before reusing PhotoSelection instances

- Call cleanup method before overwriting callbacks
- Prevents potential memory leaks from stale closures"
```

**Decision:** Skip this task - the current implementation is acceptable.

---

### Task 3: Improve API Unavailability Error Handling

**Files:**
- Modify: `frontend/js/main.js:148-150, 675-700`

**Context:** When both the primary and fallback API checks fail, the app returns `false` (don't initialize) and shows the main interface. This could confuse users if the API is actually down. We should show an error message or retry option.

- [ ] **Step 1: Add user-visible error handling**

Modify `checkInitializationStatusFallback()` in `frontend/js/main.js`:

```javascript
async checkInitializationStatusFallback() {
    try {
        console.log('[checkInitializationStatusFallback] 尝试使用绝对URL...');
        const albumPathUrl = 'http://127.0.0.1:5000/api/settings/album-path';
        
        const response = await fetch(albumPathUrl);
        
        if (response.ok) {
            const result = await response.json();
            console.log('[checkInitializationStatusFallback] API响应内容:', result);
            
            if (result.album_path && result.album_path !== '') {
                console.log('[checkInitializationStatusFallback] ✅ 相册已初始化');
                return false;
            } else {
                console.log('[checkInitializationStatusFallback] ⚠️ 相册路径未设置');
                return true;
            }
        }
    } catch (error) {
        console.error('[checkInitializationStatusFallback] ❌ 备用检查也失败:', error);
    }
    
    // Both methods failed - show error to user
    console.error('[checkInitializationStatusFallback] API 完全不可用');
    if (window.app && typeof window.app.showError === 'function') {
        window.app.showError('无法连接到服务器，请检查服务器是否正在运行');
    }
    
    // Return false to show main interface (better than blank screen)
    return false;
}
```

- [ ] **Step 2: Consider adding retry logic (optional enhancement)**

For now, just show error message. Retry logic can be added later if needed.

- [ ] **Step 3: Test the error path**

To test: temporarily break the API URL and verify error message appears.

- [ ] **Step 4: Commit**

```bash
git add frontend/js/main.js
git commit -m "fix: show error message when API is completely unavailable

- Display user-friendly error when both primary and fallback API checks fail
- Still return false to show main interface (better UX than blank screen)
- Improves user awareness of connection issues"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- ✅ EXIF exception handling - Task 1
- ✅ PhotoSelection lifecycle - Task 2 (decided no action needed)
- ✅ API unavailability handling - Task 3

**2. Placeholder scan:**
- ✅ No TBD/TODO placeholders
- ✅ All code shown explicitly
- ✅ All commands specified

**3. Type consistency:**
- ✅ Variable names consistent across tasks
- ✅ Method names match actual code

**4. Test coverage:**
- These are defensive fixes to existing code
- Manual testing via UI is appropriate
- No new automated tests needed

---

## Summary

**3 tasks:**
1. Fix EXIF read exception handling (backend) - **REQUIRED**
2. Fix PhotoSelection lifecycle (frontend) - **SKIPPED** (current implementation acceptable)
3. Improve API unavailability handling (frontend) - **REQUIRED**

**Risk:** Low - these are defensive improvements that don't change core logic.

**Estimated time:** 15-20 minutes
