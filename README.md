# 🛡️ DevOps Incident Platform (Local Edition)

Plateforme de gestion d'incidents résiliente et observable, construite pour le Hackathon OpenSource 2026.
Architecture microservices complète fonctionnant 100% en local via Docker Compose.

## 🏗 Architecture

| Service | Port | Description | Stack |
| :--- | :--- | :--- | :--- |
| **Alert Ingestion** | `:8001` | Réception et corrélation des alertes | Python (FastAPI) |
| **Incident Mgt** | `:8002` | Cycle de vie (MTTA/MTTR) | Python (FastAPI) |
| **On-Call** | `:8003` | Gestion des astreintes | Python (FastAPI) |
| **Web UI** | `:8080` | Dashboard interactif | React (Vite) |
| **Prometheus** | `:9090` | Collecte des métriques | Time-Series DB |
| **Grafana** | `:3000` | Visualisation SRE | Dashboarding |
| **Postgres** | `:5432` | Persistance des données | SQL |



[Image of microservices architecture diagram]


## 🚀 Démarrage Rapide

Pré-requis : Docker & Docker Compose.

1. **Cloner le projet**
   ```bash
   git clone <ton-repo>
   cd incident-platform
   ## 🏗 Schéma d'Architecture

```mermaid
graph TD
    User((Utilisateur)) -->|HTTP| WebUI[⚛️ Web UI :8080]
    
    subgraph "Docker Network"
        WebUI -->|API| IncidentService[🐍 Incident Mgt :8002]
        
        AlertSource[Scripts/Curl] -->|POST| AlertService[🐍 Alert Ingestion :8001]
        
        AlertService -->|SQL| DB[(🐘 PostgreSQL)]
        IncidentService -->|SQL| DB
        OnCallService[🐍 On-Call :8003] -->|SQL| DB
        
        AlertService -.->|Trigger| IncidentService
        
        Prometheus[🔥 Prometheus :9090] -.->|Scrape| AlertService
        Prometheus -.->|Scrape| IncidentService
        Prometheus -.->|Scrape| OnCallService
        
        Grafana[📊 Grafana :3000] -->|Query| Prometheus
    end
## 🧠 Challenges & Solutions SRE

### 1. Problème de Race Condition au démarrage
**Challenge :** Les microservices Python crashaient car ils essayaient de se connecter à PostgreSQL avant que celui-ci ne soit prêt.
**Solution :** Implémentation d'une **Exponential Backoff Loop** dans le code Python et utilisation de `healthcheck` dans Docker Compose.

### 2. Corrélation des Alertes
**Challenge :** Éviter la fatigue des alertes (Alert Fatigue) en ne créant pas 50 incidents pour le même problème.
**Solution :** Logique de filtrage en base de données : si un incident existe déjà pour le même service et n'est pas résolu, la nouvelle alerte est rattachée au lieu de créer un doublon.

### 3. Observabilité
**Challenge :** Mesurer l'efficacité humaine.
**Solution :** Utilisation des `Histograms` Prometheus pour calculer dynamiquement le MTTA et le MTTR.


