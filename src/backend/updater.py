"""
GitHub Releases API から最新バージョンを取得・比較するロジック (バックエンド部分)
"""

import requests
from typing import Tuple, Optional


def check_for_updates(repo: str, current_version: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    GitHub Releases API から最新タグを取得し、現在バージョンと比較する。
    Returns:
        (has_update: bool, latest_tag: str | None, release_url: str | None)
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            raw_tag = data.get("tag_name", "")
            latest_tag = raw_tag.lstrip("v")
            html_url = data.get("html_url", f"https://github.com/{repo}/releases")

            if latest_tag and _is_newer_version(latest_tag, current_version):
                return True, latest_tag, html_url
    except Exception:
        pass
    return False, None, None


def _is_newer_version(latest: str, current: str) -> bool:
    """セマンティックバージョン比較 (例: '1.1.0' > '1.0.0')"""
    def parse(v: str):
        return [int(x) for x in v.split(".") if x.isdigit()]
    return parse(latest) > parse(current)
