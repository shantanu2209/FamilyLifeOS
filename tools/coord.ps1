<#
.SYNOPSIS
  Coordination commits from an agent's own worktree (coordination/README.md section 5).

.DESCRIPTION
  Each agent works in its own git worktree, which cannot check out `main` because the
  founder's folder has it. Coordination files (coordination/STATUS.md and
  coordination/inbox/**) are therefore edited on a detached copy of origin/main and
  pushed straight to main.

    tools\coord.ps1 begin
        Requires a clean working tree. Fetches and detaches the worktree at origin/main,
        so STATUS and the inboxes are current and safe to edit.

    tools\coord.ps1 push -Message "coord: gemini status, message to claude about #18"
        Stages coordination/STATUS.md and coordination/inbox only, refuses if anything
        else is modified, commits, and pushes HEAD to main (one rebase retry if main moved).

  Typical session: `begin` -> edit STATUS / inbox -> `push` -> `git switch -c agent-<name>/issue-<n>`
  -> work, commit by path, push branch, open PR -> `begin` -> update STATUS, message the
  reviewer -> `push`.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('begin', 'push')]
    [string]$Command,

    [string]$Message
)

$ErrorActionPreference = 'Continue'

function Fail([string]$text) {
    Write-Host "coord: $text" -ForegroundColor Red
    exit 1
}

$top = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { Fail 'not inside a git working tree' }
Set-Location $top

# In the main folder .git is a directory; in a linked worktree it is a file.
$isMainFolder = Test-Path (Join-Path $top '.git') -PathType Container

if ($Command -eq 'begin' -and $isMainFolder) {
    # The founder's folder stays on main; just bring it up to date.
    git pull --quiet --rebase origin main
    if ($LASTEXITCODE -ne 0) { Fail 'git pull --rebase failed in the main folder' }
    Write-Host "coord: main folder updated to $(git rev-parse --short HEAD); it stays on main"
    exit 0
}

if ($Command -eq 'begin') {
    $dirty = git status --porcelain
    if ($dirty) { Fail "working tree is not clean; commit or stash your own work first:`n$($dirty -join "`n")" }
    git fetch --quiet origin
    if ($LASTEXITCODE -ne 0) { Fail 'git fetch failed' }
    git switch --quiet --detach origin/main
    if ($LASTEXITCODE -ne 0) { Fail 'could not detach at origin/main' }
    Write-Host "coord: at origin/main ($(git rev-parse --short HEAD)). Edit coordination/STATUS.md (your section only) and coordination/inbox/, then run: tools\coord.ps1 push -Message `"coord: ...`""
    exit 0
}

# push
if (-not $Message) { Fail 'push needs -Message "coord: ..."' }
if (-not $Message.StartsWith('coord:')) { Fail 'the commit subject must start with "coord:"' }

$branch = git rev-parse --abbrev-ref HEAD
if ($branch -ne 'HEAD' -and $branch -ne 'main') {
    Fail "you are on branch '$branch'. Coordination commits are made on a detached origin/main: push your branch, then run tools\coord.ps1 begin"
}

$outside = git status --porcelain | Where-Object {
    $path = $_.Substring(3).Trim('"')
    -not ($path -eq 'coordination/STATUS.md' -or $path.StartsWith('coordination/inbox/'))
}
if ($outside) { Fail "changes outside coordination/STATUS.md and coordination/inbox/ are present; they need a branch and a PR:`n$($outside -join "`n")" }

git add -- coordination/STATUS.md coordination/inbox
$staged = git diff --cached --name-only
if (-not $staged) { Fail 'nothing to commit under coordination/' }

git commit --quiet -m $Message
if ($LASTEXITCODE -ne 0) { Fail 'git commit failed' }

git push --quiet origin HEAD:main
if ($LASTEXITCODE -ne 0) {
    Write-Host 'coord: main moved; rebasing once and retrying'
    git fetch --quiet origin
    git rebase --quiet origin/main
    if ($LASTEXITCODE -ne 0) {
        git rebase --abort
        Fail 'rebase onto origin/main hit a conflict (someone edited the same lines). Run tools\coord.ps1 begin and redo your edit.'
    }
    git push --quiet origin HEAD:main
    if ($LASTEXITCODE -ne 0) { Fail 'push failed twice; tell the founder' }
}
Write-Host "coord: pushed $(git rev-parse --short HEAD) to main: $Message"
exit 0
