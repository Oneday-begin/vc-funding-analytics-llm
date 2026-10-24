"""Redacted secret checks for tracked, staged, or reachable Git history content.

This is a project guardrail, not a guarantee that every possible secret is detected.
Only locations and rule names are reported; matched values are never printed.
"""
import argparse
import fnmatch
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RULES = {
    "Groq API key": rb"gsk_[A-Za-z0-9]{20,}",
    "OpenAI style API key": rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}",
    "GitHub token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,})",
    "Google API key": rb"AIza[A-Za-z0-9_-]{30,}",
    "AWS access key identifier": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "Slack token": rb"xox[baprs]-[A-Za-z0-9-]{20,}",
    "Private key material": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    "Credentials embedded in URL": rb"(?:mysql(?:\+pymysql)?|postgres(?:ql)?|mongodb(?:\+srv)?|https?)://[^\s/:{}$]+:[^\s/@{}$]{4,}@",
}
ASSIGNMENT = re.compile(rb"(?i)[\"']?\b(?:[A-Z0-9_]*(?:PASSWORD|API_KEY|SECRET_KEY|ACCESS_TOKEN|AUTH_TOKEN|CLIENT_SECRET))[\"']?\s*[:=]\s*[\"']([^\"'\r\n]{8,})[\"']")
PLACEHOLDER = re.compile(rb"(?i)^(?:test[-_].*|your[-_].*|example[-_].*|dummy[-_].*|enter_privately.*|placeholder.*|<[^>]+>|\$\{.*|\{\{.*)$")
FORBIDDEN = (".env", ".env.*", "*.env", "*.env.*", "*.pem", "*.p12", "*.pfx", "*.key", "id_rsa", "id_ed25519", "*credentials*.json", "*service-account*.json", "*service_account*.json", "secrets.json", "*.db", "*.db-*", "*.sqlite", "*.sqlite-*", "*.sqlite3", "*.sqlite3-*")
EXAMPLE_FILES = {".env.example", ".env.sample", ".env.template"}


def git(*args, input=None):
    return subprocess.run(["git", *args], cwd=ROOT, input=input, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout


def forbidden_path(path):
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    return (name not in EXAMPLE_FILES and any(fnmatch.fnmatch(name, p) for p in FORBIDDEN)) or any(part in {".aws", ".ssh"} for part in normalized.split("/"))


def private_values():
    values = set()
    for path in ROOT.glob(".env*"):
        if not path.is_file() or path.name in EXAMPLE_FILES:
            continue
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if "=" not in raw or raw.lstrip().startswith("#"):
                continue
            key, value = raw.split("=", 1)
            if not re.search(r"(?i)password|secret|token|api_key|database_url", key):
                continue
            value = value.strip().strip("\"'").encode()
            if len(value) >= 4 and not PLACEHOLDER.fullmatch(value):
                values.add(value)
    for key in ("GROQ_API_KEY", "DB_PASSWORD"):
        value = os.getenv(key, "").strip().encode()
        if len(value) >= 4 and not PLACEHOLDER.fullmatch(value):
            values.add(value)
    return values


def inspect_content(data, values):
    if data.startswith(b"\x1f\x8b"):
        data = gzip.decompress(data)
    matches = []
    for value in values:
        at = data.find(value)
        if at >= 0:
            matches.append(("Exact match to a local private value", data[:at].count(b"\n") + 1))
    for label, pattern in TOKEN_RULES.items():
        for match in re.finditer(pattern, data):
            if not PLACEHOLDER.fullmatch(match.group()):
                matches.append((label, data[:match.start()].count(b"\n") + 1))
    for match in ASSIGNMENT.finditer(data):
        value = match.group(1).strip()
        if not PLACEHOLDER.fullmatch(value) and not any(x in value for x in (b"os.getenv", b"os.environ", b"process.env")):
            matches.append(("Literal assigned to a secret field", data[:match.start()].count(b"\n") + 1))
    return sorted(set(matches))


def audit(staged=False, history=False):
    values = private_values()
    findings, seen = [], set()
    files = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode().split("\0") if staged else git("ls-files", "-z").decode().split("\0")
    for path in filter(None, files):
        if forbidden_path(path):
            findings.append(dict(scope="staged" if staged else "tracked", path=path, rule="Private credential or runtime file must not be tracked"))
        data = git("show", ":" + path) if staged else (ROOT / path).read_bytes()
        for rule, line in inspect_content(data, values):
            findings.append(dict(scope="staged" if staged else "tracked", path=path, rule=rule, line=line))
    commit_count = 0
    if history:
        commit_count = int(git("rev-list", "--all", "--count"))
        objects = {}
        for line in git("rev-list", "--objects", "--all").decode().splitlines():
            oid, _, path = line.partition(" ")
            objects[oid] = path
        checked = git("cat-file", "--batch-check=%(objectname) %(objecttype)", input=("\n".join(objects) + "\n").encode()).decode()
        for entry in checked.splitlines():
            oid, kind = entry.split()
            if kind != "blob":
                continue
            seen.add(oid)
            path = objects[oid]
            if forbidden_path(path):
                findings.append(dict(scope="history", path=path, object=oid[:12], rule="Private credential or runtime file in reachable history"))
            for rule, line in inspect_content(git("cat-file", "blob", oid), values):
                findings.append(dict(scope="history", path=path, object=oid[:12], rule=rule, line=line))
    return dict(passed=not findings, revision=git("rev-parse", "HEAD").decode().strip(),
                tracked_or_staged_files=len(list(filter(None, files))), reachable_commits=commit_count,
                inspected_history_blobs=len(seen), known_private_values_checked=len(values), findings=findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.staged, args.history)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Secret check:", "PASS" if result["passed"] else "REVIEW REQUIRED")
        print("Files:", result["tracked_or_staged_files"], "| Reachable commits:", result["reachable_commits"], "| History blobs:", result["inspected_history_blobs"])
        for finding in result["findings"]:
            print(f"{finding['scope']}: {finding['path']}:{finding.get('line', '-')} - {finding['rule']}")
        print("Matched values are redacted. This check cannot prove the absence of every possible secret.")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
