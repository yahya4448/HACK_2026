# Utilise une image Python légère
FROM python:3.10-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY . .

# Utilisateur non-root pour la sécurité
RUN useradd -m appuser
USER appuser

# Le port sera passé par la variable d'environnement ou la commande
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]