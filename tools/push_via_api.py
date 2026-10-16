# -*- coding: utf-8 -*-
"""通过 api.github.com 的 Git Data API 将本地提交推送到远程（绕过被墙的 github.com:443）。

等价于 git push：逐个上传 blob → 构建 tree → 创建 commit → 创建/更新 ref。
- blob 内容取自本地 git 对象库（git cat-file），API 返回 sha 与本地比对自校验
- 已上传 blob 记录在 .push_state.json，网络中断后重跑可续传
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "thty36/rogue-tower-chinese"
API = f"https://api.github.com/repos/{REPO}"
BRANCH = "main"
STATE_FILE = ".push_state.json"


def gh_token():
    out = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True,
        env={**os.environ, "GCM_INTERACTIVE": "never", "GIT_TERMINAL_PROMPT": "0"},
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise SystemExit("no github token")


TOKEN = gh_token()


def api_call(method, url, payload=None, expect=(200, 201), retries=8, timeout=300):
    data = json.dumps(payload).encode() if payload is not None else None
    last_err = None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "rt-cn-push",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read() or b"{}")
                if r.status in expect:
                    return body
                raise RuntimeError(f"HTTP {r.status}: {str(body)[:200]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"HTTP {e.code}: {body}")
        except Exception as e:
            last_err = e
            wait = min(5 * (i + 1), 40)
            print(f"    网络错误({e})，{wait}s 后重试 {i+1}/{retries}")
            time.sleep(wait)
    raise RuntimeError(f"重试耗尽: {last_err}")


def git(*args, binary=False):
    r = subprocess.run(["git", *args], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode(errors='replace')[:200]}")
    return r.stdout if binary else r.stdout.decode().strip()


def main():
    local_tree = git("rev-parse", f"{BRANCH}^{{tree}}")
    entries = []
    for line in git("ls-tree", "-r", BRANCH).splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        entries.append((mode, typ, sha, path))
    # 小文件在前、大字体最后
    entries.sort(key=lambda e: int(git("cat-file", "-s", e[2])))
    print(f"local tree {local_tree[:12]}, {len(entries)} files")

    state = {}
    if os.path.exists(STATE_FILE):
        state = json.loads(open(STATE_FILE, encoding="utf-8").read())

    try:
        ref = api_call("GET", f"{API}/git/ref/heads/{BRANCH}", expect=(200,))
        remote_head = ref["object"]["sha"]
        print("remote main:", remote_head[:12])
    except Exception:
        remote_head = None
        print("remote main missing")

    tree_items = []
    for mode, typ, sha, path in entries:
        if state.get(path) == sha:
            print(f"  blob cached {sha[:10]} {path}")
        else:
            content = git("cat-file", "blob", sha, binary=True)
            b = api_call("POST", f"{API}/git/blobs", {
                "content": base64.b64encode(content).decode(),
                "encoding": "base64",
            })
            if b["sha"] != sha:
                raise SystemExit(f"blob sha mismatch for {path}: {sha} != {b['sha']}")
            state[path] = sha
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
            print(f"  blob ok {sha[:10]} {path}")
        tree_items.append({"path": path, "mode": mode, "type": "blob", "sha": sha})

    tree = api_call("POST", f"{API}/git/trees", {"tree": tree_items})
    if tree["sha"] != local_tree:
        raise SystemExit(f"tree sha mismatch: {local_tree} != {tree['sha']}")
    print("tree ok:", tree["sha"][:12])

    parents = [remote_head] if remote_head else []
    msg = git("log", "-1", "--pretty=%B")
    commit = api_call("POST", f"{API}/git/commits", {
        "message": msg, "tree": local_tree, "parents": parents,
    })
    print("commit ok:", commit["sha"][:12])

    if remote_head:
        api_call("PATCH", f"{API}/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
    else:
        api_call("POST", f"{API}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    print("ref updated")

    api_call("PATCH", f"https://api.github.com/repos/{REPO}", {"default_branch": BRANCH})
    print("default branch:", BRANCH)
    os.remove(STATE_FILE)
    print(f"DONE -> https://github.com/{REPO}")


if __name__ == "__main__":
    main()
