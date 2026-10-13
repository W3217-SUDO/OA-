"""Personal Office dependency installation; PM reviews before execute/rollback."""

import argparse
import base64
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.request import urlopen
from urllib.parse import urlsplit
from xml.etree import ElementTree
from cryptography.hazmat.primitives import serialization

IMAGE = "collabora/code@sha256:56541aad09403975646dfb87a3716e38afecce09b5f853391eb6d937a0ccd402"
EXPECTED_IMAGE_ID = "sha256:16cff53bb18c856f288a255c8f84cbec32fb5a0afdf52dd46b404ae868ccf2f7"
EXPECTED_ENTRYPOINT = [
    "/usr/bin/coolwsd",
    "--use-env-vars",
    "--o:sys_template_path=/opt/cool/systemplate",
    "--o:child_root_path=/opt/cool/child-roots",
    "--o:file_server_root_path=/usr/share/coolwsd",
    "--o:cache_files.path=/opt/cool/cache",
    "--o:logging.color=false",
    "--o:stop_on_config_change=true",
]
DOMAIN = "https://huzhilawfirm.com"
NAME = "sunhold-personal-collabora-20261014"
UNIT = Path("/etc/systemd/system/sunhold-oa-collabora.service")
NGINX = Path("/etc/nginx/sites-available/huzhi-oa")
ENV = Path("/opt/sunhold-oa/private/production-native.env")
STATE = Path("/opt/sunhold-oa/private/CODEX-personal-office-infra-20261014")
LOCKS = sorted(
    [
        Path("/opt/sunhold-oa/locks/formal-release.lock"),
        Path("/opt/sunhold-oa/releases/formal-release.lock"),
        Path("/opt/sunhold-oa/runtime/enterprise/formal-release.lock"),
    ]
)
CURRENT_INSTALL_OWNED = False
SNIPPET = """    # CODEX-personal-office-infra-20261014 begin
    location = /hosting/discovery {
        access_log off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:9980;
    }
    location = /hosting/capabilities {
        access_log off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:9980;
    }
    location ^~ /browser/ {
        access_log off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:9980;
    }
    location = /cool/adminws { return 404; }
    location ^~ /cool/ {
        access_log off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_pass http://127.0.0.1:9980;
    }
    location ^~ /api/v1/office/wopi/ {
        access_log off;
        client_max_body_size 21m;
        client_body_timeout 120s;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 120s;
        proxy_pass http://127.0.0.1:8001;
    }
    # CODEX-personal-office-infra-20261014 end

"""
UNIT_TEXT = """[Unit]
Description=Sunhold personal Office Collabora CODE pinned engine
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/docker start -a sunhold-personal-collabora-20261014
ExecStop=/usr/bin/docker stop -t 60 sunhold-personal-collabora-20261014
Restart=on-failure
RestartSec=10
TimeoutStopSec=75

[Install]
WantedBy=multi-user.target
"""


def digest(content):
    return hashlib.sha256(content).hexdigest()


def run(argv):
    return subprocess.check_output([str(x) for x in argv], stderr=subprocess.STDOUT, text=True, timeout=600).strip()


def runtime_commit():
    return json.loads(Path("/opt/sunhold-oa/runtime/enterprise/current/runtime-manifest.json").read_text())[
        "source_commit"
    ]


