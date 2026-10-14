"""保留连接声明，移除归档中可能存在的固定凭据。"""
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SENSITIVE = re.compile(r"token|secret|password|passwd|api[-_]?key|authorization|credential", re.I)
_VARIABLE = re.compile(r"\$\{[^}]+\}")


def sanitized_config(value):
    required = set()

    def credential(text, path):
        required.add(path)
        if isinstance(text, str) and _VARIABLE.fullmatch(text.strip()):
            return text
        return "<需自行配置>"

    def visit(node, path=""):
        if isinstance(node, dict):
            result = {}
            for key, child in node.items():
                child_path = path + "." + key if path else key
                if key in {"headers", "env"} and isinstance(child, dict):
                    result[key] = {name: credential(text, child_path + "." + name) for name, text in child.items()}
                elif _SENSITIVE.search(key) and not isinstance(child, (dict, list)):
                    result[key] = credential(child, child_path)
                else:
                    result[key] = visit(child, child_path)
            return result
        if isinstance(node, list):
            result = []
            for index, child in enumerate(node):
                child_path = path + "." + str(index)
                prior = node[index - 1] if index else None
                if isinstance(prior, str) and prior.startswith("--") and _SENSITIVE.search(prior):
                    result.append(credential(child, child_path))
                else:
                    result.append(visit(child, child_path))
            return result
        if isinstance(node, str) and node.startswith(("https://", "http://")):
            url = urlsplit(node)
            authority = url.netloc
            if url.username or url.password:
                authority = authority.rsplit("@", 1)[-1]
                required.add(path + ".userinfo")
            query = [(key, credential(text, path + "." + key) if _SENSITIVE.search(key) else text)
                     for key, text in parse_qsl(url.query, keep_blank_values=True)]
            return urlunsplit((url.scheme, authority, url.path, urlencode(query), url.fragment))
        if isinstance(node, str):
            return re.sub(r"(?i)(--(?:token|secret|password|api[-_]key|authorization)(?:\s+|=))(\S+)",
                          lambda match: match[1] + credential(match[2], path), node)
        return node

    return visit(value), sorted(required)
