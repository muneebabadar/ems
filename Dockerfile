# --- Stage 1: build the React client ---
FROM node:20-alpine AS client-build
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

# --- Stage 2: production server (serves API + built client) ---
FROM node:20-alpine
ENV NODE_ENV=production
WORKDIR /app

COPY server/package*.json ./server/
RUN npm ci --prefix server --omit=dev

COPY server/ ./server/
COPY --from=client-build /app/client/dist ./client/dist

USER node
EXPOSE 3000
CMD ["node", "server/src/index.js"]
