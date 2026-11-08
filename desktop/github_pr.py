"""Send for review: put the words added on this computer into a GitHub pull request.

Same steps as web/src/core/github.ts. The token is read from local/github_token.txt (git-ignored); it is never
written anywhere else and never logged.
"""
from __future__ import annotations

import base64
import json
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import newwords

GITHUB_REPO = "Greentears/WordsNSwords"
GITHUB_BASE = "main"
API = "https://api.github.com"
PARTS = ("words", "verbs", "nouns", "adjectives", "examples", "sentences")
EMPTY: dict[str, Any] = {"words": [], "verbs": [], "nouns": [], "adjectives": [], "examples": {}, "sentences": []}

# request(method, url, headers, body_bytes_or_None) -> (status, parsed_json_or_{})
Request = Callable[[str, str, dict, "bytes | None"], "tuple[int, Any]"]


class ApiError(Exception):
    pass


def _urllib_request(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, Any]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read()
            return res.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except (urllib.error.URLError, OSError) as exc:
        raise ApiError("No connection to GitHub.") from exc


def _explain(status: int, what: str) -> str:
    if status == 401:
        return "GitHub refused the token (wrong, expired or revoked). Make a new one and enter it again."
    if status == 403:
        return f"GitHub says the token may not do this ({what}). It needs Contents and Pull requests read & write on this repository."
    if status == 404:
        return f"GitHub could not find {what}. Check the repository name, and that the token has access to it."
    if status == 422:
        return f"GitHub did not accept the request ({what})."
    return f"GitHub answered {status} ({what})."


def _write(path: Path, data: Any, indent: int) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")


def _stamp(now: datetime) -> str:
    return now.strftime("%Y%m%d-%H%M")


def send_for_review(token: str, slug: str, deck: str, additions: list[dict], repo: str = GITHUB_REPO,
                    base: str = GITHUB_BASE, request: Request | None = None, now: datetime | None = None) -> dict:
    """Returns {"ok": True, "url", "branch", "files"} or {"ok": False, "error", "nothing_new"?}."""
    request = request or _urllib_request
    folder_path = f"users/{slug}/{deck}"

    def call(method: str, path: str, body: Any = None, ok_statuses: tuple[int, ...] = ()) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "WordsNSwords"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        status, payload = request(method, f"{API}/repos/{repo}{path}", headers, data)
        if not 200 <= status < 300 and status not in ok_statuses:
            raise ApiError(_explain(status, f"{method} {path.split('?')[0]}"))
        return status, payload

    try:
        if not token.strip():
            return {"ok": False, "error": "No token entered."}
        if not additions:
            return {"ok": False, "error": "Nothing to send: no words were added on this computer.", "nothing_new": True}
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            shas: dict[str, str] = {}
            original: dict[str, Any] = {}
            for part in PARTS:
                status, payload = call("GET", f"/contents/{folder_path}/{part}.json?ref={urllib.parse.quote(base)}", None, (404,))
                if status == 404:
                    if part == "words":
                        return {"ok": False, "error": f"There is no folder {folder_path} in the repository yet. Push your words there first."}
                    continue
                text = base64.b64decode(payload["content"]).decode("utf-8")
                shas[part] = payload["sha"]
                original[part] = json.loads(text)
                (work / f"{part}.json").write_text(text, encoding="utf-8")
            words_before = len(original["words"])
            for addition in additions:
                known = {w["word"] for w in json.loads((work / "words.json").read_text(encoding="utf-8"))}
                errors = newwords.validate(addition, known)
                if errors:
                    return {"ok": False, "error": f"An addition is no longer valid against the repository: {errors[0]}"}
                newwords.merge(work, addition)
            changed = []
            for part in PARTS:
                path = work / f"{part}.json"
                if not path.exists():
                    continue
                current = json.loads(path.read_text(encoding="utf-8"))
                if part in original and current == original[part]:
                    continue
                if part not in original and not current:
                    continue
                changed.append((part, path.read_text(encoding="utf-8")))
            if not changed:
                return {"ok": False, "error": "Everything you added is already in the repository.", "nothing_new": True}
            words_added = len(json.loads((work / "words.json").read_text(encoding="utf-8"))) - words_before

        _, ref = call("GET", f"/git/ref/heads/{base}")
        head = ref["object"]["sha"]
        now = now or datetime.now(timezone.utc)
        branch = f"add-words-{_stamp(now)}-{slug}"
        for n in range(2, 8):
            status, _ = call("POST", "/git/refs", {"ref": f"refs/heads/{branch}", "sha": head}, (422,))
            if status != 422:
                break
            branch = f"add-words-{_stamp(now)}-{slug}-{n}"
        else:
            return {"ok": False, "error": "Could not make a branch name that is free."}
        for part, text in changed:
            body = {"message": f"Add words for {slug} ({part})", "content": base64.b64encode(text.encode("utf-8")).decode("ascii"), "branch": branch}
            if part in shas:
                body["sha"] = shas[part]
            call("PUT", f"/contents/{folder_path}/{part}.json", body)
        plural = "" if words_added == 1 else "s"
        _, pr = call("POST", "/pulls", {
            "title": f"Add {words_added} word{plural} for {slug}", "head": branch, "base": base,
            "body": f"Words added from the WordsNSwords app by {slug} ({deck}).\n\nFiles: {', '.join(p + '.json' for p, _ in changed)}.",
        })
        return {"ok": True, "url": pr["html_url"], "branch": branch, "files": [p + ".json" for p, _ in changed]}
    except ApiError as exc:
        return {"ok": False, "error": str(exc)}


# ---- what is waiting to be sent, and the token (both stay in the git-ignored local/ folder)
def pending_path(workspace) -> Path:
    return workspace.local_dir / "pending.json"


def load_pending(workspace) -> list[dict]:
    try:
        data = json.loads(pending_path(workspace).read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_pending(workspace, additions: list[dict]) -> None:
    path = pending_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(additions, ensure_ascii=False), encoding="utf-8")


def token_path(root: Path) -> Path:
    return root / "local" / "github_token.txt"


def load_token(root: Path) -> str:
    try:
        return token_path(root).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_token(root: Path, token: str) -> None:
    path = token_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.strip(), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def remove_token(root: Path) -> None:
    token_path(root).unlink(missing_ok=True)


def combine(additions: list[dict]) -> dict:
    """Several answers as ONE answer (for 'Copy what I added')."""
    with tempfile.TemporaryDirectory() as tmp:
        for addition in additions:
            newwords.merge(tmp, addition)
        out = {}
        for part in PARTS:
            path = Path(tmp) / f"{part}.json"
            if path.exists():
                value = json.loads(path.read_text(encoding="utf-8"))
                if value:
                    out[part] = value
        return out
