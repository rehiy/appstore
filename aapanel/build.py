#!/usr/bin/env python3
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_STORAGE = BASE_DIR / "storage"
OUTPUT_APPS = OUTPUT_STORAGE / "apps"
OUTPUT_PKG = OUTPUT_STORAGE / "pkg"
SOURCE_URL = "https://github.com/aaPanel/appstore/archive/refs/heads/main.zip"
ZIP_PREFIX = "appstore-main/apps/"
PKG_PREFIX = "appstore-main/pkg/"
ROOT_PREFIX = "appstore-main/"
ROOT_KEEP = {
    'app_order.json',
    'apptags.json',
}
EXECUTABLE_EXTENSIONS = {'.sh', '.py', '.bat', '.exe', '.ps1', '.pl', '.cmd'}

# 不打包的文件（已有单独处理）
EXCLUDE_FILES = {'docker-compose.yml', 'app.json', 'README.md', '.env'}
# 不打包的文件扩展名（图标等静态资源）
EXCLUDE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg'}

# 正则表达式常量
COMPOSE_PATH_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*):-/www/dk_project/dk_app/[^}]+}')
JSON_PATH_PREFIX = '/www/dk_project/dk_app/'
DOMAIN_FIELD_ATTR = 'domain'
DOMAIN_FIELD_NAME = '域名'


def download_source(temp_dir: Path) -> Path:
    zip_path = temp_dir / "appstore.zip"
    print(f"[下载] {SOURCE_URL}")
    urllib.request.urlretrieve(SOURCE_URL, zip_path)
    print(f"[完成] 下载到 {zip_path}")
    return zip_path


def extract_apps(zip_path: Path) -> None:
    if OUTPUT_STORAGE.exists():
        print(f"[清理] 删除旧 storage: {OUTPUT_STORAGE}")
        shutil.rmtree(OUTPUT_STORAGE)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            # 跳过 .env 文件（已废弃，不再使用）
            if member.endswith('/.env') or member.endswith('/.env/'):
                continue
            if member.startswith(ZIP_PREFIX):
                rel_path = member[len(ZIP_PREFIX):]
                if not rel_path:
                    continue
                # 扁平化：去掉应用名子目录（如 redis/redis/file -> redis/file）
                parts = rel_path.split('/', 1)
                if len(parts) == 2 and parts[0] == parts[1].split('/')[0]:
                    rel_path = parts[1]  # 去掉第一个重复的应用名目录
                target = OUTPUT_APPS / rel_path
            elif member.startswith(PKG_PREFIX):
                rel_path = member[len(PKG_PREFIX):]
                if not rel_path:
                    continue
                target = OUTPUT_PKG / rel_path
            elif member.startswith(ROOT_PREFIX):
                rel_path = member[len(ROOT_PREFIX):]
                if rel_path in ROOT_KEEP:
                    target = OUTPUT_STORAGE / rel_path
                else:
                    continue
            else:
                continue
            if member.endswith('/'):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(target, 'wb') as dst:
                dst.write(src.read())
    print(f"[提取] 原始 aaPanel 应用存储到：{OUTPUT_APPS}")
    print(f"[提取] pkg 数据到：{OUTPUT_PKG}")
    print(f"[保留] 根目录文件：{', '.join(sorted(ROOT_KEEP))}")


def is_executable_file(path: Path) -> bool:
    if path.suffix.lower() in EXECUTABLE_EXTENSIONS:
        return True
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return bool(mode & 0o111)


def remove_executable_files() -> None:
    removed = 0
    for path in OUTPUT_APPS.rglob('*'):
        if path.is_file() and is_executable_file(path):
            path.unlink()
            removed += 1
    print(f"[清理] 删除可执行脚本文件：{removed} 个")


def _is_domain_field(field: object) -> bool:
    """判断是否是域名字段"""
    return (
        isinstance(field, dict) and 
        (field.get('attr') == DOMAIN_FIELD_ATTR or 
         DOMAIN_FIELD_NAME in str(field.get('name', '')))
    )


def _is_domain_env(env: object) -> bool:
    """判断是否是域名环境变量"""
    return (
        isinstance(env, dict) and 
        env.get('key') is not None and 
        'domain' in str(env.get('key', '')).lower()
    )


