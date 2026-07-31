# discover-target-project.ps1 - pwsh parity port of discover-target-project.sh
# Universal detection of plugin_root and memory_path.
# Product specifics are declarative: profiles/<id>.md (ONE fenced ```json block = SoT of markers).
# Core detects: marker -> profiles loop -> self-t800 -> generic-plugin -> workspace-cursor.
# Usage: pwsh scripts/discover-target-project.ps1 [--workspace PATH] [--plugin-root PATH] [WORKSPACE]

param(
    [Parameter(Position = 0)]
    [string]$Workspace = ".",
    [string]$PluginRoot = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest = @()
)

# Bash-style flag parity: --workspace X, --plugin-root X, bare positional = workspace
$i = 0
while ($i -lt $Rest.Count) {
    switch ($Rest[$i]) {
        "--workspace" {
            if ($i + 1 -lt $Rest.Count) { $Workspace = $Rest[$i + 1] }
            $i += 2
        }
        "--plugin-root" {
            if ($i + 1 -lt $Rest.Count) { $PluginRoot = $Rest[$i + 1] }
            $i += 2
        }
        default {
            if ($Rest[$i] -notmatch "^-") { $Workspace = $Rest[$i] }
            $i += 1
        }
    }
}

$ErrorActionPreference = "Continue"

$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
$ProfilesDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\profiles"))

$NeedsUserQuestion = $false
$Profile = "unknown"
$ProfileDeclared = $false
$PluginRootOut = ""
$MemoryDir = ""
$MemoryPath = ""
$Slug = ""
$ReleaseHandoff = $null
$KnowledgeVaultPath = $null
$ArtifactSurface = "cursor-workspace"
$PluginRootSource = $null
$WriteAllowed = $true
$Adapter = $null

# --- Discovery profiles (profiles/<id>.md, one fenced json block) ------------

function Get-ProfileBlock([string]$Id) {
    $f = Join-Path $ProfilesDir "$Id.md"
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { return $null }
    $inBlock = $false
    $sb = New-Object System.Text.StringBuilder
    foreach ($line in (Get-Content -LiteralPath $f -Encoding utf8)) {
        if ($line -match '^```json\s*$') { $inBlock = $true; continue }
        if ($line -match '^```\s*$' -and $inBlock) { break }
        if ($inBlock) { [void]$sb.AppendLine($line) }
    }
    $block = $sb.ToString().Trim()
    if ($block.Length -gt 0) { return $block }
    return $null
}

# Match workspace against profiles/*.md by markers {require[], any_of[], memory_dir_present}
function Match-Profiles([string]$Ws) {
    $files = Get-ChildItem -Path $ProfilesDir -Filter "*.md" -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        $pid = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
        $block = Get-ProfileBlock $pid
        if (-not $block) { continue }
        try { $d = $block | ConvertFrom-Json } catch { continue }
        $m = $d.markers
        $okAll = $true
        if ($m -and $m.require) {
            foreach ($r in @($m.require)) {
                if (-not (Test-Path -LiteralPath (Join-Path $Ws $r))) { $okAll = $false; break }
            }
        }
        if (-not $okAll) { continue }
        if ($m -and $m.any_of -and @($m.any_of).Count -gt 0) {
            $anyOk = $false
            foreach ($a in @($m.any_of)) {
                if (Test-Path -LiteralPath (Join-Path $Ws $a)) { $anyOk = $true; break }
            }
            if (-not $anyOk) { continue }
        }
        if ($m -and $m.memory_dir_present) {
            if (-not (Test-Path -LiteralPath (Join-Path $Ws $m.memory_dir_present) -PathType Container)) { continue }
        }
        if (-not $d.id) {
            $d | Add-Member -NotePropertyName id -NotePropertyValue $pid -Force
        }
        return $d
    }
    return $null
}

function Expand-Tilde([string]$p) {
    if ($p.StartsWith("~")) { return ($env:USERPROFILE + $p.Substring(1)) }
    return $p
}

function Read-EnvFileValue([string]$EnvFile, [string]$EnvKey) {
    $path = Expand-Tilde $EnvFile
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return "" }
    $pattern = "^" + [regex]::Escape($EnvKey) + "=(.*)$"
    $value = ""
    foreach ($line in (Get-Content -LiteralPath $path -Encoding utf8)) {
        if ($line -match $pattern) { $value = $Matches[1] }
    }
    return $value.Trim()
}

