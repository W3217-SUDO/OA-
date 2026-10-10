"""从已核验官方依赖层和 GitHub Debian 包构建隔离镜像，不操作 OA 服务。"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parent
SOURCE_INDEX = "sha256:3ab6ebc7c605e5a32b7ae3ff19daed4925090245acc8100ce2230bd766c88212"
SOURCE_MANIFEST = "sha256:e231bc62da8c1f0c1f78188f8c7e17e67716f38955d0ad1d703cf911ad6db84b"
DEB_SHA256 = "0860e68c4fecf429b4e13602a4a5ec6945e6ec9f0e9af9867ef0171845aa07df"
DEB_SIZE = 699704588
PACKAGE_VERSION = "9.4.0-129"
BASE_NAME = "sunhold-onlyoffice-dependencies:9.4.0.1"
BASE_LAYER_COUNT = 7
CTR = ["ctr", "--address", "/run/containerd/containerd.sock", "--namespace", "moby"]
UBUNTU_PACKAGES = {
    "logrotate": {"version": "3.21.0-2build1", "size": 52212, "sha256": "e609ad80a9cec135b404a84f99d9d87bc304800eb212702444a985527edba70c", "url": "https://archive.ubuntu.com/ubuntu/pool/main/l/logrotate/logrotate_3.21.0-2build1_amd64.deb"},
    "libpopt0": {"version": "1.19+dfsg-1build1", "size": 28562, "sha256": "b3e7ea5192e57c847b77c527d51f5b8d4bce47988d2ba326a5c3193f6d173ded", "url": "https://archive.ubuntu.com/ubuntu/pool/main/p/popt/libpopt0_1.19+dfsg-1build1_amd64.deb"},
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def descriptor(data: bytes, kind: str) -> dict:
    return {"mediaType": f"application/vnd.oci.image.{kind}.v1+json", "digest": "sha256:" + hashlib.sha256(data).hexdigest(), "size": len(data)}


def base_documents(index: dict, manifest: dict, config: dict) -> tuple[dict, dict]:
    selected = [item for item in index["manifests"] if item.get("platform", {}).get("os") == "linux" and item.get("platform", {}).get("architecture") == "amd64"]
    if len(selected) != 1 or selected[0]["digest"] != SOURCE_MANIFEST or len(manifest["layers"]) != 9:
        raise RuntimeError("官方 index、平台 manifest 或依赖层数量不一致")
    if config["architecture"] != "amd64" or config["os"] != "linux" or len(config["rootfs"]["diff_ids"]) != 9:
        raise RuntimeError("官方配置的平台或 rootfs 不一致")
    environment = dict(item.split("=", 1) for item in config["config"]["Env"])
    if environment.get("BASE_VERSION") != "24.04":
        raise RuntimeError("依赖底座不是已核验的 Ubuntu 24.04")
    result = copy.deepcopy(config)
    result["rootfs"]["diff_ids"] = result["rootfs"]["diff_ids"][:BASE_LAYER_COUNT]
    history = []
    count = 0
    for item in config["history"]:
        history.append(item)
        if not item.get("empty_layer", False):
            count += 1
        if count == BASE_LAYER_COUNT:
            break
    if count != BASE_LAYER_COUNT:
        raise RuntimeError("官方镜像历史不能对应依赖层")
    result["history"] = history
    # 依赖底座不继承编辑器 VOLUME，避免安装结果被匿名卷排除出镜像。
    result["config"] = {"Env": [f"{name}={environment[name]}" for name in ("PATH", "LANG", "LANGUAGE", "LC_ALL", "BASE_VERSION", "COMPANY_NAME", "PRODUCT_NAME", "DS_DOCKER_INSTALLATION", "DS_PLUGIN_INSTALLATION")], "Labels": {"org.sunhold.onlyoffice.source-index": SOURCE_INDEX, "org.sunhold.onlyoffice.source-manifest": SOURCE_MANIFEST}}
    data = encoded(result)
    base_manifest = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json", "config": descriptor(data, "config"), "layers": manifest["layers"][:BASE_LAYER_COUNT]}
    return result, base_manifest


def export_base(output: Path) -> None:
    if output.exists() or ROOT in output.resolve().parents:
        raise RuntimeError("导出文件必须是部署目录外的新临时文件")
    with tempfile.TemporaryDirectory(prefix="CODEX-onlyoffice-base-") as temporary:
        staging = Path(temporary)
        blobs = staging / "blobs/sha256"
        blobs.mkdir(parents=True)

        def fetch(digest: str) -> bytes:
            path = blobs / digest.partition(":")[2]
            with path.open("xb") as stream:
                subprocess.run([*CTR, "content", "get", digest], stdout=stream, check=True)
            if "sha256:" + sha256(path) != digest:
                raise RuntimeError("官方缓存 blob 摘要不一致")
            return path.read_bytes()

        index_bytes = fetch(SOURCE_INDEX)
        manifest_bytes = fetch(SOURCE_MANIFEST)
        manifest = json.loads(manifest_bytes)
        config_bytes = fetch(manifest["config"]["digest"])
        config, base_manifest = base_documents(json.loads(index_bytes), manifest, json.loads(config_bytes))
        for layer in base_manifest["layers"]:
            path = blobs / layer["digest"].partition(":")[2]
            with path.open("xb") as stream:
                subprocess.run([*CTR, "content", "get", layer["digest"]], stdout=stream, check=True)
            if path.stat().st_size != layer["size"] or "sha256:" + sha256(path) != layer["digest"]:
                raise RuntimeError("依赖层大小或摘要不一致")
        for data in (encoded(config), encoded(base_manifest)):
            (blobs / hashlib.sha256(data).hexdigest()).write_bytes(data)
        entry = {**descriptor(encoded(base_manifest), "manifest"), "annotations": {"org.opencontainers.image.ref.name": BASE_NAME}, "platform": {"os": "linux", "architecture": "amd64"}}
        (staging / "index.json").write_bytes(encoded({"schemaVersion": 2, "manifests": [entry]}))
        (staging / "oci-layout").write_bytes(encoded({"imageLayoutVersion": "1.0.0"}))
        with tarfile.open(output, "x") as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.add(path, arcname=str(path.relative_to(staging)), recursive=False)
    print(json.dumps({"base_archive_sha256": sha256(output), "bytes": output.stat().st_size, "manifest": entry["digest"], "editor_payload_included": False}))


def verify_base(path: Path, expected_sha256: str) -> tuple[dict, str]:
    if sha256(path) != expected_sha256:
        raise RuntimeError("传输后的依赖底座归档摘要不一致")
    with tarfile.open(path) as archive:
        def read_blob(digest: str) -> bytes:
            member = archive.extractfile("blobs/sha256/" + digest.partition(":")[2])
            if member is None:
                raise RuntimeError("OCI 归档缺少 blob")
            with member:
                data = member.read()
            if "sha256:" + hashlib.sha256(data).hexdigest() != digest:
                raise RuntimeError("OCI metadata 摘要不一致")
            return data

        index = json.loads(read_blob(SOURCE_INDEX))
        source = json.loads(read_blob(SOURCE_MANIFEST))
        config = json.loads(read_blob(source["config"]["digest"]))
        expected_config, expected_manifest = base_documents(index, source, config)
        root = json.load(archive.extractfile("index.json"))
        if len(root["manifests"]) != 1 or root["manifests"][0]["digest"] != descriptor(encoded(expected_manifest), "manifest")["digest"]:
            raise RuntimeError("导入 manifest 不是已核验的官方依赖子集")
        if read_blob(expected_manifest["config"]["digest"]) != encoded(expected_config):
            raise RuntimeError("底座配置与核验结果不一致")
        if read_blob(root["manifests"][0]["digest"]) != encoded(expected_manifest):
            raise RuntimeError("底座 manifest 与核验结果不一致")
        for layer in expected_manifest["layers"]:
            name = "blobs/sha256/" + layer["digest"].partition(":")[2]
            member = archive.extractfile(name)
            if member is None:
                raise RuntimeError("OCI 归档缺少依赖层")
            with member:
                actual = hashlib.file_digest(member, "sha256").hexdigest()
            if archive.getmember(name).size != layer["size"] or "sha256:" + actual != layer["digest"]:
                raise RuntimeError("导入依赖层摘要或大小不一致")
    return expected_config, descriptor(encoded(expected_manifest), "manifest")["digest"]


def build_image(base: Path, base_sha256: str, deb: Path, output: Path, dependencies: dict[str, Path]) -> None:
    if output.exists() or ROOT in output.resolve().parents:
        raise RuntimeError("来源回执必须写入部署目录外的新文件")
    config, base_manifest = verify_base(base, base_sha256)
    if deb.stat().st_size != DEB_SIZE or sha256(deb) != DEB_SHA256:
        raise RuntimeError("GitHub Debian 包与官方 release asset 摘要不一致")
    for field, expected in (("Package", "onlyoffice-documentserver"), ("Version", PACKAGE_VERSION), ("Architecture", "amd64")):
        if subprocess.check_output(["dpkg-deb", "--field", str(deb), field], text=True).strip() != expected:
            raise RuntimeError(f"GitHub Debian 包字段不一致：{field}")
    for name, metadata in UBUNTU_PACKAGES.items():
        path = dependencies[name]
        if path.stat().st_size != metadata["size"] or sha256(path) != metadata["sha256"]:
            raise RuntimeError(f"Ubuntu 官方依赖包摘要或大小不一致：{name}")
        for field, expected in (("Package", name), ("Version", metadata["version"]), ("Architecture", "amd64")):
            if subprocess.check_output(["dpkg-deb", "--field", str(path), field], text=True).strip() != expected:
                raise RuntimeError(f"Ubuntu 官方依赖包字段不一致：{name}/{field}")
    subprocess.run([*CTR, "images", "import", "--platform", "linux/amd64", str(base)], check=True)
    base_id = subprocess.check_output(["docker", "image", "inspect", base_manifest, "--format", "{{.Id}}"], text=True).strip()
    layers = json.loads(subprocess.check_output(["docker", "image", "inspect", base_id, "--format", "{{json .RootFS.Layers}}"], text=True))
    if layers != config["rootfs"]["diff_ids"]:
        raise RuntimeError("Docker 导入的实际依赖底座 rootfs 不一致")
    container = subprocess.check_output(["docker", "create", "--name", "CODEX-onlyoffice-install-" + uuid.uuid4().hex, "--network", "none", "--cpus", "2", "--memory", "4g", "--pids-limit", "512", "--entrypoint", "/bin/bash", base_id, "/tmp/sunhold-onlyoffice-install.sh"], text=True).strip()
    try:
        subprocess.run(["docker", "cp", str(deb), container + ":/tmp/onlyoffice.deb"], check=True)
        for name, path in dependencies.items():
            subprocess.run(["docker", "cp", str(path), container + f":/tmp/{name}.deb"], check=True)
        subprocess.run(["docker", "cp", str(ROOT / "install-github-deb.sh"), container + ":/tmp/sunhold-onlyoffice-install.sh"], check=True)
        subprocess.run(["docker", "start", "--attach", container], check=True, timeout=600)
        status = subprocess.check_output(["docker", "inspect", container, "--format", "{{.State.ExitCode}}"], text=True).strip()
        if status != "0":
            raise RuntimeError(f"隔离 Debian 包安装失败：exit {status}")
        labels = {"org.sunhold.onlyoffice.github-deb.sha256": DEB_SHA256, "org.sunhold.onlyoffice.package-version": PACKAGE_VERSION, "org.sunhold.onlyoffice.base-image": base_id}
        changes = ["ENTRYPOINT [\"/app/ds/run-document-server.sh\"]", "CMD []"]
        changes.extend(f"LABEL {key}={value}" for key, value in labels.items())
        command = ["docker", "commit"]
        for change in changes:
            command.extend(("--change", change))
        image_id = subprocess.check_output([*command, container], text=True).strip()
        actual = subprocess.check_output(["docker", "image", "inspect", image_id, "--format", "{{.Id}}"], text=True).strip()
        if actual != image_id:
            raise RuntimeError("最终构建 ImageID 不一致")
        receipt = {"image_id": image_id, "base_image_id": base_id, "base_archive_sha256": base_sha256, "source_index": SOURCE_INDEX, "source_manifest": SOURCE_MANIFEST, "github_deb_sha256": DEB_SHA256, "package_version": PACKAGE_VERSION, "github_asset_url": "https://github.com/ONLYOFFICE/DocumentServer/releases/download/v9.4.0/onlyoffice-documentserver_amd64.deb", "ubuntu_dependencies": UBUNTU_PACKAGES}
        with output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
        print(json.dumps(receipt))
    finally:
        subprocess.run(["docker", "rm", "--force", "--volumes", container], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    export = commands.add_parser("export-base")
    export.add_argument("--output", type=Path, required=True)
    build = commands.add_parser("build")
    build.add_argument("--base", type=Path, required=True)
    build.add_argument("--base-sha256", required=True)
    build.add_argument("--deb", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    for name in UBUNTU_PACKAGES:
        build.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.action == "export-base":
        export_base(args.output)
    else:
        build_image(args.base, args.base_sha256, args.deb, args.output, {name: getattr(args, name) for name in UBUNTU_PACKAGES})


if __name__ == "__main__":
    main()
