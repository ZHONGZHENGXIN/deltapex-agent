import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.core.config import settings
from app.core.logging import get_structured_logger

logger = get_structured_logger("app.content_moderation")

RULES_PATH = Path(__file__).resolve().parents[1] / "core" / "content_moderation_rules.json"


@dataclass(frozen=True)
class ModerationResult:
    categories: tuple[str, ...]
    matched_keywords: tuple[str, ...]

    @property
    def has_financial_risk(self) -> bool:
        return "financial_risk" in self.categories

    @property
    def has_distress(self) -> bool:
        return "distress" in self.categories


class ContentModerationService:
    def __init__(self, rules_path: Path = RULES_PATH):
        self.rules_path = rules_path
        self.rules = _load_rules(rules_path)

    def inspect(self, text: str) -> ModerationResult:
        if not settings.CONTENT_MODERATION_ENABLED:
            return ModerationResult(categories=(), matched_keywords=())

        normalized = (text or "").casefold()
        categories: list[str] = []
        matched_keywords: list[str] = []

        for category, config in self.rules.items():
            keywords = config.get("keywords", [])
            matched = [keyword for keyword in keywords if keyword.casefold() in normalized]
            if matched:
                categories.append(category)
                matched_keywords.extend(matched)

        return ModerationResult(categories=tuple(categories), matched_keywords=tuple(sorted(set(matched_keywords))))

    def moderate_assistant_output(self, content: str, lang: str, *, user_id: int, chat_id: str | int) -> str:
        result = self.inspect(content)
        if not result.has_financial_risk:
            return content

        logger.warning(
            "assistant_output_financial_risk_detected",
            user_id=user_id,
            chat_id=chat_id,
            categories=result.categories,
            keyword_count=len(result.matched_keywords),
        )

        notice = get_investment_disclaimer(lang)
        if notice in content:
            return content
        return f"{content}\n\n{notice}"

    def build_distress_response(self, lang: str, *, user_id: int, chat_id: str | int, user_text: str) -> str:
        result = self.inspect(user_text)
        logger.warning(
            "user_distress_signal_detected",
            user_id=user_id,
            chat_id=chat_id,
            categories=result.categories,
            keyword_count=len(result.matched_keywords),
        )
        return get_distress_support_message(lang)


def _load_rules(rules_path: Path) -> dict[str, dict[str, Iterable[str]]]:
    with rules_path.open("r", encoding="utf-8") as rules_file:
        return json.load(rules_file)


def get_investment_disclaimer(lang: str) -> str:
    if lang == "en":
        return (
            "Compliance notice: AI content is for learning and research only and does not constitute investment "
            "advice. Please make independent decisions based on your own risk tolerance and consult a licensed "
            "professional when needed."
        )
    return "合规提示：AI 内容不构成投资建议，仅供学习参考。请结合自身风险承受能力独立判断，必要时咨询持牌专业人士。"


def get_distress_support_message(lang: str) -> str:
    contact = settings.COMPLIANCE_SUPPORT_CONTACT
    if lang == "en":
        return (
            "I noticed signs of severe stress or trading-loss distress. Please pause trading and contact a trusted "
            f"person or {contact} for human support. If you may harm yourself or someone else, contact local emergency "
            "services immediately. AI content cannot replace professional help."
        )
    return (
        "我注意到你可能正在经历严重压力或亏损情绪。请先暂停交易，并尽快联系可信赖的人或"
        f"{contact}获取人工支持。如果你可能伤害自己或他人，请立即联系当地紧急救援服务。AI 内容不能替代专业帮助。"
    )
