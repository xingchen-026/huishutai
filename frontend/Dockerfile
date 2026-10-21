# 第一阶段：构建 Vue 项目
FROM node:20-alpine AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 第二阶段：用 Nginx 托管打包后的静态文件
FROM nginx:alpine
# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf
# 从构建阶段复制打包结果
COPY --from=build-stage /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]