# plugin_root from profile: env_key (grep env_file) -> readonly_fallback -> workspace self
function Resolve-ProfilePluginRoot($ProfileObj) {
    $pr = $ProfileObj.plugin_root
    $envKey = if ($pr -and $pr.env_key) { [string]$pr.env_key } else { "" }
    $envFile = if ($pr -and $pr.env_file) { [string]$pr.env_file } else { "" }
    $fallback = if ($pr -and $pr.readonly_fallback) { [string]$pr.readonly_fallback } else { "" }
    if ($envKey.Length -gt 0) {
        $val = [Environment]::GetEnvironmentVariable($envKey)
        if (-not $val) { $val = "" }
        if ($val.Length -eq 0 -and $envFile.Length -gt 0) {
            $val = Read-EnvFileValue $envFile $envKey
        }
        if ($val.Length -gt 0 -and (Test-Path -LiteralPath $val -PathType Container)) {
            $script:PluginRootOut = (Resolve-Path -LiteralPath $val).Path
            $script:PluginRootSource = "env"
            $script:WriteAllowed = $true
            return $true
        }
    }
    if ($fallback.Length -gt 0) {
        $fb = Expand-Tilde $fallback
        if (Test-Path -LiteralPath $fb -PathType Container) {
            # Readonly fallback for reading contracts - not a write destination
            $script:PluginRootOut = (Resolve-Path -LiteralPath $fb).Path
            $script:PluginRootSource = "installed_readonly"
            $script:WriteAllowed = $false
            $script:NeedsUserQuestion = $true
            return $true
        }
    }
    if ($envKey.Length -eq 0 -and $fallback.Length -eq 0) {
        # "workspace self" strategy: profile without env/fallback - plugin is the workspace itself
        $script:PluginRootOut = $Workspace
        $script:PluginRootSource = "workspace"
        $script:WriteAllowed = $true
        return $true
    }
    return $false
}

function Resolve-Absolute([string]$Base, [string]$PathValue) {
    if ([System.IO.Path]::IsPathRooted($PathValue)) { return $PathValue }
    return [System.IO.Path]::GetFullPath((Join-Path $Base $PathValue))
}

# 1) project-memory.marker.json (walk up)
$search = $Workspace
while ($search) {
    $marker = Join-Path $search "project-memory.marker.json"
    if (Test-Path -LiteralPath $marker -PathType Leaf) {
        $mk = $null
        try { $mk = (Get-Content -LiteralPath $marker -Raw -Encoding utf8 | ConvertFrom-Json) } catch {}
        if ($mk) {
            if ($mk.slug) { $Slug = [string]$mk.slug }
            if ($mk.memory_dir) { $MemoryDir = [string]$mk.memory_dir }
            $pr = "."
            if ($mk.plugin_root) { $pr = [string]$mk.plugin_root }
            if ($mk.release_handoff) { $ReleaseHandoff = [string]$mk.release_handoff }
            if ($mk.knowledge_vault_path -and ([string]$mk.knowledge_vault_path).Trim().Length -gt 0) {
                $KnowledgeVaultPath = Resolve-Absolute $search ([string]$mk.knowledge_vault_path)
            }
            if ($pr -eq ".") {
                $PluginRootOut = $search
            } else {
                $PluginRootOut = (Resolve-Path -LiteralPath (Join-Path $search $pr)).Path
            }
            $MemoryPath = Join-Path $search $MemoryDir
            # Product override inside marker: marker + manifest memory + .cursor-plugin + product gates
            # -> profile from profiles/ (adapter read from matched profile, no hardcode)
            if ((Test-Path -LiteralPath (Join-Path $search "plugin-memory") -PathType Container) -and
                (Test-Path -LiteralPath (Join-Path $search ".cursor-plugin\plugin.json") -PathType Leaf)) {
                $mo = Match-Profiles $search
                if ($mo) {
                    if ($mo.id) { $Profile = [string]$mo.id }
                    $ProfileDeclared = $true
                    $ArtifactSurface = if ($mo.artifact_surface) { [string]$mo.artifact_surface } else { "cursor-plugin" }
                    if ($Slug.Length -eq 0 -and $mo.slug) { $Slug = [string]$mo.slug }
                    if ($null -eq $ReleaseHandoff -and $mo.release_handoff) {
                        $ReleaseHandoff = [string]$mo.release_handoff
                    }
                } else {
                    $Profile = "marker"
                }
            } else {
                $Profile = "marker"
            }
        }
        break
    }
    $parent = Split-Path -Parent $search
    if (-not $parent -or $parent -eq $search) { break }
    $search = $parent
}

