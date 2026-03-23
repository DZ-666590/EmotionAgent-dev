import json
from functools import lru_cache
from pathlib import Path

from loguru import logger

from ..config import settings
from ..domain.models import KnowledgeSnippet, NormalizedUserSignal


class KnowledgeService:
    """
    本地知识库检索服务。
    当前基于规则匹配从项目内置 JSON 语料中召回相关片段，后续可平滑替换为向量检索。
    """

    @classmethod
    def _knowledge_base_dir(cls) -> Path:
        return Path(__file__).resolve().parents[2] / "knowledge_base"

    @classmethod
    @lru_cache(maxsize=1)
    def _load_psyqa(cls) -> list[dict]:
        path = cls._knowledge_base_dir() / "PsyQA_example.json"
        if not path.exists():
            logger.warning("PsyQA knowledge file not found: {}", path)
            return []
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @classmethod
    @lru_cache(maxsize=1)
    def _load_dialog_guides(cls) -> list[dict]:
        path = cls._knowledge_base_dir() / "cn_data_version7.json"
        if not path.exists():
            logger.warning("Dialog knowledge file not found: {}", path)
            return []
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _build_terms(signal: NormalizedUserSignal, user_text: str) -> list[str]:
        terms: list[str] = []
        for item in signal.primary_emotions + signal.symptom_signals + signal.stressors + signal.risk_clues:
            value = (item or "").strip().lower()
            if value and value not in terms:
                terms.append(value)

        compact_text = user_text.strip().lower()
        if compact_text:
            terms.append(compact_text[:80])
        return terms

    @staticmethod
    def _trim_text(text: str) -> str:
        clean = " ".join((text or "").split())
        return clean[: settings.knowledge_max_excerpt_chars]

    @classmethod
    def _score_text(cls, text: str, terms: list[str], weight: float) -> float:
        haystack = (text or "").lower()
        score = 0.0
        for term in terms:
            if term and term in haystack:
                score += weight
        return score

    @classmethod
    def _search_psyqa(cls, terms: list[str]) -> list[KnowledgeSnippet]:
        results: list[KnowledgeSnippet] = []
        for item in cls._load_psyqa():
            answers = item.get("answers") or []
            best_answer = answers[0].get("answer_text", "") if answers else ""
            keyword_text = item.get("keywords", "")
            title = item.get("question", "未命名问题")
            body = "\n".join([
                item.get("description", ""),
                best_answer,
            ])
            score = 0.0
            score += cls._score_text(keyword_text, terms, 4.0)
            score += cls._score_text(title, terms, 3.0)
            score += cls._score_text(body, terms, 2.0)
            if score <= 0:
                continue
            results.append(
                KnowledgeSnippet(
                    source="PsyQA",
                    title=title,
                    content=cls._trim_text(body),
                    score=score,
                    metadata={
                        "keywords": keyword_text,
                        "question_id": item.get("questionID"),
                    },
                )
            )
        return results

    @classmethod
    def _search_dialog_guides(cls, terms: list[str]) -> list[KnowledgeSnippet]:
        results: list[KnowledgeSnippet] = []
        for item in cls._load_dialog_guides():
            title = item.get("topic") or item.get("psychotherapy") or "治疗对话"
            guide = item.get("guide", "")
            summary = item.get("summary", "")
            background = item.get("background", "")
            searchable = "\n".join([
                title,
                item.get("psychotherapy", ""),
                guide,
                summary,
                background,
            ])
            score = cls._score_text(searchable, terms, 1.5)
            if score <= 0:
                continue
            results.append(
                KnowledgeSnippet(
                    source="DialogueGuide",
                    title=title,
                    content=cls._trim_text("\n".join([guide, summary, background])),
                    score=score,
                    metadata={
                        "dialog_id": item.get("dialog_id"),
                        "psychotherapy": item.get("psychotherapy"),
                        "stage": item.get("stage"),
                    },
                )
            )
        return results

    @classmethod
    async def retrieve(
        cls,
        signal: NormalizedUserSignal,
        user_text: str
    ) -> list[KnowledgeSnippet]:
        if not settings.knowledge_enabled:
            return []

        terms = cls._build_terms(signal, user_text)
        if not terms:
            return []

        results = cls._search_psyqa(terms) + cls._search_dialog_guides(terms)
        results.sort(key=lambda item: item.score, reverse=True)
        top_results = results[: settings.knowledge_top_k]
        logger.info("Retrieved {} knowledge snippets", len(top_results))
        return top_results