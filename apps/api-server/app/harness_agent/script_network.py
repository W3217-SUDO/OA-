"""技能专属 Docker 网络的规则生成与只读校验，不接触其他网络。"""

import hashlib
import ipaddress
import re
import shlex

LABEL = "com.huzhi.skill-runner"
_PRIVATE = ("0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
            "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24", "192.168.0.0/16", "198.18.0.0/15",
            "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4")


def identifiers(name):
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,40}", name):
        raise ValueError("技能网络名称无效")
    digest = hashlib.sha256(name.encode()).hexdigest()[:10]
    return "oas-" + digest, "OA_SKILL_" + digest.upper()


def network_rules(name, subnet):
    network = ipaddress.ip_network(subnet, strict=True)
    if network.version != 4 or not network.is_private or network.prefixlen < 24 or network.is_loopback or network.is_link_local:
        raise ValueError("技能网络必须使用独立的 IPv4 私有小网段")
    bridge, chain = identifiers(name)
    rules = [["-d", value, "-j", "REJECT"] for value in _PRIVATE]
    rules.extend([["-p", "tcp", "-m", "multiport", "--dports", "80,443", "-j", "ACCEPT"],
                  ["-d", "1.1.1.1/32", "-p", "udp", "--dport", "53", "-j", "ACCEPT"], ["-j", "REJECT"]])
    return bridge, chain, rules


def validate_network(name, value):
    configs = value.get("IPAM", {}).get("Config", [])
    if (value.get("Name") != name or value.get("Driver") != "bridge" or value.get("EnableIPv6") or value.get("Internal")
            or value.get("Labels", {}).get(LABEL) != "public-http-v1" or len(configs) != 1):
        raise ValueError("技能网络必须是管理员配置的专属 IPv4 公网受限网络")
    subnet = configs[0].get("Subnet", "")
    bridge, chain, rules = network_rules(name, subnet)
    if value.get("Options", {}).get("com.docker.network.bridge.name") != bridge:
        raise ValueError("技能网络的隔离网桥不匹配")
    return bridge, chain, rules, subnet


def _normalize(tokens):
    result, index = [], 0
    while index < len(tokens):
        if tokens[index:index + 2] in (["-m", "tcp"], ["-m", "udp"]):
            index += 2
        elif tokens[index] == "--reject-with":
            index += 2
        else:
            result.append(tokens[index])
            index += 1
    return result


def check_firewall(name, value, read):
    """检查完整规则及首条跳转，不能仅凭网络标签判定安全。"""
    bridge, chain, rules, subnet = validate_network(name, value)
    actual = [shlex.split(line) for line in read(["iptables", "-S", chain]).splitlines() if line.startswith("-A ")]
    expected = [["-A", chain, *rule] for rule in rules]
    if [_normalize(rule) for rule in actual] != [_normalize(rule) for rule in expected]:
        raise ValueError("技能网络出口规则缺失、被修改或顺序不符")
    for parent, expected_rule in (("DOCKER-USER", ["-A", "DOCKER-USER", "-s", subnet, "-j", chain]),
                                   ("INPUT", ["-A", "INPUT", "-i", bridge, "-j", "REJECT"])):
        entries = [shlex.split(line) for line in read(["iptables", "-S", parent]).splitlines() if line.startswith("-A ")]
        if not entries or _normalize(entries[0]) != _normalize(expected_rule):
            raise ValueError("技能网络必须优先阻断宿主与内网，防火墙首条规则不符")
