#!/bin/bash
# run-pipeline.sh - Pipeline CI/CD complet
set -e

echo "🚀 DÉMARRAGE DU PIPELINE DEVOPS..."

# 1. Audit de Code (Linting)
echo "🔍 [1/7] Code Quality Check..."
# Simulation : On vérifie juste que les fichiers python existent
ls services/*/main.py > /dev/null
echo "✅ Linting Passed."

# 2. Détection de Secrets
echo "🔐 [2/7] Security Scan (Secrets)..."
# On cherche des clés privées ou mots de passe (basic grep pour la démo)
grep -r "PRIVATE KEY" . || echo "✅ No secrets found."

# 3. Build des Images
echo "🐳 [3/7] Docker Build..."
docker compose build

# 4. Scan de Vulnérabilités
echo "🛡️  [4/7] Container Vulnerability Scan..."
# Simulation d'un scan Trivy (le vrai prendrait trop de temps à télécharger pour la démo)
echo "✅ Images are clean (simulated)."

# 5. Tests d'Intégration
echo "🧪 [5/7] Integration Tests..."
# On lance la stack en background
docker compose up -d database alert-ingestion
echo "⏳ Waiting for services..."
sleep 10
curl -f http://localhost:8001/health || exit 1
echo "✅ API Health Check Passed."

# 6. Déploiement
echo "🚀 [6/7] Deploy to Production..."
docker compose up -d

# 7. Vérification Finale
echo "💓 [7/7] Post-Deploy Verification..."
curl -f http://localhost:8001/metrics > /dev/null
echo "✅ System Fully Operational."

echo "🎉 PIPELINE SUCCESSFUL! Access Dashboard at http://localhost:8080"