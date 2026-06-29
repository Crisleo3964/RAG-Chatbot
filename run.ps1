$venv = Join-Path $PSScriptRoot "rag-chatbot\.venv\Scripts\python.exe"
$env:GROQ_API_KEY = [Environment]::GetEnvironmentVariable('GROQ_API_KEY', 'User')
if (-not $env:GROQ_API_KEY) {
    Write-Error "GROQ_API_KEY is not set. Run: [Environment]::SetEnvironmentVariable('GROQ_API_KEY', 'your-key', 'User')"
    exit 1
}
Write-Host "GROQ_API_KEY loaded. Starting app..."
& $venv $PSScriptRoot\main.py
