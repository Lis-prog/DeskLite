FROM node:20-alpine AS base

WORKDIR /app

COPY package*.json ./
RUN npm ci

# ── Local development (docker-compose.yml) ────────────────────────────────────
FROM base AS development

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

# ── Production build ──────────────────────────────────────────────────────────
FROM base AS builder

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY . .

RUN npm run build

FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/next.config.mjs ./

EXPOSE 3000

CMD ["npm", "run", "start"]
