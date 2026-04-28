FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/app.conf

# Копируем фронтенд в директорию статики Nginx
COPY ../frontend/index.html /usr/share/nginx/html/index.html

EXPOSE 80 443
