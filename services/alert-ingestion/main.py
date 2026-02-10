import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import asyncpg
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(
    title="Incident Management API",
    description="Service de gestion du cycle de vie des incidents SRE",
    version="1.0.0",
    contact={
        "name": "SRE Team - Hackathon 2026",
    },
)

# Configuration
DB_URL = os.getenv("DB_URL", "postgresql://user:password@database:5432/incident_db")
ALERTS_TOTAL = Counter('alerts_received_total', 'Total alerts received', ['severity'])

class AlertSchema(BaseModel):
    service: str
    severity: str
    message: str

@app.on_event("startup")
async def startup():
    # BOUCLE DE CONNEXION ROBUSTE (Anti-Crash)
    retries = 10
    while retries > 0:
        try:
            print(f"🔄 Tentative de connexion DB ({DB_URL})...")
            app.state.pool = await asyncpg.create_pool(DB_URL)
            print("✅ Connecté à la Base de Données !")
            
            # Création des tables si elles n'existent pas (Au cas où)
            async with app.state.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS incidents (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'open',
                        service VARCHAR(100),
                        severity VARCHAR(20),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        acknowledged_at TIMESTAMP,
                        resolved_at TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS alerts (
                        id SERIAL PRIMARY KEY,
                        incident_id INT REFERENCES incidents(id),
                        raw_data JSONB,
                        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            break
        except Exception as e:
            print(f"⚠️ La DB n'est pas prête ({e}), nouvelle tentative dans 5s...")
            retries -= 1
            await asyncio.sleep(5)

import requests  # Ajoute l'import en haut du fichier

@app.post("/api/v1/alerts")
async def create_alert(alert: AlertSchema):
    ALERTS_TOTAL.labels(severity=alert.severity).inc()
    print(f"📥 Alerte reçue: {alert.service} - {alert.message}")
    
    # AJOUT : Récupérer l'astreinte en temps réel
    try:
        oncall_info = requests.get("http://oncall-service:8003/api/v1/oncall/current").json()
        engineer = oncall_info['primary']['name']
    except Exception as e:
        print(f"⚠️ Erreur récupération astreinte: {e}")
        engineer = "Unassigned"
    
    print(f"📢 Alerte transmise à : {engineer}")
    
    async with app.state.pool.acquire() as conn:
        # Corrélation: Chercher un incident ouvert
        row = await conn.fetchrow(
            "SELECT id FROM incidents WHERE service = $1 AND status != 'resolved'", 
            alert.service
        )
        
        if row:
            incident_id = row['id']
            print(f"🔗 Lié à l'incident existant #{incident_id}")
            status = "existing_incident"
        else:
            # Créer nouvel incident avec l'ingénieur assigné
            incident_id = await conn.fetchval(
                "INSERT INTO incidents (title, service, severity, status, assigned_to) VALUES ($1, $2, $3, 'open', $4) RETURNING id",
                f"Alert: {alert.message}", alert.service, alert.severity, engineer
            )
            print(f"🆕 Nouvel incident créé #{incident_id} - Assigné à {engineer}")
            status = "new_incident"

        # Sauvegarder l'alerte
        await conn.execute(
            "INSERT INTO alerts (incident_id, raw_data) VALUES ($1, $2)",
            incident_id, alert.model_dump_json()
        )
            
    return {
        "status": "processed", 
        "incident_id": incident_id, 
        "type": status,
        "assigned_to": engineer
    }

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
from datetime import datetime
from fastapi import HTTPException
@app.get("/health")
async def health_check():
    try:
        # On vérifie si la connexion DB est active
        async with app.state.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")