FROM node:22-alpine AS build

RUN corepack enable
WORKDIR /app

# Dependencies first: this layer is reused until pnpm-lock.yaml changes.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM nginx:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