# 2) Profiles loop: product profiles from profiles/*.md (declared markers)
if ($Profile -eq "unknown") {
    $pm = Match-Profiles $Workspace
    if ($pm) {
        if ($pm.id) { $Profile = [string]$pm.id }
        $ProfileDeclared = $true
        if ($pm.memory_dir) { $MemoryDir = [string]$pm.memory_dir }
        $MemoryPath = Join-Path $Workspace $MemoryDir
        if ($pm.slug) { $Slug = [string]$pm.slug }
        $ArtifactSurface = if ($pm.artifact_surface) { [string]$pm.artifact_surface } else { "cursor-plugin" }
        if ($pm.release_handoff) { $ReleaseHandoff = [string]$pm.release_handoff }
        [void](Resolve-ProfilePluginRoot $pm)
        # Optional KVP from marker without overriding profile (if step 1 did not fire)
        $wsMarker = Join-Path $Workspace "project-memory.marker.json"
        if ($null -eq $KnowledgeVaultPath -and (Test-Path -LiteralPath $wsMarker -PathType Leaf)) {
            try {
                $mk2 = (Get-Content -LiteralPath $wsMarker -Raw -Encoding utf8 | ConvertFrom-Json)
                if ($mk2.knowledge_vault_path -and ([string]$mk2.knowledge_vault_path).Trim().Length -gt 0) {
                    $KnowledgeVaultPath = Resolve-Absolute $Workspace ([string]$mk2.knowledge_vault_path)
                }
            } catch {}
        }
        # never_canonical from profile is informational: sibling paths are never canonical,
        # discovery does not guess them (plugin_root only env / readonly fallback / workspace self).
    }
}

# 3) Self T-800
if ($MemoryDir.Length -eq 0 -and
    (Test-Path -LiteralPath (Join-Path $Workspace "t-800-memory") -PathType Container) -and
    (Test-Path -LiteralPath (Join-Path $Workspace "t-800-agent\.cursor-plugin") -PathType Container)) {
    $Profile = "self-t800"
    $PluginRootOut = Join-Path $Workspace "t-800-agent"
    $ArtifactSurface = "cursor-plugin"
    $MemoryDir = "t-800-memory"
    $MemoryPath = Join-Path $Workspace "t-800-memory"
    $Slug = "t-800-agent"
}

# 4) Generic: .cursor-plugin + {name}-memory
$wsPluginJson = Join-Path $Workspace ".cursor-plugin\plugin.json"
if ($PluginRootOut.Length -eq 0 -and (Test-Path -LiteralPath $wsPluginJson -PathType Leaf)) {
    $pname = "plugin"
    try {
        $pj = (Get-Content -LiteralPath $wsPluginJson -Raw -Encoding utf8 | ConvertFrom-Json)
        if ($pj.name) { $pname = [string]$pj.name }
    } catch {}
    $Slug = $pname
    $PluginRootOut = $Workspace
    $candidate = "$pname-memory"
    $Profile = "generic-plugin"
    $ArtifactSurface = "cursor-plugin"
    $MemoryDir = $candidate
    $MemoryPath = Join-Path $Workspace $candidate
    if (-not (Test-Path -LiteralPath $MemoryPath -PathType Container)) {
        $NeedsUserQuestion = $true
    }
}

# 5) t-800-agent inside workspace only
if ($PluginRootOut.Length -eq 0 -and
    (Test-Path -LiteralPath (Join-Path $Workspace "t-800-agent\.cursor-plugin") -PathType Container)) {
    $Profile = "self-t800"
    $PluginRootOut = Join-Path $Workspace "t-800-agent"
    $ArtifactSurface = "cursor-plugin"
    if (Test-Path -LiteralPath (Join-Path $Workspace "t-800-memory") -PathType Container) {
        $MemoryDir = "t-800-memory"
        $MemoryPath = Join-Path $Workspace "t-800-memory"
    } elseif (Test-Path -LiteralPath (Join-Path $Workspace "t-800-agent\t-800-memory") -PathType Container) {
        $MemoryDir = "t-800-memory"
        $MemoryPath = Join-Path $Workspace "t-800-agent\t-800-memory"
    } else {
        $MemoryDir = "t-800-memory"
        $MemoryPath = Join-Path $Workspace "t-800-memory"
        $NeedsUserQuestion = $true
    }
    $Slug = "t-800-agent"
}

