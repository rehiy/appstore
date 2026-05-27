#!/usr/bin/env python3
import json
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
            if member.startswith(ZIP_PREFIX):
                rel_path = member[len(ZIP_PREFIX):]
                if not rel_path:
                    continue
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


def load_json(path: Path) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f) or {}
    except Exception as e:
        print(f"[警告] 读取 JSON 失败：{path} -> {e}")
        return {}


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
    slim_pkg_apps()
    if OUTPUT_PKG.exists() and not (OUTPUT_PKG / 'apps.json').is_file():
        print(f"[警告] 未生成预期的 storage/pkg/apps.json")
    if (BASE_DIR / 'index.json').exists():
        (BASE_DIR / 'index.json').unlink()
        print('[清理] 删除旧的 index.json')
    print('[完成] aapanel/storage/apps 和 aapanel/storage/pkg/apps.json 已更新')


if __name__ == '__main__':
    main()
