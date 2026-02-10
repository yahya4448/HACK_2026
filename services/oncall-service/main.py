# from fastapi import FastAPI
# from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
# from starlette.responses import Response

# app = FastAPI()

# @app.get("/api/v1/oncall/current")
# def get_current_oncall():
#     # Mock simple pour le hackathon
#     return {
#         "team": "platform",
#         "primary": {"name": "Alice Admin", "phone": "+123456789"},
#         "secondary": {"name": "Bob Builder", "phone": "+987654321"}
#     }

# @app.get("/metrics")
# def metrics():
#     return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncpg
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(
    title="Incident Management API",
    description="Service de gestion du cycle de vie des incidents SRE",
    version="1.0.0",
    contact={
        "name": "SRE Team - Hackathon 2026",
    },
)

DB_URL = os.getenv("DB_URL", "postgresql://user:password@database:5432/incident_db")

class ShiftSchema(BaseModel):
    engineer_name: str
    phone_number: str
    start_time: datetime
    end_time: datetime

@app.on_event("startup")
async def startup():
    # Connexion DB + Création Table Astreinte
    retries = 10
    while retries > 0:
        try:
            app.state.pool = await asyncpg.create_pool(DB_URL)
            async with app.state.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS shifts (
                        id SERIAL PRIMARY KEY,
                        engineer_name VARCHAR(100),
                        phone_number VARCHAR(20),
                        start_time TIMESTAMP,
                        end_time TIMESTAMP
                    );
                """)
            print("✅ On-Call Service: DB Connected & Table Ready")
            break
        except Exception as e:
            print(f"⚠️ Waiting for DB... ({e})")
            retries -= 1
            await asyncio.sleep(5)

@app.post("/api/v1/oncall/shifts")
async def create_shift(shift: ShiftSchema):
    async with app.state.pool.acquire() as conn:
        # On insère un créneau
        shift_id = await conn.fetchval(
            "INSERT INTO shifts (engineer_name, phone_number, start_time, end_time) VALUES ($1, $2, $3, $4) RETURNING id",
            shift.engineer_name, shift.phone_number, shift.start_time.replace(tzinfo=None), shift.end_time.replace(tzinfo=None)
        )
    return {"status": "created", "shift_id": shift_id}

@app.get("/api/v1/oncall/current")
async def get_current_oncall():
    async with app.state.pool.acquire() as conn:
        # Qui travaille MAINTENANT ?
        row = await conn.fetchrow(
            "SELECT * FROM shifts WHERE NOW() BETWEEN start_time AND end_time LIMIT 1"
        )
        
        if row:
            return {
                "status": "active",
                "primary": {
                    "name": row['engineer_name'],
                    "phone": row['phone_number']
                },
                "source": "database"
            }
        else:
            # Fallback si pas de planning
            return {
                "status": "no-coverage",
                "primary": {"name": "Default Admin", "phone": "911"},
                "source": "fallback"
            }

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health_check():
    try:
        # On vérifie si la connexion DB est active
        async with app.state.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return {"status": "healthy", "database": "connected", "timestamp": datetime.now()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")
