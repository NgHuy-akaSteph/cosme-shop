# see https://dockerfile.ops-playground.dev for syntax

FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Rebuild the image whenever code changes
FROM base AS development
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

CMD ["npm", "run", "dev", "--", "--host"]

# Production image
FROM base AS production
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=development /app/dist ./dist

EXPOSE 3000

CMD ["npm", "run", "preview"]
