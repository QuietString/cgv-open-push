[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Failures = [System.Collections.Generic.List[string]]::new()

function Add-Failure {
    param([Parameter(Mandatory)][string]$Message)
    $script:Failures.Add($Message)
}

Push-Location $ProjectRoot

try {
    $RequiredFiles = @(
        '.gitignore',
        'AGENTS.md',
        'README.md',
        'LICENSE',
        'v1/Dockerfile',
        'v1/requirements.txt',
        'Docs/README.md',
        'Docs/Project/PROJECT_BRIEF.md',
        'Docs/Technical/ARCHITECTURE.md',
        'Docs/Technical/BUILD_TEST_RUN.md',
        'Docs/Status/IMPLEMENTATION_STATUS.md',
        'Docs/Status/KNOWN_ISSUES.md',
        'Docs/Work/ACTIVE.md',
        'Docs/Work/Tasks/README.md',
        'Docs/Work/Archive/README.md',
        'Docs/Decisions/README.md',
        'Docs/Templates/TASK_TEMPLATE.md',
        'Docs/Templates/ADR_TEMPLATE.md'
    )

    foreach ($RequiredFile in $RequiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot $RequiredFile) -PathType Leaf)) {
            Add-Failure "Missing required context or project file: $RequiredFile"
        }
    }

    $IgnoredSamples = @(
        '.env',
        '.env.local',
        'cgv-open-push.log',
        'v1/__pycache__/probe.pyc',
        '.pytest_cache/probe',
        '.venv/probe',
        '.idea/probe',
        '.vscode/probe'
    )

    foreach ($IgnoredSample in $IgnoredSamples) {
        & git check-ignore --quiet -- $IgnoredSample
        if ($LASTEXITCODE -ne 0) {
            Add-Failure "Expected secret/generated/local path is not ignored: $IgnoredSample"
        }
    }

    $TrackedSamples = @(
        'README.md',
        'AGENTS.md',
        'v1/cgv_open_push_main.py',
        'Docs/Status/IMPLEMENTATION_STATUS.md'
    )

    foreach ($TrackedSample in $TrackedSamples) {
        & git check-ignore --quiet -- $TrackedSample
        if ($LASTEXITCODE -eq 0) {
            Add-Failure "Expected project source/context path is ignored: $TrackedSample"
        }
    }

    if (Test-Path -LiteralPath (Join-Path $ProjectRoot 'AGENTS.md')) {
        $AgentsLength = (Get-Item -LiteralPath (Join-Path $ProjectRoot 'AGENTS.md')).Length
        if ($AgentsLength -gt 12288) {
            Add-Failure "AGENTS.md is $AgentsLength bytes; keep the bootstrap instructions at or below 12 KiB."
        }
    }

    $MarkdownFiles = @(
        Get-Item -LiteralPath (Join-Path $ProjectRoot 'AGENTS.md')
        Get-Item -LiteralPath (Join-Path $ProjectRoot 'README.md')
    ) + @(
        Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'Docs') -Recurse -File -Filter '*.md'
    )

    $LinkPattern = '(?<!\!)\[[^\]]+\]\((?<target>[^)]+)\)'

    foreach ($MarkdownFile in $MarkdownFiles) {
        $Text = Get-Content -Raw -LiteralPath $MarkdownFile.FullName

        foreach ($Match in [regex]::Matches($Text, $LinkPattern)) {
            $Target = $Match.Groups['target'].Value.Trim().Trim('<', '>')

            if ($Target -match '^(?:https?://|mailto:|#)') {
                continue
            }

            $PathPart = ($Target -split '#', 2)[0]
            if ([string]::IsNullOrWhiteSpace($PathPart)) {
                continue
            }

            $DecodedPath = [System.Uri]::UnescapeDataString($PathPart)
            if ([System.IO.Path]::IsPathRooted($DecodedPath)) {
                $ResolvedTarget = Join-Path $ProjectRoot $DecodedPath.TrimStart('/', '\')
            }
            else {
                $ResolvedTarget = Join-Path $MarkdownFile.DirectoryName $DecodedPath
            }

            if (-not (Test-Path -LiteralPath $ResolvedTarget)) {
                $RelativeSource = [System.IO.Path]::GetRelativePath($ProjectRoot, $MarkdownFile.FullName)
                Add-Failure "Broken local Markdown link in ${RelativeSource}: $Target"
            }
        }
    }

    $StatusFiles = @(
        'Docs/Project/PROJECT_BRIEF.md',
        'Docs/Technical/ARCHITECTURE.md',
        'Docs/Technical/BUILD_TEST_RUN.md',
        'Docs/Status/IMPLEMENTATION_STATUS.md',
        'Docs/Status/KNOWN_ISSUES.md',
        'Docs/Work/ACTIVE.md',
        'Docs/Decisions/README.md'
    )

    foreach ($StatusFile in $StatusFiles) {
        $StatusText = Get-Content -Raw -LiteralPath (Join-Path $ProjectRoot $StatusFile)
        if ($StatusText -notmatch '(?m)^> Status: ') {
            Add-Failure "Missing Status metadata in $StatusFile"
        }
        if ($StatusText -notmatch '(?m)^> Last verified: \d{4}-\d{2}-\d{2}$') {
            Add-Failure "Missing or invalid Last verified metadata in $StatusFile"
        }
    }
}
finally {
    Pop-Location
}

if ($Failures.Count -gt 0) {
    Write-Error ("Project context validation failed:`n- " + ($Failures -join "`n- "))
    exit 1
}

Write-Output 'Project context validation passed.'
Write-Output "Checked $($RequiredFiles.Count) required files, $($IgnoredSamples.Count) ignore rules, $($TrackedSamples.Count) tracked-path rules, and $($MarkdownFiles.Count) Markdown files."
