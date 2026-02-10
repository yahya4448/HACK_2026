FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# On lance Vite en mode host pour le dev/demo rapide
CMD ["npm", "run", "dev", "--", "--host"]