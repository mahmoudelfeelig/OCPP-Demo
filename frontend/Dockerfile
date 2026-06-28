FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package.json
COPY tsconfig.json tsconfig.json
COPY next.config.mjs next.config.mjs
COPY next-env.d.ts next-env.d.ts
RUN npm install

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

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
