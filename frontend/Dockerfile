FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# Image nginx tự thay biến môi trường trong /etc/nginx/templates/*.template khi khởi động.
# Mặc định chạy với docker compose; trên Railway đặt PORT và BACKEND_URL (URL công khai của backend).
ENV PORT=80 BACKEND_URL=http://backend:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
