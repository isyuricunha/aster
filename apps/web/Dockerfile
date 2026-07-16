FROM node:22-alpine AS build

ARG NEXT_PUBLIC_ASTER_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_ASTER_API_URL=$NEXT_PUBLIC_ASTER_API_URL

WORKDIR /app
RUN npm install --global pnpm@10

COPY package.json pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --no-frozen-lockfile

COPY apps/web apps/web
RUN pnpm --filter @aster/web build

FROM node:22-alpine AS runner

ENV NODE_ENV=production
WORKDIR /app
RUN npm install --global pnpm@10

COPY --from=build --chown=node:node /app /app
USER node

EXPOSE 3000

CMD ["pnpm", "--filter", "@aster/web", "start"]
