# Deploys MatchVoice to Azure Container Apps. Run it after `az login` and with Docker Desktop running:
#   powershell -ExecutionPolicy Bypass -File .\infra\deploy.ps1 -Location westus3
# The image is built locally and pushed to Azure Container Registry, because student subscriptions cannot use
# ACR Tasks (build in the cloud). The values in .env go to the app as environment variables; the .env file
# itself never goes into the image (see .dockerignore).
param(
  [string]$Name = 'backtothegame',
  [string]$ResourceGroup = 'rg-backtothegame',
  [string]$Location = 'westus3',
  [string]$Environment = 'matchvoice-env',
  [int]$MaxAiStreams = 3, # AI streams at the same time: this is what limits the model spend of the public demo
  [switch]$Recreate # delete and recreate an existing app (needed to update it on an Express environment)
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$wanted = 'FOUNDRY_PROJECT_ENDPOINT', 'FOUNDRY_MODEL_DEPLOYMENT', 'SPEECH_REGION', 'SPEECH_RESOURCE_ID'

function Run($what, [scriptblock]$cmd) {
  & $cmd
  if ($LASTEXITCODE -ne 0) { throw "$what failed" }
}

# 1) Environment variables from .env (names are printed, values never)
$vars = foreach ($line in Get-Content (Join-Path $root '.env')) {
  $key = ($line -split '=', 2)[0].Trim()
  if ($wanted -contains $key) { $line.Trim() -replace '"', '' }
}
$found = $vars | ForEach-Object { ($_ -split '=', 2)[0] }
$missing = $wanted | Where-Object { $found -notcontains $_ }
if ($missing) { throw "Missing in .env: $($missing -join ', ')" }
$vars += "MAX_AI_STREAMS=$MaxAiStreams"
Write-Host "Variables passed to the app: $(($vars | ForEach-Object { ($_ -split '=', 2)[0] }) -join ', ')"

# 2) Docker must be running
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) { throw 'Docker is not running. Open Docker Desktop, wait until it says "running", and try again.' }

# 3) A container registry in the resource group (reuse one if it exists)
$acr = az acr list --resource-group $ResourceGroup --query '[0].name' -o tsv
if (-not $acr) {
  $acr = 'matchvoice' + (Get-Random -Minimum 10000 -Maximum 99999)
  Write-Host "Creating registry $acr..."
  Run 'az acr create' { az acr create --name $acr --resource-group $ResourceGroup --location $Location --sku Basic --admin-enabled true --output none }
}
Run 'az acr update' { az acr update --name $acr --admin-enabled true --output none }
$server = az acr show --name $acr --query loginServer -o tsv
$user = az acr credential show --name $acr --query username -o tsv
$pass = az acr credential show --name $acr --query 'passwords[0].value' -o tsv

# 4) Build and push the image
$tag = Get-Date -Format 'yyyyMMdd-HHmm'
$image = "$server/${Name}:$tag"
Run 'az acr login' { az acr login --name $acr }
Write-Host "Building $image (a few minutes the first time)..."
Run 'docker build' { docker build --tag $image $root }
Run 'docker push' { docker push $image }

# 5) Create or update the container app.
# Express environments reject any update of an app that has a system identity, and `az containerapp identity remove`
# crashes there too. The only way to ship a new image is to delete the app and create it again (same name and
# environment, so the URL stays the same), then grant the roles to its new identity (step 6). That means a few
# minutes of downtime, so it only happens with -Recreate.
Set-Location $root
# Windows PowerShell 5.1 turns anything an `az` command writes to stderr (warnings, "app not found") into a
# terminating error while ErrorActionPreference is Stop, so this lookup runs with Continue.
$ErrorActionPreference = 'Continue'
$existing = az containerapp show --name $Name --resource-group $ResourceGroup --query identity.type -o tsv 2>$null
$ErrorActionPreference = 'Stop'
if ($existing -and $existing -ne 'None') {
  if (-not $Recreate) {
    throw "The app '$Name' has a managed identity and Express environments cannot update it. The image $image is already pushed. Run this script again with -Recreate to delete and recreate the app (a few minutes of downtime, same URL)."
  }
  Write-Host "Deleting the app '$Name' to recreate it..."
  Run 'az containerapp delete' { az containerapp delete --name $Name --resource-group $ResourceGroup --yes --output none }
}
Run 'az containerapp up' {
  az containerapp up `
    --name $Name `
    --resource-group $ResourceGroup `
    --location $Location `
    --environment $Environment `
    --image $image `
    --registry-server $server `
    --registry-username $user `
    --registry-password $pass `
    --ingress external `
    --target-port 8000 `
    --env-vars $vars
}

# 6) Give the (new) identity its roles again. The first deploy needs this too, so it always runs.
& (Join-Path $PSScriptRoot 'grant-access.ps1') -Name $Name -ResourceGroup $ResourceGroup

$fqdn = az containerapp show --name $Name --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
Write-Host "`nApp URL: https://$fqdn"