def remove_domain_fields() -> None:
    """从每个 app 的 app.json 中移除与域名相关的字段（attr=='domain' 或名称含'域名'）"""
    modified = 0
    for app_json_path in OUTPUT_APPS.rglob('app.json'):
        try:
            data = load_json(app_json_path)
            changed = False
            
            # 处理 field 数组
            if isinstance(data.get('field'), list):
                new_fields = [f for f in data['field'] if not _is_domain_field(f)]
                if len(new_fields) != len(data['field']):
                    data['field'] = new_fields
                    changed = True
            
            # 处理 env 数组
            if isinstance(data.get('env'), list):
                new_env = [e for e in data['env'] if not _is_domain_env(e)]
                if len(new_env) != len(data['env']):
                    data['env'] = new_env
                    changed = True
            
            if changed:
                with open(app_json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                modified += 1
        except Exception as e:
            print(f"[警告] 处理 {app_json_path} 时出错：{e}")
    print(f"[精简] 从 app.json 中移除域名字段：{modified} 个应用被修改")


def replace_path_prefix(obj: object) -> bool:
    """递归替换对象中所有字符串值中的 /www/dk_project/dk_app/ 前缀为 ."""
    changed = False
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and value.startswith(JSON_PATH_PREFIX):
                # 提取后面的相对路径部分（跳过 dk_app 和应用名）
                parts = value.split('/')
                if 'dk_app' in parts:
                    idx = parts.index('dk_app')
                    relative_parts = parts[idx + 2:]  # 跳过 dk_app 和应用名
                    obj[key] = './' + '/'.join(relative_parts) if relative_parts else '.'
                    changed = True
            elif replace_path_prefix(value):
                changed = True
    elif isinstance(obj, list):
        for item in obj:
            if replace_path_prefix(item):
                changed = True
    return changed


def modify_compose_config() -> None:
    """修改 docker-compose.yml 中的配置"""
    modified_files = 0
    for compose_file in OUTPUT_APPS.rglob('docker-compose.yml'):
        try:
            content = compose_file.read_text(encoding='utf-8')
            original_content = content
            
            content = content.replace('bt_apps', 'appstore')
            content = content.replace('baota_net', 'sdnet')
            
            # 替换 ${VAR:-/www/dk_project/dk_app/应用名/...} 为 ${VAR:-.}
            content = COMPOSE_PATH_PATTERN.sub(lambda m: f'${{{m.group(1)}:-.}}', content)
            
            if content != original_content:
                compose_file.write_text(content, encoding='utf-8')
                modified_files += 1
        except Exception as e:
            print(f"[警告] 处理 {compose_file} 时出错：{e}")
    print(f"[修改] 修改 docker-compose.yml 配置（createdBy/networks）：{modified_files} 个文件被修改")

def load_json(path: Path) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
        # 自动替换路径前缀，如果有修改则写回文件
        if replace_path_prefix(data):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    except Exception as e:
        print(f"[警告] 读取 JSON 失败：{path} -> {e}")
        return {}


def _ensure_has_app_files(app_dir: Path) -> None:
    """确保 app.json 中包含 has_app_files: true 字段"""
    app_json_path = app_dir / 'app.json'
    if not app_json_path.is_file():
        return
    try:
        with open(app_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
        if not data.get('has_app_files'):
            data['has_app_files'] = True
            with open(app_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [警告] 无法更新 {app_json_path}: {e}")


def package_app_files() -> None:
    """将每个应用的额外依赖文件打包为 app_files.zip，然后删除原始文件"""
    packaged = 0
    for app_dir in OUTPUT_APPS.iterdir():
        if not app_dir.is_dir():
            continue
        
        # 检查是否已有 app_files.zip，如果有则确保 app.json 中有 has_app_files 字段
        zip_path = app_dir / 'app_files.zip'
        if zip_path.is_file():
            _ensure_has_app_files(app_dir)
            packaged += 1
            continue
        
        # 收集所有需要打包的文件（应用根目录 + 子目录）
        all_files = []  # List of (file_path, arcname)
        sub_dirs = []
        
        for f in app_dir.iterdir():
            if f.is_file() and f.name not in EXCLUDE_FILES:
                if f.suffix.lower() not in EXCLUDE_EXTENSIONS:
                    all_files.append((f, f.name))
            elif f.is_dir() and f.name != '__pycache__':
                sub_dirs.append(f)
        
        # 收集子目录中的文件（保留子目录前缀）
        for sub_dir in sub_dirs:
            for f in sub_dir.iterdir():
                if f.is_file() and f.name not in EXCLUDE_FILES:
                    if f.suffix.lower() not in EXCLUDE_EXTENSIONS:
                        arcname = f"{sub_dir.name}/{f.name}"
                        all_files.append((f, arcname))
        
        # 打包所有文件到一个 app_files.zip
        if all_files:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f, arcname in all_files:
                    zf.write(f, arcname)
            # 删除已打包的原始文件
            for f, _ in all_files:
                f.unlink()
            # 删除已清空的子目录
            for sub_dir in sub_dirs:
                try:
                    sub_dir.rmdir()
                except OSError:
                    pass  # 目录非空，跳过
            packaged += 1
            print(f"  [打包] {app_dir.name}: {len(all_files)} 个文件 -> app_files.zip")
            
            # 在 app.json 中添加 has_app_files 字段
            _ensure_has_app_files(app_dir)
    
    if packaged > 0:
        print(f"[打包] 共 {packaged} 个应用版本打包了依赖文件")
    
    if packaged > 0:
        print(f"[打包] 共 {packaged} 个应用版本打包了依赖文件")


def slim_pkg_apps() -> None:
    pkg_file = OUTPUT_PKG / 'apps.json'
    if not pkg_file.is_file():
        return
    data = load_json(pkg_file)
    if not isinstance(data, list):
        print(f"[警告] pkg/apps.json 格式异常，跳过精简")
        return
    slim_fields = ['appname', 'apptitle', 'appdesc', 'appTypeCN', 'appversion', 'home', 'help', 'icon', 'appstatus', 'sort', 'appid', 'apptype']
    slim_data = []
    for item in data:
        slim_item = {k: item.get(k) for k in slim_fields if k in item}
        slim_data.append(slim_item)
    with open(pkg_file, 'w', encoding='utf-8') as f:
        json.dump(slim_data, f, ensure_ascii=False, indent=2)
    print(f"[精简] storage/pkg/apps.json 为列表元数据 ({len(slim_data)} apps)")


def build_versions(app_json: dict) -> dict:
    versions = {}
    for item in app_json.get('appversion', []) or []:
        m_version = item.get('m_version')
        if not m_version:
            continue
        m_version = str(m_version).strip()
        s_versions = item.get('s_version') or []
        if s_versions:
            for sv in s_versions:
                versions[f"{m_version}.{sv}"] = {}
        else:
            versions[m_version] = {}
    if not versions:
        versions['latest'] = {}
    return versions


def app_info_from_json(app_key: str, app_json: dict) -> dict:
    return {
        'name': app_json.get('appname') or app_key,
        'title': app_json.get('apptitle') or app_json.get('appname') or app_key,
        'description': app_json.get('appdesc') or app_json.get('help') or app_json.get('apptitle') or '',
        'website': app_json.get('home') or '',
        'tags': [app_json.get('appTypeCN')] if app_json.get('appTypeCN') else [],
        'versions': build_versions(app_json),
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = download_source(Path(tmp))
        extract_apps(zip_path)
    remove_executable_files()
    package_app_files()
    slim_pkg_apps()
    remove_domain_fields()
    modify_compose_config()
    if OUTPUT_PKG.exists() and not (OUTPUT_PKG / 'apps.json').is_file():
        print(f"[警告] 未生成预期的 storage/pkg/apps.json")
    if (BASE_DIR / 'index.json').exists():
        (BASE_DIR / 'index.json').unlink()
        print('[清理] 删除旧的 index.json')
    print('[完成] aapanel/storage/apps 和 aapanel/storage/pkg/apps.json 已更新')


if __name__ == '__main__':
    main()
