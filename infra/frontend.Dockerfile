FROM node:22-alpine AS budowanie
WORKDIR /src
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend ./
RUN pnpm build
FROM nginx:1.28-alpine
COPY --from=budowanie /src/dist /usr/share/nginx/html
COPY infra/nginx.conf /etc/nginx/nginx.conf
