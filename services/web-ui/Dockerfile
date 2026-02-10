# --- builder stage ---
FROM node:18 AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build --if-present

# --- runtime stage ---
FROM node:18-alpine
WORKDIR /app
RUN apk add --no-cache curl
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
ENV NODE_ENV=production
COPY package.json ./
RUN npm install --production
COPY --from=builder /app/dist ./dist
COPY src ./src
EXPOSE 3000
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:3000/health || exit 1
CMD ["node", "src/server.js"]