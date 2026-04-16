from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree

import requests


@dataclass(frozen=True)
class LiteratureDocument:
    source: str
    source_id: str
    title: str
    abstract: str = ""
    keywords: tuple[str, ...] = ()
    year: int | None = None
    journal: str = ""
    url: str = ""


@dataclass(frozen=True)
class CalculatorCategory:
    name: str
    target_count: int
    representative_calculators: tuple[str, ...]
    keywords: tuple[str, ...]


CATEGORY_DEFINITIONS: tuple[CalculatorCategory, ...] = (
    CalculatorCategory(
        name="心血管",
        target_count=13,
        representative_calculators=("CHA2DS2-VASc", "HAS-BLED", "ASCVD", "TIMI", "GRACE"),
        keywords=(
            "cha2ds2-vasc",
            "has-bled",
            "ascvd",
            "timi",
            "grace",
            "atrial fibrillation",
            "房颤",
            "stroke",
            "卒中",
            "bleeding",
            "出血",
            "acute coronary",
            "冠脉",
            "cardiovascular",
            "心血管",
        ),
    ),
    CalculatorCategory(
        name="代谢",
        target_count=7,
        representative_calculators=("FINDRISC", "CDRS", "代谢综合征评分"),
        keywords=(
            "findrisc",
            "cdrs",
            "metabolic syndrome",
            "代谢综合征",
            "diabetes risk",
            "糖尿病风险",
            "obesity",
            "肥胖",
            "glucose",
            "血糖",
        ),
    ),
    CalculatorCategory(
        name="老年",
        target_count=10,
        representative_calculators=("Morse 跌倒", "Braden 压疮", "MNA", "GDS-15"),
        keywords=(
            "morse",
            "braden",
            "mna",
            "gds-15",
            "fall risk",
            "跌倒",
            "pressure ulcer",
            "压疮",
            "geriatric",
            "老年",
            "nutrition assessment",
            "营养评估",
        ),
    ),
    CalculatorCategory(
        name="精神",
        target_count=2,
        representative_calculators=("PHQ-9", "GAD-7"),
        keywords=("phq-9", "gad-7", "depression", "抑郁", "anxiety", "焦虑", "mental health", "精神"),
    ),
    CalculatorCategory(
        name="呼吸",
        target_count=2,
        representative_calculators=("MMRC", "CAT"),
        keywords=("mmrc", "cat", "copd", "chronic obstructive", "呼吸", "肺功能", "dyspnea", "呼吸困难"),
    ),
    CalculatorCategory(
        name="神经",
        target_count=2,
        representative_calculators=("NIHSS", "Glasgow"),
        keywords=("nihss", "glasgow", "gcs", "stroke scale", "神经", "意识", "卒中评分"),
    ),
    CalculatorCategory(
        name="综合",
        target_count=14,
        representative_calculators=("NEWS", "qSOFA", "Barthel 指数"),
        keywords=(
            "news",
            "qsofa",
            "barthel",
            "activities of daily living",
            "日常生活能力",
            "综合评估",
            "early warning",
            "预警评分",
        ),
    ),
)


class MedicalCalculatorClassifier:
    def __init__(self, categories: tuple[CalculatorCategory, ...] | None = None) -> None:
        self.categories = categories or CATEGORY_DEFINITIONS

    def classify(self, document: LiteratureDocument) -> str | None:
        text = " ".join(
            [document.title, document.abstract, " ".join(document.keywords), document.journal]
        ).lower()
        best_name: str | None = None
        best_score = 0
        for category in self.categories:
            score = sum(3 for keyword in category.representative_calculators if keyword.lower() in text)
            score += sum(1 for keyword in category.keywords if keyword.lower() in text)
            if score > best_score:
                best_score = score
                best_name = category.name
        return best_name

    def summarize(self, documents: list[LiteratureDocument]) -> dict[str, Any]:
        counts = {category.name: 0 for category in self.categories}
        classified_documents: list[dict[str, Any]] = []
        unclassified = 0

        for document in documents:
            category_name = self.classify(document)
            if category_name:
                counts[category_name] += 1
            else:
                unclassified += 1
            classified_documents.append(
                {
                    "source": document.source,
                    "source_id": document.source_id,
                    "title": document.title,
                    "year": document.year,
                    "journal": document.journal,
                    "category": category_name,
                    "url": document.url,
                }
            )

        category_rows = [
            {
                "category": category.name,
                "matched_count": counts[category.name],
                "target_count": category.target_count,
                "representative_calculators": list(category.representative_calculators),
            }
            for category in self.categories
        ]

        return {
            "target_total": sum(category.target_count for category in self.categories),
            "matched_total": sum(counts.values()),
            "unclassified_count": unclassified,
            "categories": category_rows,
            "documents": classified_documents,
        }


