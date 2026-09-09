FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
COPY tsconfig.json tsconfig.json
COPY next.config.mjs next.config.mjs
COPY next-env.d.ts next-env.d.ts
RUN npm ci

FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY package.json package.json
COPY tsconfig.json tsconfig.json
COPY next.config.mjs next.config.mjs
COPY next-env.d.ts next-env.d.ts
COPY app app
COPY public public

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --chown=node:node --from=builder /app/package.json ./package.json
COPY --chown=node:node --from=builder /app/.next/standalone ./
COPY --chown=node:node --from=builder /app/.next/static ./.next/static
COPY --chown=node:node --from=builder /app/public ./public

EXPOSE 3000

USER node
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "server.js"]
