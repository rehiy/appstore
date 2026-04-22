# AppStore — Docker 应用市场

基于 [1Panel AppStore](https://github.com/1Panel-dev/appstore) 数据源构建的 Docker 应用市场前端，提供可视化的应用浏览、搜索和安装体验。

## 功能特性

- **应用浏览** — 分类展示所有可用应用，支持搜索过滤
- **详情查看** — 查看应用介绍、版本列表、README 文档
- **一键安装** — 填写配置后生成安装脚本或通过 `postMessage` 与父窗口通信
- **响应式设计** — 适配桌面端和移动端
- **懒加载优化** — 图片按需加载，提升首屏性能

## 项目结构

```
appstore/
├── .github/
│   └── workflows/
│       └── release.yml      # CI/CD：打 tag 自动构建 Docker 镜像并推送
├── 1panel/
│   ├── build.py             # 构建脚本：下载源码 → 生成 index.json + storage/
│   ├── Dockerfile           # 多阶段构建：Python 构建 + Nginx 运行
│   ├── index.html           # 前端单页应用（Vue 3 + Tailwind CSS）
│   └── README.md            # 前端详细说明
└── README.md                # 本文件
```

## 构建流程

`build.py` 执行以下步骤：

1. 从 GitHub 下载 1Panel AppStore 源码（`dev` 分支）
2. 解析每个应用的 `data.yml`，生成 `index.json`（仅含元信息与版本号）
3. 为每个版本在 `storage/{app}/{version}/` 下生成：
   - `meta.yml` — 包含 `compose`（原始模板，含 `${VAR}` 占位符）、`formFields`（表单字段定义）、可选 `init`（附加运行文件）
   - `init.zip` — 仅当存在 compose 以外的运行时文件时生成
4. 复制应用级静态文件（`logo.png`、`README*.md`）到 `storage/{app}/`

### 本地构建

```bash
pip install pyyaml
python 1panel/build.py
```

构建产物：`1panel/index.json` + `1panel/storage/`

### 本地运行

```bash
# 使用 Python
python -m http.server 8080 -d 1panel

# 或使用 Node.js
npx serve 1panel
```

访问 <http://localhost:8080>

## Docker 部署

```bash
docker run -d -p 8080:80 rehiy/appstore
```

### 自行构建镜像

```bash
docker build -f 1panel/Dockerfile -t appstore .
```

Dockerfile 采用多阶段构建：

1. **构建阶段** — `python:3.12-slim`，运行 `build.py` 生成 `index.json` 和 `storage/`
2. **运行阶段** — `nginx:alpine`，托管 `index.html`、`index.json` 和 `storage/`

## CI/CD

推送到 GitHub 时，打 `v*.*.*` 格式的 tag 即触发自动构建：

```bash
git tag v1.0.0
git push origin v1.0.0
```

流水线会：

1. 检出代码
2. 使用 Docker Buildx 构建多架构镜像（`amd64` + `arm64`）
3. 推送到 DockerHub，同时打 `latest` 和版本号标签

## 嵌入集成

应用市场支持被嵌入到 iframe 中，安装时通过 `postMessage` 向父窗口发送结构化数据：

```javascript
// 父窗口监听
window.addEventListener('message', (event) => {
  if (event.data?.source === 'marketplace' && event.data?.type === 'install') {
    console.log('安装应用:', event.data);
    // event.data.name      — 实例名
    // event.data.compose   — 前端插值完毕的 docker-compose.yml 文本
    // event.data.initURL   — 附加运行文件 init.zip 的下载地址（可选）
  }
});
```

系统变量 `APP_NAME` / `CONTAINER_NAME` / `NETWORK_NAME`（默认 `app-network`）由前端自动注入，父窗口无需关心。

## 技术栈

- **Vue 3** — 渐进式 JavaScript 框架
- **Tailwind CSS** — 实用优先的 CSS 框架
- **Marked** — Markdown 解析器
- **Font Awesome** — 图标库
- **Python PyYAML** — YAML 解析与生成
- **Nginx** — 静态文件服务
- **Docker Buildx** — 多架构镜像构建

## 致谢

- [1Panel AppStore](https://github.com/1Panel-dev/appstore) — 提供丰富的 Docker 应用模板和配置文件
- [GitHub Markdown CSS](https://github.com/sindresorhus/github-markdown-css) — GitHub 风格 Markdown 样式
