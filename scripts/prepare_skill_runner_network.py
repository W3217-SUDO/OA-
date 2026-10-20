"""管理员显式准备技能专属公网网络；不部署代码，不修改其他 Docker 网络。"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api-server"))
from app.harness_agent.script_network import LABEL, check_firewall, network_rules, validate_network


def execute(arguments):
    return subprocess.run(arguments, check=True, capture_output=True, text=True, timeout=15).stdout


def main():
    parser = argparse.ArgumentParser(description="仅创建或核验技能专属网络和精确出口规则")
    parser.add_argument("--network", required=True)
    parser.add_argument("--subnet", required=True)
    options = parser.parse_args()
    if sys.platform != "linux" or os.geteuid() != 0:
        raise SystemExit("必须由 Linux 管理员显式运行")
    bridge, chain, rules = network_rules(options.network, options.subnet)
    names = execute(["docker", "network", "ls", "--format", "{{.Name}}"]).splitlines()
    if options.network not in names:
        execute(["docker", "network", "create", "--driver", "bridge", "--subnet", options.subnet,
                 "--opt", "com.docker.network.bridge.name=" + bridge,
                 "--opt", "com.docker.network.bridge.enable_icc=false", "--label", LABEL + "=public-http-v1", options.network])
    value = json.loads(execute(["docker", "network", "inspect", options.network]))[0]
    _, _, _, actual_subnet = validate_network(options.network, value)
    if actual_subnet != options.subnet:
        raise SystemExit("已有技能网络网段不符，未修改")
    existing = execute(["iptables", "-S"])
    if "-N " + chain not in existing.splitlines():
        execute(["iptables", "-N", chain])
    else:
        current = execute(["iptables", "-S", chain])
        if any(line.startswith("-A ") for line in current.splitlines()):
            # 已存在的网络只核验，不清空或覆盖管理员规则。
            check_firewall(options.network, value, execute)
            print("技能专属网络和防火墙规则核验通过")
            return
    for rule in rules:
        execute(["iptables", "-A", chain, *rule])
    execute(["iptables", "-I", "DOCKER-USER", "1", "-s", options.subnet, "-j", chain])
    execute(["iptables", "-I", "INPUT", "1", "-i", bridge, "-j", "REJECT"])
    check_firewall(options.network, value, execute)
    print("技能专属网络已配置；仅准公网 HTTP/HTTPS 与指定 DNS，宿主、内网和元数据均被阻断")


if __name__ == "__main__":
    main()
