# 构建阶段：运行 build.py 生成 storage/pkg/apps.json 和 storage/
FROM python:3.12-slim AS builder

WORKDIR /build

COPY aapanel/build.py ./
RUN pip install --no-cache-dir pyyaml && python build.py

# 运行阶段：nginx 静态文件服务
FROM nginx:alpine

COPY aapanel/index.html /usr/share/nginx/html/index.html
COPY --from=builder /build/storage /usr/share/nginx/html/storage
