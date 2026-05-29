# aaPanel 应用市场

基于 [aaPanel AppStore](https://github.com/aaPanel/appstore) 的 Docker 应用商店前端。

## 数据适配

`build.py` 对 aaPanel 原始仓库进行适配处理：

1. 从 GitHub 下载 `aaPanel/appstore`（`main` 分支）
2. 提取 `apps/` 到 `storage/apps/`，删除可执行脚本（`.sh`、`.py`、`.bat`、`.exe`）
3. 提取聚合元数据到 `storage/pkg/apps.json`
4. 保留根目录 `app_order.json`、`apptags.json`
5. 移除 `app.json` 中的域名字段（`attr=='domain'` 或名称含"域名"）
6. 替换路径前缀 `/www/dk_project/dk_app/` → `./`

## 构建

```bash
pip install pyyaml
python build.py
```

构建产物：

| 文件 | 说明 |
|---|---|
| `storage/pkg/apps.json` | 聚合应用元数据（列表页使用） |
| `storage/apps/<app>/app.json` | 单个应用详情（详情页使用） |
| `storage/apps/<app>/docker-compose.yml` | compose 模板 |
| `app_order.json`、`apptags.json` | 排序与标签数据 |

## 本地运行

```bash
python -m http.server 8080 -d .
```

访问 <http://localhost:8080>

## Docker 部署

```bash
docker build -f aapanel/Dockerfile -t appstore-aapanel .
docker run -d -p 8080:80 appstore-aapanel
```

## 前端适配

`index.html` 适配 aaPanel 原始仓库结构：

- 图标：`storage/apps/<app>/ico-dkapp_<app>.png`
- 字段：`storage/apps/<app>/app.json` 中的 `field` 和 `env`
- compose：`storage/apps/<app>/<app>/docker-compose.yml` 或 `storage/apps/<app>/docker-compose.yml`

## 技术栈

Vue 3 · Tailwind CSS · Marked · Font Awesome · PyYAML · Nginx