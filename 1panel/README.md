# Docker 应用市场

现代化的 Docker 应用商店前端，提供可视化的应用浏览、搜索和安装体验。

## 快速开始

```bash
# 本地运行
python -m http.server 8080

# Docker 部署
docker run -d -p 8080:80 rehiy/appstore
```

## 构建说明

```bash
pip install pyyaml
python build.py
```

构建产物：`index.json`（应用元信息）+ `storage/`（版本详情）

## 嵌入集成

支持 iframe 嵌入，通过 `postMessage` 通信：

```javascript
window.addEventListener('message', (event) => {
  if (event.data?.source === 'marketplace' && event.data?.type === 'install') {
    // event.data.name    — 实例名
    // event.data.compose — docker-compose.yml 文本
    // event.data.initURL — 附加文件下载地址（可选）
  }
});
```

系统变量 `APP_NAME` / `CONTAINER_NAME` / `NETWORK_NAME` 由前端自动注入。

## 致谢

- [1Panel AppStore](https://github.com/1Panel-dev/appstore) — 提供丰富的 Docker 应用模板和配置文件
