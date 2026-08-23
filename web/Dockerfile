FROM node:22-slim AS deps
WORKDIR /srv/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci --omit=dev || npm install --omit=dev

FROM node:22-slim AS build
WORKDIR /srv/web
COPY web/package.json web/package-lock.json* ./
RUN npm ci || npm install
COPY web .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /srv/web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /srv/web/node_modules ./node_modules
COPY --from=build /srv/web/.next ./.next
COPY --from=build /srv/web/public ./public
COPY web/package.json web/next.config.mjs ./
EXPOSE 3000
CMD ["npx", "next", "start"]