class PubMedProvider:
    EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()
        self.api_key = os.getenv("NCBI_API_KEY")
        self.tool = os.getenv("NCBI_TOOL", "agentmd-home-health")
        self.email = os.getenv("NCBI_EMAIL", "")

    def search(
        self,
        query: str,
        *,
        max_results: int = 50,
        mindate: str | None = None,
        maxdate: str | None = None,
    ) -> list[LiteratureDocument]:
        ids = self._search_ids(query, max_results=max_results, mindate=mindate, maxdate=maxdate)
        if not ids:
            return []
        summaries = self._summaries(ids)
        abstracts = self._abstracts(ids)
        documents: list[LiteratureDocument] = []
        for pmid in ids:
            summary = summaries.get(pmid, {})
            documents.append(
                LiteratureDocument(
                    source="pubmed",
                    source_id=pmid,
                    title=str(summary.get("title", "")).strip(),
                    abstract=abstracts.get(pmid, ""),
                    keywords=tuple(summary.get("keywords", []) or ()),
                    year=_extract_year(summary.get("pubdate")),
                    journal=str(summary.get("fulljournalname", "") or summary.get("source", "")).strip(),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
        return documents

    def _search_ids(
        self,
        query: str,
        *,
        max_results: int,
        mindate: str | None,
        maxdate: str | None,
    ) -> list[str]:
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "sort": "relevance",
            "tool": self.tool,
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        if mindate or maxdate:
            params["datetype"] = "pdat"
            if mindate:
                params["mindate"] = mindate
            if maxdate:
                params["maxdate"] = maxdate
        response = self.session.get(f"{self.EUTILS_BASE}/esearch.fcgi", params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        return list(payload.get("esearchresult", {}).get("idlist", []))

    def _summaries(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
            "tool": self.tool,
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        response = self.session.get(f"{self.EUTILS_BASE}/esummary.fcgi", params=params, timeout=20)
        response.raise_for_status()
        payload = response.json().get("result", {})
        return {
            uid: payload.get(uid, {})
            for uid in ids
        }

    def _abstracts(self, ids: list[str]) -> dict[str, str]:
        params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": self.tool,
        }
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        response = self.session.get(f"{self.EUTILS_BASE}/efetch.fcgi", params=params, timeout=20)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        abstracts: dict[str, str] = {}
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID", default="").strip()
            abstract_texts = [
                "".join(node.itertext()).strip()
                for node in article.findall(".//Abstract/AbstractText")
                if "".join(node.itertext()).strip()
            ]
            if pmid:
                abstracts[pmid] = "\n".join(abstract_texts)
        return abstracts


class SinoMedProvider:
    def __init__(self, session: requests.Session | None = None, api_url_template: str | None = None) -> None:
        self.session = session or requests.Session()
        self.api_url_template = api_url_template or os.getenv("SINOMED_API_URL_TEMPLATE")
        self.auth_token = os.getenv("SINOMED_AUTH_TOKEN", "")
        self.cookie = os.getenv("SINOMED_COOKIE", "")

    def search(self, query: str, *, max_results: int = 50) -> list[LiteratureDocument]:
        if not self.api_url_template:
            raise RuntimeError(
                "SinoMed 查询需要配置 SINOMED_API_URL_TEMPLATE。"
                "官方站点说明提供基于 REST 的 API 接口服务，但公开页面未提供通用匿名调用文档。"
            )

        url = self.api_url_template.format(query=quote(query), page=1, page_size=max_results)
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if self.cookie:
            headers["Cookie"] = self.cookie

        response = self.session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        records = _pick_first_list(payload, ("results", "data", "records", "list", "items"))
        documents: list[LiteratureDocument] = []
        for item in records:
            title = _pick_first_value(item, ("title", "docTitle", "cnTitle", "articleTitle"))
            if not title:
                continue
            keywords = _normalize_keywords(_pick_first_value(item, ("keywords", "keyword", "meshTerms")))
            source_id = str(_pick_first_value(item, ("id", "docId", "pmid", "recordId")) or title)
            documents.append(
                LiteratureDocument(
                    source="sinomed",
                    source_id=source_id,
                    title=title,
                    abstract=str(_pick_first_value(item, ("abstract", "summary", "docAbstract")) or ""),
                    keywords=tuple(keywords),
                    year=_extract_year(_pick_first_value(item, ("year", "pubYear", "publishYear", "date"))),
                    journal=str(_pick_first_value(item, ("journal", "source", "journalTitle")) or ""),
                    url=str(_pick_first_value(item, ("url", "link")) or ""),
                )
            )
        return documents


class MedicalCalculatorLiteratureService:
    def __init__(
        self,
        *,
        pubmed_provider: PubMedProvider | None = None,
        sinomed_provider: SinoMedProvider | None = None,
        classifier: MedicalCalculatorClassifier | None = None,
    ) -> None:
        self.pubmed_provider = pubmed_provider or PubMedProvider()
        self.sinomed_provider = sinomed_provider or SinoMedProvider()
        self.classifier = classifier or MedicalCalculatorClassifier()

    def collect_statistics(
        self,
        query: str,
        *,
        sources: list[str] | None = None,
        max_results_each: int = 50,
        mindate: str | None = None,
        maxdate: str | None = None,
    ) -> dict[str, Any]:
        source_names = sources or ["pubmed", "sinomed"]
        all_documents: list[LiteratureDocument] = []
        provider_errors: list[dict[str, str]] = []

        for source_name in source_names:
            try:
                if source_name == "pubmed":
                    documents = self.pubmed_provider.search(
                        query,
                        max_results=max_results_each,
                        mindate=mindate,
                        maxdate=maxdate,
                    )
                elif source_name == "sinomed":
                    documents = self.sinomed_provider.search(query, max_results=max_results_each)
                else:
                    raise ValueError(f"Unsupported literature source: {source_name}")
                all_documents.extend(documents)
            except Exception as exc:
                provider_errors.append({"source": source_name, "error": str(exc)})

        summary = self.classifier.summarize(all_documents)
        summary.update(
            {
                "query": query,
                "sources": source_names,
                "provider_errors": provider_errors,
                "retrieved_total": len(all_documents),
            }
        )
        return summary


def _extract_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match:
        return int(match.group(0))
    return None


def _pick_first_list(payload: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _pick_first_list(value, keys)
            if nested:
                return nested
    return []


def _pick_first_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def _normalize_keywords(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    normalized = text.replace("；", ";").replace("，", ";").replace(",", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]
