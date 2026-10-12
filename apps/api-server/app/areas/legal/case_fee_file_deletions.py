"""费用附件删除标记按原始账本键识别，不根据文件名猜测来源。"""


def fee_file_was_deleted(data: dict, *, attachment_id: int = 0, legacy_file_key: str = "") -> bool:
    markers = data.get("deleted_case_fee_files", [])
    if not isinstance(markers, list):
        raise ValueError("费用附件删除记录格式异常")
    return any(isinstance(marker, dict) and (
        (attachment_id and marker.get("attachment_id") == attachment_id)
        or (legacy_file_key and marker.get("legacy_file_key") == legacy_file_key)
    ) for marker in markers)
