# aaPanel AppStore 适配器

本目录实现了一个 aaPanel 原始 appstore 数据适配层：

- 从 `https://github.com/aaPanel/appstore` 下载原始仓库
- 将 `apps/` 目录完整提取到 `aapanel/storage/apps/`
- 删除其中的可执行脚本文件（如 `.sh`、`.py`、`.bat`、`.exe`）
- 提取官方聚合元数据到 `aapanel/storage/pkg/apps.json`
- 保留根目录文件：`app_order.json`、`apptags.json`
- 保留各应用目录下完整的 `app.json`
- 前端列表使用精简 `storage/pkg/apps.json`，安装详情仍从 `storage/apps/<app>/app.json` 读取

## 构建

```bash
python3 aapanel/build.py
```

生成产物：

- `aapanel/storage/pkg/apps.json`
- `aapanel/storage/apps/<app>/...`

## 本地运行

```bash
python3 -m http.server 8080 -d aapanel
```

然后访问 `http://127.0.0.1:8080`。

## Docker

```bash
docker build -f aapanel/Dockerfile -t appstore-aapanel .
docker run -d -p 8080:80 appstore-aapanel
```

## 说明

`aapanel/index.html` 已适配 aaPanel 原始仓库结构：

- 应用图标使用 `storage/apps/<app>/ico-dkapp_<app>.png`
- 应用字段来自 `storage/apps/<app>/app.json` 中的 `field` 和 `env`
- docker compose 文件在 `storage/apps/<app>/<app>/docker-compose.yml` 或 `storage/apps/<app>/docker-compose.yml` 中查找

当前逻辑更贴近原始 aaPanel 包结构，使用官方 `storage/pkg/apps.json` 作为聚合元数据，不再生成额外的 `index.json` 或 `meta.yml`。