def require_idle_release_queue():
    states = {}
    with Path("/opt/sunhold-oa/releases/queue.tsv").open(newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row:
                continue
            if len(row) != 6:
                raise RuntimeError("release queue malformed; infrastructure change refused")
            states[row[0]] = row
    pending = [row[0] for row in states.values() if row[1] in {"assigned", "activating"}]
    if pending:
        raise RuntimeError("unresolved release queue; infrastructure change refused: " + ",".join(pending))


def atomic(path, content, mode):
    temporary = path.with_name(path.name + ".CODEX-personal-office-pending")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        dfd = os.open(path.parent, os.O_DIRECTORY | os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        temporary.unlink(missing_ok=True)


def save_state(state):
    atomic(STATE / "state.json", (json.dumps(state, indent=2) + "\n").encode(), 0o600)


def health():
    with urlopen(DOMAIN + "/health", timeout=15) as response:
        if response.status != 200 or json.load(response).get("status") != "ok":
            raise RuntimeError("OA health failed")


def discovery(url):
    with urlopen(url, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError("discovery HTTP status failed")
        content = response.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024 or b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise RuntimeError("invalid discovery envelope")
    root = ElementTree.fromstring(content)
    action = next(n for n in root.iter("action") if n.get("name") == "edit" and n.get("ext") == "docx")
    selected = urlsplit(action.get("urlsrc", ""))
    if selected.scheme != "https" or selected.netloc != "huzhilawfirm.com" or not selected.path.startswith("/browser/"):
        raise RuntimeError("discovery edit origin/path does not match configured same-origin HTTPS")
    proof = root.find("proof-key")
    if proof is None or not proof.get("modulus") or not proof.get("exponent"):
        raise RuntimeError("discovery proof unavailable")
    expected = (
        serialization.load_pem_private_key((STATE / "proof_key").read_bytes(), password=None)
        .public_key()
        .public_numbers()
    )
    supplied_n = int.from_bytes(base64.b64decode(proof.get("modulus"), validate=True), "big")
    supplied_e = int.from_bytes(base64.b64decode(proof.get("exponent"), validate=True), "big")
    if supplied_n != expected.n or supplied_e != expected.e:
        raise RuntimeError("discovery proof does not match the newly generated owned RSA key")
    return {
        "sha256": digest(content),
        "docx_edit_path_present": bool(action.get("urlsrc")),
        "proof_present": True,
        "owned_proof_match": True,
    }


def install(expected_nginx, expected_env, expected_runtime, resume=False):
    global CURRENT_INSTALL_OWNED
    if UNIT.exists():
        raise RuntimeError("owned unit already exists; do not overwrite")
    if STATE.exists() and not resume:
        raise RuntimeError("owned state exists; use guarded resume only after pull failure, or rollback")
    if runtime_commit() != expected_runtime:
        raise RuntimeError("runtime baseline drift")
    if digest(NGINX.read_bytes()) != expected_nginx or digest(ENV.read_bytes()) != expected_env:
        raise RuntimeError("preflight config drift")
    if run(["docker", "ps", "-a", "--filter", "name=^/" + NAME + "$", "--format", "{{.Names}}"]):
        raise RuntimeError("owned container name occupied")
    if ":9980" in run(["ss", "-lnt"]):
        raise RuntimeError("port 9980 already occupied")
    health()
    if resume:
        state = json.loads((STATE / "state.json").read_text())
        if (
            state["phase"] not in ("backup", "pull-failed")
            or state["container_created"]
            or state["unit_created"]
            or state["image"] != IMAGE
            or state["baseline_commit"] != expected_runtime
        ):
            raise RuntimeError("resume is restricted to verified pre-mutation pull failure")
        if (
            digest((STATE / "nginx.before").read_bytes()) != expected_nginx
            or digest((STATE / "native-env.before").read_bytes()) != expected_env
        ):
            raise RuntimeError("preserved backups mismatch")
    else:
        STATE.mkdir(mode=0o700)
        atomic(STATE / "nginx.before", NGINX.read_bytes(), 0o600)
        atomic(STATE / "native-env.before", ENV.read_bytes(), 0o600)
        state = {
            "phase": "backup",
            "image": IMAGE,
            "baseline_commit": expected_runtime,
            "nginx_before_sha256": expected_nginx,
            "env_before_sha256": expected_env,
            "container_created": False,
            "unit_created": False,
            "nginx_after_sha256": None,
            "env_after_sha256": None,
            "owner": "D-personal-office-20261014",
            "pid": os.getpid(),
        }
    save_state(state)
    CURRENT_INSTALL_OWNED = True
    try:
        run(["docker", "pull", IMAGE])
    except Exception:
        state["phase"] = "pull-failed"
        save_state(state)
        raise RuntimeError(
            "official image pull failed before OA mutations; preserved backups support guarded resume or rollback"
        ) from None
    inspected = json.loads(run(["docker", "image", "inspect", IMAGE]))[0]
    if inspected["Architecture"] != "amd64" or IMAGE not in inspected.get("RepoDigests", []):
        raise RuntimeError("fixed official image identity mismatch")
    if (
        inspected["Id"] != EXPECTED_IMAGE_ID
        or inspected["Config"].get("Entrypoint") != EXPECTED_ENTRYPOINT
        or inspected["Config"].get("Cmd") not in (None, [])
    ):
        raise RuntimeError("pinned image entrypoint/Cmd differs from independently verified registry config")
    proof_key = STATE / "proof_key"
    if not proof_key.exists():
        run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", proof_key])
        proof_key.chmod(0o400)
        os.chown(proof_key, 1001, 1001)
    # CODE is self-hosted free development edition, not a paid enterprise image.
    run(
        [
            "docker",
            "create",
            "--name",
            NAME,
            "--label",
            "oa.owner=personal-office-20261014",
            "--memory",
            "2g",
            "--memory-swap",
            "2g",
            "--cpus",
            "2",
            "--pids-limit",
            "512",
            "--cap-add",
            "MKNOD",
            "-p",
            "127.0.0.1:9980:9980",
            "--mount",
            f"type=bind,src={proof_key},dst=/etc/coolwsd/proof_key,readonly",
            IMAGE,
            "--o:server_name=huzhilawfirm.com",
            "--o:ssl.enable=false",
            "--o:ssl.termination=true",
            "--o:admin_console.enable=false",
            "--o:storage.wopi[@allow]=true",
            "--o:storage.wopi.alias_groups[@mode]=groups",
            "--o:storage.wopi.alias_groups.group[0].host=https://huzhilawfirm.com:443",
            "--o:storage.wopi.alias_groups.group[0].host[@allow]=true",
            "--o:security.enable_macros_execution=false",
            "--o:mount_jail_tree=false",
            "--o:ai.enabled=false",
            "--o:net.content_security_policy=frame-ancestors 'self'",
            "--o:logging.level=warning",
        ]
    )
    state.update(phase="container-created", container_created=True, image_id=inspected["Id"])
    save_state(state)
    state.update(unit_created=True, unit_sha256=digest(UNIT_TEXT.encode()))
    save_state(state)
    atomic(UNIT, UNIT_TEXT.encode(), 0o644)
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", "--now", "sunhold-oa-collabora"])
    failure = None
    for _ in range(60):
        try:
            state["loopback_discovery"] = discovery("http://127.0.0.1:9980/hosting/discovery")
            break
        except Exception as exc:
            failure = exc
            time.sleep(2)
    else:
        raise RuntimeError("CODE discovery never became ready") from failure
    original = NGINX.read_text()
    marker = "    location /api/ {\n"
    if original.count(marker) != 1 or "CODEX-personal-office-infra-20261014" in original:
        raise RuntimeError("nginx insertion point mismatch")
    replacement = original.replace(marker, SNIPPET + marker, 1).encode()
    state.update(phase="nginx-written", nginx_after_sha256=digest(replacement))
    save_state(state)
    atomic(NGINX, replacement, 0o644)
    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])
    state["public_discovery"] = discovery(DOMAIN + "/hosting/discovery")
    health()
    # Runtime bytes are preserved except explicit Office keys; secret is generated only here.
    before = ENV.read_bytes()
    if digest(before) != expected_env:
        raise RuntimeError("native env drift while preparing engine")
    allowed = {
        "OFFICE_PERSONAL_EDITOR_ENABLED": "true",
        "OFFICE_EDITOR_ENABLED": "false",
        "CODE_SERVER_URL": "http://127.0.0.1:9980",
        "CODE_BROWSER_URL": DOMAIN,
        "OFFICE_WOPI_BASE_URL": DOMAIN,
        "OFFICE_FRONTEND_ORIGIN": DOMAIN,
        "OFFICE_TRUSTED_ORIGINS": json.dumps(["http://127.0.0.1:9980", DOMAIN], separators=(",", ":")),
        "OFFICE_WOPI_TOKEN_SECRET": secrets.token_urlsafe(48),
    }
    original_lines = before.decode().splitlines(keepends=True)
    existing = {line.split("=", 1)[0] for line in original_lines if "=" in line and not line.startswith("#")}
    if existing.intersection(allowed):
        raise RuntimeError("Office settings now exist; re-review rather than overwrite")
    after = (
        before
        + (b"" if before.endswith(b"\n") else b"\n")
        + "".join(k + "=" + v + "\n" for k, v in allowed.items()).encode()
    )
    state.update(
        phase="configured-no-api-restart",
        env_after_sha256=digest(after),
        nonsecret_keys=[k for k in allowed if k != "OFFICE_WOPI_TOKEN_SECRET"],
        secret_generated=True,
    )
    save_state(state)
    atomic(ENV, after, 0o600)
    health()
    # Existing OA service is not restarted here; new settings load with final release activation.
    return {
        "phase": state["phase"],
        "image": IMAGE,
        "image_id": state["image_id"],
        "state_path": str(STATE / "state.json"),
        "nginx_sha256": state["nginx_after_sha256"],
        "native_env_sha256": state["env_after_sha256"],
        "loopback_discovery": state["loopback_discovery"],
        "public_discovery": state["public_discovery"],
        "case_editor_enabled": False,
        "personal_editor_configured": True,
    }


def rollback(expected_runtime):
    state = json.loads((STATE / "state.json").read_text())
    active = json.loads(Path("/opt/sunhold-oa/runtime/enterprise/current/runtime-manifest.json").read_text())
    if active["source_commit"] != expected_runtime:
        raise RuntimeError("third-party runtime drift; rollback refused")
    for path, key, before in [
        (ENV, "env_after_sha256", STATE / "native-env.before"),
        (NGINX, "nginx_after_sha256", STATE / "nginx.before"),
    ]:
        expected = state.get(key)
        if expected:
            if digest(path.read_bytes()) == digest(before.read_bytes()):
                continue
            if digest(path.read_bytes()) != expected:
                raise RuntimeError("third-party configuration drift; rollback refused")
            atomic(path, before.read_bytes(), 0o600 if path == ENV else 0o644)
    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])
    if state.get("unit_created") and UNIT.exists():
        if digest(UNIT.read_bytes()) != state["unit_sha256"]:
            raise RuntimeError("unit changed; stop refused")
        run(["systemctl", "disable", "--now", "sunhold-oa-collabora"])
        # Preserve the owned stopped container, pinned image and backups for recovery.
    run(["systemctl", "restart", "sunhold-oa-api", "sunhold-oa-web"])
    state.update(phase="rolled-back")
    save_state(state)
    health()
    return {"phase": "rolled-back", "owned_container_preserved": True, "backups_server_only": True}


parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["install", "resume", "rollback"])
parser.add_argument("--execute-approved", action="store_true")
parser.add_argument("--expected-nginx-sha256")
parser.add_argument("--expected-env-sha256")
parser.add_argument("--expected-runtime-commit")
args = parser.parse_args()
if not args.execute_approved:
    parser.error("PM-reviewed execution approval required")
if os.geteuid() != 0:
    raise RuntimeError("root execution required")
if args.action in ("install", "resume") and (not args.expected_nginx_sha256 or not args.expected_env_sha256):
    parser.error("explicit preflight hashes required")
if not args.expected_runtime_commit:
    parser.error("explicit expected current runtime SHA required")
held = []
try:
    for lock_path in LOCKS:
        handle = lock_path.open("r+")
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held.append(handle)
    if runtime_commit() != args.expected_runtime_commit:
        raise RuntimeError("runtime baseline drift under formal mutex")
    require_idle_release_queue()
    if args.action == "rollback":
        result = rollback(args.expected_runtime_commit)
    else:
        try:
            result = install(
                args.expected_nginx_sha256,
                args.expected_env_sha256,
                args.expected_runtime_commit,
                resume=args.action == "resume",
            )
        except Exception as installation_error:
            if CURRENT_INSTALL_OWNED and STATE.exists():
                state = json.loads((STATE / "state.json").read_text())
                if state["phase"] not in ("backup", "pull-failed"):
                    try:
                        rollback(args.expected_runtime_commit)
                    except Exception:
                        raise RuntimeError(
                            "installation failed; guarded rollback could not confirm recovery; inspect owned state without retry"
                        ) from None
            raise installation_error
    print(json.dumps(result, ensure_ascii=False))
finally:
    for handle in reversed(held):
        handle.close()
