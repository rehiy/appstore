# AppStore — Docker 应用市场

Docker 应用市场，提供可视化的应用浏览、搜索与一键安装体验。支持 1Panel 与 aaPanel 两种应用数据源。

## 功能特性

| 特性 | 说明 |
|---|---|
| **应用浏览** | 分类展示、关键词搜索、标签过滤 |
| **版本管理** | 多版本切换、版本详情与 README 文档 |
| **一键安装** | 表单配置 → 生成 `docker-compose.yml` → `postMessage` 交付宿主 |
| **响应式布局** | 桌面端双栏 / 移动端单栏自适应 |
| **iframe 嵌入** | 通过 `postMessage` 与宿主通信，无需同源 |

## 项目结构

```
appstore/
├── .github/workflows/release.yml   # CI/CD：tag 触发多架构镜像构建
├── 1panel/                          # 1Panel 应用数据源
│   ├── build.py                     # 下载 1Panel/appstore → 生成 index.json + storage/
│   ├── Dockerfile                   # 多阶段构建（Python 构建 + Nginx 运行）
│   ├── index.html                   # Vue 3 + Tailwind CSS 前端
│   └── README.md
├── aapanel/                         # aaPanel 应用数据源
│   ├── build.py                     # 下载 aaPanel/appstore → 生成 storage/pkg/apps.json + storage/apps/
│   ├── Dockerfile                   # 多阶段构建
│   ├── index.html                   # 适配 aaPanel 原始结构的前端
│   └── README.md
└── README.md
```

## 构建流程

### 1Panel 数据源

```bash
pip install pyyaml
python 1panel/build.py
```

`build.py` 执行步骤：

1. 从 GitHub 下载 1Panel appstore 源码（`dev` 分支）
2. 解析每个应用的 `data.yml`，生成 `index.json`（元信息 + 版本号）
3. 为每个版本生成 `storage/{app}/{version}/meta.yml`（含 compose 原文、formFields）
4. 存在 compose 以外文件时生成 `init.zip`
5. 复制 `logo.png`、`README*.md` 到 `storage/{app}/`

### aaPanel 数据源

```bash
pip install pyyaml
python aapanel/build.py
```

`build.py` 执行步骤：

1. 从 GitHub 下载 aaPanel appstore 源码（`main` 分支）
2. 提取 `apps/` 到 `storage/apps/`，删除可执行脚本（`.sh`、`.py`、`.bat`、`.exe`）
3. 提取聚合元数据到 `storage/pkg/apps.json`
4. 保留根目录 `app_order.json`、`apptags.json`
5. 移除 `app.json` 中的域名字段，替换路径前缀

## 本地运行

```bash
# 1Panel 数据源
python -m http.server 8080 -d 1panel

# aaPanel 数据源
python -m http.server 8080 -d aapanel
```

访问 <http://localhost:8080>

## Docker 部署

```bash
# 1Panel 镜像（tag: 1panel）
docker run -d -p 8080:80 rehiy/appstore:1panel

# aaPanel 镜像（tag: latest / aapanel）
docker run -d -p 8080:80 rehiy/appstore:latest
```

### 自行构建

```bash
# 1Panel
docker build -f 1panel/Dockerfile -t appstore-1panel .

# aaPanel
docker build -f aapanel/Dockerfile -t appstore-aapanel .
```

Dockerfile 采用多阶段构建：

| 阶段 | 基础镜像 | 作用 |
|---|---|---|
| **builder** | `python:3.12-slim` | 运行 `build.py` 生成产物 |
| **nginx** | `nginx:alpine` | 托管 `index.html`、`index.json`、`storage/` |

## CI/CD

推送 `v*.*.*` 格式 tag 触发自动构建：

```bash
git tag v1.0.0 && git push origin v1.0.0
```

流水线：

1. 检出代码
2. Docker Buildx 构建多架构镜像（`linux/amd64` + `linux/arm64`）
3. 推送至 DockerHub

| 镜像 | 数据源 | 标签 |
|---|---|---|
| `rehiy/appstore:1panel` | 1Panel | `1panel` |
| `rehiy/appstore:latest` | aaPanel | `latest`、`aapanel` |

## 嵌入集成

应用市场可嵌入 iframe，安装时通过 `postMessage` 向父窗口发送数据：

```javascript
window.addEventListener('message', (event) => {
  if (event.data?.source === 'marketplace' && event.data?.type === 'install') {
    // event.data.name    — 容器实例名
    // event.data.compose — 插值完毕的 docker-compose.yml 文本
    // event.data.initURL — init.zip 下载地址（可选）
  }
});
```

系统变量 `APP_NAME` / `CONTAINER_NAME` / `NETWORK_NAME` 由前端自动注入。

## 技术栈

- **前端**：Vue 3 · Tailwind CSS · Marked · Font Awesome
- **构建**：Python 3.12 · PyYAML
- **服务**：Nginx Alpine · Docker Buildx
