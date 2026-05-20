param(
    [string]$EnvFile = ".env.windows",
    [string]$ComposeFile = "docker-compose.windows-installer.yml",
    [string]$EnvTemplateFile = ".env.windows.template",
    [int]$MinimumFreeSpaceGb = 12
)

$ErrorActionPreference = "Stop"

function Get-FreeSpaceGb {
    param([string]$Path)
    $resolved = Resolve-Path $Path
    $drive = Get-PSDrive -Name $resolved.Path.Substring(0, 1)
    return [math]::Floor($drive.Free / 1GB)
}

function Test-DockerDesktop {
    docker version | Out-Null
    docker info | Out-Null
}

function Read-EnvFile {
    param([string]$Path)
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^[A-Za-z_][A-Za-z0-9_]*=') {
            $parts = $_ -split '=', 2
            [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process')
        }
    }
}

function Get-RegistryCredentialValue {
    param(
        [string]$CurrentValue,
        [string]$Prompt,
        [string]$DefaultValue = "",
        [switch]$Secure
    )

    if ($CurrentValue) {
        return $CurrentValue
    }

    if ($Secure) {
        $secureValue = Read-Host -Prompt $Prompt -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
        try {
            return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }

    if ($DefaultValue) {
        $enteredValue = Read-Host -Prompt "$Prompt [$DefaultValue]"
        if ([string]::IsNullOrWhiteSpace($enteredValue)) {
            return $DefaultValue
        }

        return $enteredValue
    }

    return Read-Host -Prompt $Prompt
}

function Set-Or-ReplaceEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )

    $lines = Get-Content $Path
    $updated = $false

    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match "^$Key=") {
            $lines[$index] = "$Key=$Value"
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $lines += "$Key=$Value"
    }

    Set-Content -Path $Path -Value $lines
}

function Get-RequiredEnvValue {
    param(
        [string]$Key,
        [string]$Prompt,
        [string]$CurrentValue,
        [string]$DefaultValue = "",
        [switch]$Secure,
        [string]$PersistPath
    )

    $value = Get-RegistryCredentialValue \
        -CurrentValue $CurrentValue \
        -Prompt $Prompt \
        -DefaultValue $DefaultValue \
        -Secure:$Secure

    if (-not $value) {
        throw "$Key is required to continue."
    }

    if ($PersistPath) {
        Set-Or-ReplaceEnvValue -Path $PersistPath -Key $Key -Value $value
        [Environment]::SetEnvironmentVariable($Key, $value, 'Process')
    }

    return $value
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

if (-not (Test-Path $EnvFile)) {
    if (-not (Test-Path $EnvTemplateFile)) {
        throw "Missing env file: $EnvFile and template file: $EnvTemplateFile"
    }

    Copy-Item $EnvTemplateFile $EnvFile
    Write-Host "Created $EnvFile from $EnvTemplateFile"
}

$freeSpaceGb = Get-FreeSpaceGb -Path $scriptRoot
if ($freeSpaceGb -lt $MinimumFreeSpaceGb) {
    throw "Not enough free disk space. Required: $MinimumFreeSpaceGb GB. Available: $freeSpaceGb GB."
}

Test-DockerDesktop
Read-EnvFile -Path $EnvFile

$registry = $env:REGISTRY
if (-not $registry) {
    throw "REGISTRY must be set in $EnvFile"
}

$env:INSTALLATION_UUID = Get-RequiredEnvValue \
    -Key "INSTALLATION_UUID" \
    -Prompt "Enter installation UUID" \
    -CurrentValue $env:INSTALLATION_UUID \
    -PersistPath $EnvFile

$env:APPLICATION_KEY = Get-RequiredEnvValue \
    -Key "APPLICATION_KEY" \
    -Prompt "Enter application key" \
    -CurrentValue $env:APPLICATION_KEY \
    -PersistPath $EnvFile

$env:POSTGRES_PASSWORD = Get-RequiredEnvValue \
    -Key "POSTGRES_PASSWORD" \
    -Prompt "Enter PostgreSQL password" \
    -CurrentValue $env:POSTGRES_PASSWORD \
    -Secure \
    -PersistPath $EnvFile

$env:REGISTRY_USERNAME = Get-RegistryCredentialValue \
    -CurrentValue $env:REGISTRY_USERNAME \
    -Prompt "Enter registry username" \
    -DefaultValue "nickglezakos"

$env:REGISTRY_PASSWORD = Get-RegistryCredentialValue \
    -CurrentValue $env:REGISTRY_PASSWORD \
    -Prompt "Enter registry token or password" \
    -Secure

if (-not $env:REGISTRY_USERNAME -or -not $env:REGISTRY_PASSWORD) {
    throw "Registry username and token are required to continue."
}

if (-not $env:REGISTRY_USERNAME) {
    throw "Registry username is required to continue."
}

Set-Or-ReplaceEnvValue -Path $EnvFile -Key "REGISTRY_USERNAME" -Value $env:REGISTRY_USERNAME

$registryHost = $registry -replace '/.*$', ''
$env:COMPOSE_PROJECT_NAME = "pplmeta"

Write-Host "Logging into registry $registryHost"
$env:REGISTRY_PASSWORD | docker login $registryHost --username $env:REGISTRY_USERNAME --password-stdin

Write-Host "Pulling pinned images"
docker compose --env-file $EnvFile -f $ComposeFile pull

Write-Host "Starting stack"
docker compose --env-file $EnvFile -f $ComposeFile up -d

Write-Host "Current container status"
docker compose --env-file $EnvFile -f $ComposeFile ps

Write-Host "Installer flow completed. Run health checks next."