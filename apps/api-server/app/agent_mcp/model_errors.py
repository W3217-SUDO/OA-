"""保留模型错误分类和请求编号，不记录提示词、业务数据或凭据。"""

import logging
import re


logger = logging.getLogger(__name__)


def _identifier(value) -> str:
    text = str(value or "")
    return text[:128] if re.fullmatch(r"[a-zA-Z0-9_.:/\[\]-]*", text) else "redacted"


def model_error(response) -> RuntimeError:
    try:
        value = response.json()
    except ValueError:
        value = {}
    error = value.get("error", {}) if isinstance(value, dict) else {}
    error = error if isinstance(error, dict) else {}
    message = str(error.get("message") or "").casefold()
    context_limit = (
        "token" in message and any(term in message for term in ("exceed", "maximum", "too many", "limit"))
    ) or "context_length_exceeded" in str(error.get("code") or "")
    request_id = response.headers.get("x-request-id") or response.headers.get("x-tt-logid") or ""
    if not request_id:
        matched = re.search(r"request id:\s*([a-zA-Z0-9-]+)", str(error.get("message") or ""), re.I)
        request_id = matched.group(1) if matched else ""
    logger.warning(
        "model_request_rejected status=%s code=%s type=%s parameter=%s request_id=%s reason=%s",
        response.status_code, _identifier(error.get("code")), _identifier(error.get("type")),
        _identifier(error.get("param")), _identifier(request_id), "context_limit" if context_limit else "provider_rejected",
    )
    if context_limit:
        return RuntimeError(
            f"model_http_{response.status_code}：本轮资料超过模型输入上限，请使用全量统计、缩小明细查询范围或分批处理附件"
        )
    return RuntimeError(f"model_http_{response.status_code}")


def unsupported_stream(response) -> bool:
    if response.status_code in {404, 405, 415, 501}:
        return True
    if response.status_code not in {400, 422}:
        return False
    try:
        value = response.json()
    except ValueError:
        message = response.text.casefold()
    else:
        error = value.get("error", {}) if isinstance(value, dict) else {}
        message = str(error.get("message") or "").casefold() if isinstance(error, dict) else ""
    return "stream" in message and any(term in message for term in ("not supported", "unsupported", "not support"))
