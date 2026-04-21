FROM nginx:1.27-alpine

# Удаляем дефолтный конфиг
RUN rm /etc/nginx/conf.d/default.conf

# Подключаем наш конфиг
COPY nginx.conf /etc/nginx/conf.d/app.conf

EXPOSE 80 443
