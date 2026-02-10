
import os, asyncio, requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Initialisation de l'API avec Métadonnées pour le Swagger
app = FastAPI(
    title="Incident Management Engine",
    description="Cerveau de gestion des incidents - Hackathon 2026",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configuration
DB_URL = os.getenv("DB_URL", "postgresql://user:password@database:5432/incident_db")
DB_OFF_SIMULATION = False 

# Métriques Prometheus
MTTA = Histogram('incident_mtta_seconds', 'Time to Acknowledge')
MTTR = Histogram('incident_mttr_seconds', 'Time to Resolve')
ESCALATIONS = Counter('escalations_total', 'Total Escalations triggered')

@app.on_event("startup")
async def startup():
    retries = 10
    while retries > 0:
        try:
            app.state.pool = await asyncpg.create_pool(DB_URL)
            async with app.state.pool.acquire() as conn:
                # Création des tables (Fusionnée et Robuste)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS incidents (
                        id SERIAL PRIMARY KEY, title TEXT, service TEXT, severity TEXT,
                        status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT NOW(),
                        acknowledged_at TIMESTAMP, resolved_at TIMESTAMP, description TEXT
                    );
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id SERIAL PRIMARY KEY, action VARCHAR(100), incident_id INT,
                        timestamp TIMESTAMP DEFAULT NOW()
                    );
                """)
            asyncio.create_task(escalation_worker())
            print("✅ Incident Engine: DB Connected & Tables Ready")
            break
        except Exception as e:
            print(f"⚠️ DB Connection failed, retrying... {e}")
            retries -= 1
            await asyncio.sleep(5)

async def escalation_worker():
    """Vérifie les incidents ignorés et simule une notification On-Call"""
    while True:
        if not DB_OFF_SIMULATION:
            try:
                async with app.state.pool.acquire() as conn:
                    # On cherche les incidents 'open' depuis plus de 60s
                    rows = await conn.fetch("SELECT id, title FROM incidents WHERE status='open' AND created_at < NOW() - INTERVAL '1 minute' AND title NOT LIKE '[URGENT]%'")
                    
                    for r in rows:
                        # Appel au service On-Call (Comme dans ton ancien code)
                        try:
                            oncall = requests.get("http://oncall-service:8003/api/v1/oncall/current", timeout=2).json()
                            eng = oncall['primary']['name']
                        except:
                            eng = "Admin"

                        print(f"🔥 [ESCALATION] Notification envoyée à {eng} pour l'incident #{r['id']}")
                        
                        await conn.execute("UPDATE incidents SET title = '[URGENT] ' || title WHERE id=$1", r['id'])
                        await conn.execute("INSERT INTO audit_logs (action, incident_id) VALUES ($1, $2)", "AUTO_ESCALATION", r['id'])
                        ESCALATIONS.inc()
            except Exception as e:
                print(f"Worker Error: {e}")
        await asyncio.sleep(30)

@app.get("/api/v1/incidents")
async def get_incidents():
    if DB_OFF_SIMULATION: raise HTTPException(status_code=500, detail="Database Down (Chaos Simulation)")
    async with app.state.pool.acquire() as conn:
        return [dict(r) for r in await conn.fetch("SELECT * FROM incidents ORDER BY created_at DESC")]

@app.put("/api/v1/incidents/{id}/acknowledge")
async def acknowledge(id: int):
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow("UPDATE incidents SET status='acknowledged', acknowledged_at=NOW() WHERE id=$1 AND status='open' RETURNING created_at, acknowledged_at", id)
        if row:
            MTTA.observe((row['acknowledged_at']-row['created_at']).total_seconds())
            await conn.execute("INSERT INTO audit_logs (action, incident_id) VALUES ('ACKNOWLEDGE', $1)", id)
            return {"status": "acknowledged"}
    return {"status": "already_processed"}

@app.put("/api/v1/incidents/{id}/resolve")
async def resolve(id: int):
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow("UPDATE incidents SET status='resolved', resolved_at=NOW() WHERE id=$1 AND status!='resolved' RETURNING created_at, resolved_at", id)
        if row:
            MTTR.observe((row['resolved_at']-row['created_at']).total_seconds())
            # FIX: Ici on met bien 'RESOLVE' et non 'ACKNOWLEDGE'
            await conn.execute("INSERT INTO audit_logs (action, incident_id) VALUES ('RESOLVE', $1)", id)
            return {"status": "resolved"}
    return {"status": "already_resolved"}

@app.get("/api/v1/audit")
async def get_audit():
    async with app.state.pool.acquire() as conn:
        return [dict(r) for r in await conn.fetch("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 30")]

# --- CHAOS ENGINEERING ---
@app.post("/api/v1/chaos/kill-db")
async def kill():
    global DB_OFF_SIMULATION
    DB_OFF_SIMULATION = True
    await app.state.pool.close()
    return {"status": "🚨 DB CONNECTION KILLED"}

@app.post("/api/v1/chaos/restore-db")
async def restore():
    global DB_OFF_SIMULATION
    DB_OFF_SIMULATION = False
    app.state.pool = await asyncpg.create_pool(DB_URL)
    return {"status": "✅ DB CONNECTION RESTORED"}

# --- OBSERVABILITÉ ---
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health_check():
    if DB_OFF_SIMULATION:
        raise HTTPException(status_code=503, detail="Database connection simulated down")
    try:
        async with app.state.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now()}
    except:
        raise HTTPException(status_code=503, detail="Unhealthy")
