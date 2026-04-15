# Stage 1: React 빌드
# 빌드 컨텍스트는 프로젝트 루트 (docker-compose에서 context: . 지정)
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Nginx 서빙
FROM nginx:alpine

# React 빌드 결과물 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx 설정 복사
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
