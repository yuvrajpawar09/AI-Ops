# ---- Build stage ----
FROM node:20-slim AS build
WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Vite inlines import.meta.env.VITE_* as string literals at build time -
# there's no server process to read env vars from at container start (the
# run stage is static nginx), so these have to be build args instead.
# Defaults match the ports docker-compose.yml publishes to the host.
ARG VITE_ANOMALY_API_URL=http://localhost:8000
ARG VITE_RCA_API_URL=http://localhost:8100
ARG VITE_ORDER_API_URL=http://localhost:8081
ENV VITE_ANOMALY_API_URL=$VITE_ANOMALY_API_URL
ENV VITE_RCA_API_URL=$VITE_RCA_API_URL
ENV VITE_ORDER_API_URL=$VITE_ORDER_API_URL

RUN npm run build

# ---- Run stage ----
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
