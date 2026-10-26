# Lets the deployed app call Foundry and Azure AI Speech with its own identity (no keys). Run it once, after deploy.ps1:
#   powershell -ExecutionPolicy Bypass -File .\infra\grant-access.ps1
param(
  [string]$Name = 'matchvoice',
  [string]$ResourceGroup = 'rg-backtothegame',
  [string]$FoundryAccount = 'al064488-6492-resource',
  [string]$SpeechAccount = 'btg-speech-hack',
  [int]$MinReplicas = 0  # 1 keeps an instance warm; not supported on Express environments
)

$ErrorActionPreference = 'Stop'

Write-Host 'Turning on the managed identity of the app...'
az containerapp identity assign --name $Name --resource-group $ResourceGroup --system-assigned --output none
$principal = az containerapp show --name $Name --resource-group $ResourceGroup --query identity.principalId -o tsv
if (-not $principal) { throw 'The app has no identity. Did deploy.ps1 finish?' }

$foundryId = az cognitiveservices account show --name $FoundryAccount --resource-group $ResourceGroup --query id -o tsv
$speechId = az cognitiveservices account show --name $SpeechAccount --resource-group $ResourceGroup --query id -o tsv

$grants = @(
  @{ Role = 'Foundry User'; Scope = $foundryId; Label = 'Foundry' },  # formerly called "Azure AI User"
  @{ Role = 'Cognitive Services Speech User'; Scope = $speechId; Label = 'Speech' }
)
foreach ($g in $grants) {
  Write-Host "Granting '$($g.Role)' on $($g.Label)..."
  az role assignment create --assignee-object-id $principal --assignee-principal-type ServicePrincipal `
    --role $g.Role --scope $g.Scope --output none
  if ($LASTEXITCODE -ne 0) { throw "Could not grant '$($g.Role)'" }
}

if ($MinReplicas -gt 0) {
  # Express environments reject `update` while the app has a system identity, so this is best effort.
  Write-Host "Keeping at least $MinReplicas instance running (best effort)..."
  $ErrorActionPreference = 'Continue' # stderr output must not stop the script on Windows PowerShell 5.1
  az containerapp update --name $Name --resource-group $ResourceGroup --min-replicas $MinReplicas --output none 2>$null
  $ErrorActionPreference = 'Stop'
  if ($LASTEXITCODE -ne 0) { Write-Host 'Could not set the minimum replicas here; ping /api/health every few minutes to keep it warm.' }
}

$fqdn = az containerapp show --name $Name --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn -o tsv
Write-Host "`nDone. Role changes can take a few minutes to apply."
Write-Host "App URL: https://$fqdn"
