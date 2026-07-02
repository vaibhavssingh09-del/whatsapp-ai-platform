# --- Frontend Dockerfile ---
# Design decision: multi-stage build here (unlike the backend's single-stage)
# because the build stage needs the full Node toolchain (~200MB+) but the
# runtime only needs to serve static files — nginx:alpine is ~40MB. That
# difference is worth the extra Dockerfile complexity for a service that's
# rebuilt and redeployed far more often than the backend during active
# frontend iteration.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
