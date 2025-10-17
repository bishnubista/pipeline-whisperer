---
name: fix-pr
description: MUST BE USED after CodeRabbit reviews. Systematically addresses all PR review comments with incremental validation and atomic commits. Use proactively when user mentions CodeRabbit feedback or PR comments.
tools: Read, Edit, Bash, TodoWrite
---

# CodeRabbit PR Fixer

**Core Principles:**

- ONE fix at a time with validation
- NEVER commit if build broken
- NEVER skip validation
- Single atomic commit at end

---

## Workflow

### Step 1: Identify PR

```bash
# If no PR number provided, use current branch
gh pr view --json number,title

# If PR number provided (e.g., /fix-pr 42)
gh pr checkout 42 && gh pr view --json number,title
```

---

### Step 2: Fetch CodeRabbit Comments

```bash
gh pr view --json comments --jq '.comments[] | select(.author.login == "coderabbitai") | {body: .body, createdAt: .createdAt}'
```

---

### Step 3: Categorize & Create Todo List

**Severity levels:**

- 🔴 **Critical**: Security, crashes, data corruption, blocking bugs
- 🟡 **Major**: Performance issues, architecture problems, test failures
- 🟢 **Minor**: Style violations, docs, nitpicks

**Create TodoWrite list:**

```json
{
  "todos": [
    {
      "content": "🔴 Fix [issue] in file:line",
      "activeForm": "🔴 Fixing [issue]",
      "status": "pending"
    },
    {
      "content": "🟡 Fix [issue] in file:line",
      "activeForm": "🟡 Fixing [issue]",
      "status": "pending"
    }
  ]
}
```

---

### Step 4: Fix Issues Incrementally

**For EACH issue (Critical → Major → Minor):**

#### 4.1 Update Todo → in_progress

#### 4.2 Read Affected Code

- Use Read tool on file
- Understand context (5-10 lines around change)

#### 4.3 Apply Fix

- Use Edit tool for precise changes
- Follow CodeRabbit suggestion if reasonable

#### 4.4 Validate (REQUIRED)

**Auto-detect project and run validation:**

```bash
# Auto-detection script
if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
  # Python
  if command -v uv &> /dev/null && [ -f "pyproject.toml" ]; then
    uv run pytest tests/ -v 2>&1 | head -50
  else
    pytest tests/ -v 2>&1 | head -50
  fi
elif [ -f "package.json" ]; then
  # Node.js
  [ -f "pnpm-lock.yaml" ] && pnpm build && pnpm test || npm run build && npm test
elif [ -f "Cargo.toml" ]; then
  cargo build && cargo test
elif [ -f "go.mod" ]; then
  go build ./... && go test ./...
elif [ -f "build.sh" ]; then
  ./build.sh
else
  echo "⚠️ No recognized project type"
  exit 1
fi
```

**If build FAILS:**

1. Revert change immediately
2. Try alternative approach (max 2 attempts)
3. Mark as "Unable to fix" with reason

**If build PASSES:**

1. Update TodoWrite → completed
2. Continue to next issue

---

### Step 5: Final Validation

After all fixes:

```bash
# Run full test suite based on project type
# Ensure all tests pass, 0 errors
```

---

### Step 6: Commit and Push

```bash
git add -A

# Use <<'EOF' with quotes to prevent variable expansion
git commit -m "$(cat <<'EOF'
Fix CodeRabbit review comments

## Critical Issues Fixed (N)
- [Issue]: [Solution]

## Major Issues Fixed (N)
- [Issue]: [Solution]

## Minor Issues Fixed (N)
- [Issue]: [Solution]

## Unable to Fix (N)
- [Issue]: [Reason and recommendation]

## Validation
- Build: ✅ Passing
- Tests: ✅ N/N passing

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

git push
```

---

### Step 7: Report Summary

```
## CodeRabbit PR Fixes Complete ✅

### Issues Addressed: X/Y

#### Critical (🔴): X/N
✅ [Issue]: Fixed by [solution]
❌ [Issue]: Unable to fix - [reason]

#### Major (🟡): X/N
✅ [Issue]: Fixed by [solution]

#### Minor (🟢): X/N
✅ [Issue]: Fixed by [solution]

### Validation
- Build: ✅ Passing
- Tests: ✅ N/N passing

### Commit
SHA: [hash]
Branch: [name]

### Next Steps
1. Wait for CodeRabbit auto-review (2-5 min)
2. Address any new comments if needed
3. Merge when approved
```

---

## Error Handling

### No PR found

```
❌ No active PR found

Options:
1. gh pr checkout [PR-NUMBER], then /fix-pr
2. /fix-pr [PR-NUMBER]
```

### No CodeRabbit comments

```
✅ No CodeRabbit comments found

Possible reasons:
- CodeRabbit hasn't reviewed yet
- All comments already resolved
- CodeRabbit not configured
```

### Build fails after fix

```
❌ Build failed after fix: [Issue]

Actions:
1. Reverted change
2. Build restored

Recommendation: Create separate issue/PR for this fix
```

---

## Key Rules

1. **One Fix at a Time** - Each fix validated independently
2. **Build Must Pass** - Never commit broken code
3. **Don't Over-Fix** - Skip minor issues if time-consuming
4. **Document Blockers** - Explain why fixes failed with clear reasoning
5. **Single Commit** - All fixes in one atomic commit

---

## Success Criteria

- ✅ All Critical issues fixed or documented
- ✅ All Major issues addressed (fixed or reasoned skip)
- ✅ Minor issues fixed where reasonable
- ✅ Build passing with 0 errors
- ✅ All tests passing
- ✅ Single commit with comprehensive message
- ✅ Changes pushed to remote

**Typical completion time**: 5-15 minutes
