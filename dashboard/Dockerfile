# ---- Build stage ----
FROM node:20-slim AS build
WORKDIR /app

# package-lock.json is committed, so npm ci installs the exact locked tree and
# fails loudly if the lock file and package.json ever drift apart.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Phase 8 removed the per-backend VITE_* build args. The browser no longer
# calls published host ports directly - it calls /api/rca and /api/detector on
# its own origin, which nginx reverse-proxies (see nginx.conf). That keeps the
# session cookie same-site and leaves nothing host-specific baked into the
# bundle.
RUN npm run build

# ---- Run stage ----
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
