$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    Write-Host "Création de l'environnement virtuel..." -ForegroundColor Cyan
    python -m venv .venv
}

# Activer l'environnement
. .venv\Scripts\Activate.ps1

Write-Host "Vérification des dépendances..." -ForegroundColor Cyan
pip install -r requirements.txt | Out-Null

Write-Host "Lancement de Disney Infinity Creator (PySide6)..." -ForegroundColor Cyan
python src/main.py
exit 