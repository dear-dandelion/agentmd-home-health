from __future__ import annotations

import unittest

from app.literature.service import (
    LiteratureDocument,
    MedicalCalculatorClassifier,
    MedicalCalculatorLiteratureService,
    PubMedProvider,
    SinoMedProvider,
)


class FakeResponse:
    def __init__(self, *, json_data=None, text: str = "", status_code: int = 200) -> None:
        self._json_data = json_data
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):  # type: ignore[no-untyped-def]
        return self._json_data


class FakeSession:
    def __init__(self, responses):  # type: ignore[no-untyped-def]
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class LiteratureServiceTests(unittest.TestCase):
    def test_classifier_maps_documents_into_expected_categories(self) -> None:
        classifier = MedicalCalculatorClassifier()
        documents = [
            LiteratureDocument(source="pubmed", source_id="1", title="Validation of CHA2DS2-VASc in atrial fibrillation"),
            LiteratureDocument(source="pubmed", source_id="2", title="Use of FINDRISC for diabetes risk screening"),
            LiteratureDocument(source="pubmed", source_id="3", title="Morse fall scale in geriatric home care"),
            LiteratureDocument(source="pubmed", source_id="4", title="PHQ-9 as a depression screening tool"),
            LiteratureDocument(source="pubmed", source_id="5", title="MMRC dyspnea scale for COPD"),
            LiteratureDocument(source="pubmed", source_id="6", title="NIHSS score in acute stroke"),
            LiteratureDocument(source="pubmed", source_id="7", title="NEWS early warning score for home monitoring"),
        ]

        summary = classifier.summarize(documents)
        counts = {item["category"]: item["matched_count"] for item in summary["categories"]}

        self.assertEqual(counts["心血管"], 1)
        self.assertEqual(counts["代谢"], 1)
        self.assertEqual(counts["老年"], 1)
        self.assertEqual(counts["精神"], 1)
        self.assertEqual(counts["呼吸"], 1)
        self.assertEqual(counts["神经"], 1)
        self.assertEqual(counts["综合"], 1)

    def test_pubmed_provider_maps_esearch_esummary_and_efetch(self) -> None:
        session = FakeSession(
            [
                FakeResponse(json_data={"esearchresult": {"idlist": ["1001"]}}),
                FakeResponse(
                    json_data={
                        "result": {
                            "uids": ["1001"],
                            "1001": {
                                "uid": "1001",
                                "title": "CHA2DS2-VASc for stroke risk",
                                "pubdate": "2024 Jan",
                                "fulljournalname": "Test Journal",
                                "keywords": ["CHA2DS2-VASc", "atrial fibrillation"],
                            },
                        }
                    }
                ),
                FakeResponse(
                    text="""
                    <PubmedArticleSet>
                      <PubmedArticle>
                        <MedlineCitation>
                          <PMID>1001</PMID>
                          <Article>
                            <Abstract>
                              <AbstractText>Stroke risk score validation study.</AbstractText>
                            </Abstract>
                          </Article>
                        </MedlineCitation>
                      </PubmedArticle>
                    </PubmedArticleSet>
                    """
                ),
            ]
        )
        provider = PubMedProvider(session=session)

        documents = provider.search("CHA2DS2-VASc", max_results=1)

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].source, "pubmed")
        self.assertEqual(documents[0].source_id, "1001")
        self.assertIn("CHA2DS2-VASc", documents[0].title)
        self.assertIn("Stroke risk score", documents[0].abstract)
        self.assertEqual(documents[0].year, 2024)

    def test_sinomed_provider_parses_generic_json_records(self) -> None:
        session = FakeSession(
            [
                FakeResponse(
                    json_data={
                        "results": [
                            {
                                "id": "CN-1",
                                "title": "Morse跌倒风险量表在社区老年人中的应用",
                                "abstract": "用于老年居家跌倒风险初筛。",
                                "keywords": "Morse; 跌倒; 老年",
                                "year": "2023",
                                "journal": "中华老年医学杂志",
                                "url": "https://example.org/CN-1",
                            }
                        ]
                    }
                )
            ]
        )
        provider = SinoMedProvider(session=session, api_url_template="https://example.org/search?q={query}&page={page}&size={page_size}")

        documents = provider.search("跌倒 风险", max_results=5)

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].source, "sinomed")
        self.assertEqual(documents[0].source_id, "CN-1")
        self.assertEqual(documents[0].year, 2023)

    def test_literature_service_collects_provider_errors_without_failing(self) -> None:
        class StubPubMedProvider:
            def search(self, query, **kwargs):  # type: ignore[no-untyped-def]
                return [LiteratureDocument(source="pubmed", source_id="1", title="PHQ-9 depression screening")]

        class StubSinoMedProvider:
            def search(self, query, **kwargs):  # type: ignore[no-untyped-def]
                raise RuntimeError("SinoMed API not configured")

        service = MedicalCalculatorLiteratureService(
            pubmed_provider=StubPubMedProvider(),
            sinomed_provider=StubSinoMedProvider(),
        )

        result = service.collect_statistics("calculator", sources=["pubmed", "sinomed"], max_results_each=10)

        self.assertEqual(result["retrieved_total"], 1)
        self.assertEqual(len(result["provider_errors"]), 1)
        self.assertEqual(result["provider_errors"][0]["source"], "sinomed")


if __name__ == "__main__":
    unittest.main()
