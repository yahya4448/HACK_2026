Write-Host "🧹 Nettoyage de la plateforme..." -ForegroundColor Cyan

# 1. Arrêter les conteneurs et supprimer les volumes (efface la DB et les métriques)
docker compose down -v

# 2. Relancer tout à neuf
docker compose up -d

Write-Host "⏳ Attente du démarrage de la base de données..."
Start-Sleep -Seconds 10

# 3. Ré-insérer un ingénieur d'astreinte par défaut
$body = @{
    engineer_name = "Equipe SRE Hackathon"
    phone_number = "+212 5 00 00 00 00"
    start_time = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    end_time = (Get-Date).AddDays(7).ToString("yyyy-MM-ddTHH:mm:ss")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8003/api/v1/oncall/shifts" -Method Post -ContentType "application/json" -Body $body

Write-Host "✨ Système prêt et propre pour la démo !" -ForegroundColor Green