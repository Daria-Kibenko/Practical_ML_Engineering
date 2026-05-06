FROM nginx:alpine

# Удаляем дефолтный конфиг
RUN rm /etc/nginx/conf.d/default.conf

# Копируем ваш готовый nginx.conf
COPY web-proxy/nginx.conf /etc/nginx/conf.d/app.conf

# Никаких других COPY не нужно – весь контент раздаёт Flask
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]