# 6) Workspace - skills/rules in .cursor/ (not a plugin)
if ($Profile -eq "unknown" -and $PluginRootOut.Length -eq 0) {
    if ((Test-Path -LiteralPath (Join-Path $Workspace ".cursor") -PathType Container) -or
        (Test-Path -LiteralPath (Join-Path $Workspace ".git") -PathType Container)) {
        $Profile = "workspace-cursor"
        $ArtifactSurface = "cursor-workspace"
        $MemoryDir = ".cursor/t800-memory"
        $MemoryPath = Join-Path $Workspace ".cursor\t800-memory"
        $Slug = "workspace"
        try {
            New-Item -ItemType Directory -Force -Path (Join-Path $MemoryPath "fragments") | Out-Null
            New-Item -ItemType Directory -Force -Path (Join-Path $MemoryPath "factory-briefs") | Out-Null
        } catch {}
    }
}

# Unresolved plugin_root: declared product profile keeps identity,
# others without memory -> unknown; workspace-cursor is not flagged here.
if ($PluginRootOut.Length -eq 0 -and $Profile -ne "workspace-cursor") {
    $NeedsUserQuestion = $true
    if ($MemoryDir.Length -eq 0 -and -not $ProfileDeclared) {
        $Profile = "unknown"
    }
}

if ($MemoryDir.Length -gt 0 -and -not (Test-Path -LiteralPath $MemoryPath -PathType Container)) {
    $NeedsUserQuestion = $true
}

# Explicit operator choice (--plugin-root after list-target-plugins)
if ($PluginRoot.Length -gt 0 -and
    (Test-Path -LiteralPath (Join-Path $PluginRoot ".cursor-plugin") -PathType Container)) {
    $PluginRootOut = (Resolve-Path -LiteralPath $PluginRoot).Path
    $NeedsUserQuestion = $false
    if ($Profile -eq "unknown") {
        $Profile = "generic-plugin"
        $ArtifactSurface = "cursor-plugin"
    }
    $ovrPluginJson = Join-Path $PluginRootOut ".cursor-plugin\plugin.json"
    if (Test-Path -LiteralPath $ovrPluginJson -PathType Leaf) {
        try {
            $pj2 = (Get-Content -LiteralPath $ovrPluginJson -Raw -Encoding utf8 | ConvertFrom-Json)
            if ($pj2.name) { $Slug = [string]$pj2.name }
        } catch {}
    }
}

# Default sources
if ($null -eq $PluginRootSource -and $PluginRootOut.Length -gt 0) {
    if ($ProfileDeclared) {
        $PluginRootSource = "workspace"
    } elseif ($Profile -eq "marker") {
        $PluginRootSource = "marker"
    } elseif ($PluginRoot.Length -gt 0) {
        $PluginRootSource = "override"
    } else {
        $PluginRootSource = "discovery"
    }
}

# Adapter from matched discovery profile (profiles/<id>.md -> field adapter)
if ($null -eq $Adapter -and $Profile -ne "unknown") {
    $pb = Get-ProfileBlock $Profile
    if ($pb) {
        try {
            $pd = $pb | ConvertFrom-Json
            if ($pd.adapter) { $Adapter = [string]$pd.adapter }
        } catch {}
    }
}

$out = [ordered]@{
    workspace_root       = $Workspace
    plugin_root          = $PluginRootOut
    plugin_root_source   = $PluginRootSource
    write_allowed        = $WriteAllowed
    memory_dir           = $MemoryDir
    memory_path          = $MemoryPath
    profile              = $Profile
    slug                 = $Slug
    artifact_surface     = $ArtifactSurface
    release_handoff      = $ReleaseHandoff
    knowledge_vault_path = $KnowledgeVaultPath
    adapter              = $Adapter
    needs_user_question  = $NeedsUserQuestion
}

$out | ConvertTo-Json
