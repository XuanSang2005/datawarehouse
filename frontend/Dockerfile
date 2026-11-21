FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# The nginx image substitutes environment variables in /etc/nginx/templates/*.template at startup.
# Defaults suit docker compose; on Railway set PORT and BACKEND_URL (the backend's public URL).
ENV PORT=80 BACKEND_URL=http://backend:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
