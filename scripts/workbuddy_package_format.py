"""能力包的原始文本格式和分类，不执行包内代码。"""
import yaml


REPOSITORY = "https://github.com/infometa/workbuddyskills"
CATEGORIES = {"01-ProductDesign": "产品设计", "02-Engineering": "技术工程", "03-GameSpatial": "游戏空间",
              "04-DataAI": "数据智能", "05-MarketingGrowth": "营销增长", "06-ContentCreative": "内容创作",
              "07-SalesCommerce": "销售商务", "08-FinanceInvestment": "金融投资", "09-OperationsHR": "运营人力",
              "10-ProjectQuality": "项目质量", "11-SecurityCompliance": "法务安全", "12-IndustryConsultant": "行业顾问",
              "13-TencentZone": "腾讯专区", "14-WorldWise": "全球发展", "15-Education": "教育学习"}


def license_kind(text):
    if "MIT License" in text and "Permission is hereby granted" in text:
        return "MIT"
    if "Apache License" in text and "Version 2.0" in text and "Grant of Copyright License" in text:
        return "Apache-2.0"
    return None


def localized(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("zh") or value.get("en") or "").strip()
    return ""


def markdown(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        metadata = yaml.safe_load("".join(lines[1:end]))
        if not isinstance(metadata, dict):
            raise ValueError("元数据不是键值对象")
        return metadata, "".join(lines[end + 1:]).strip()
    return {}, text.strip()
