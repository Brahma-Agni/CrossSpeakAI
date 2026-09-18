"""Regression checks for conversation memory and dynamic knowledge merging."""

from __future__ import annotations

import unittest

from langchain_core.documents import Document

from rag.pipeline import RAGPipeline
from rag.prompt_builder import PromptBuilder
from utils.language_detector import LanguageStyle


class _Detector:
    def detect(self, _: str) -> LanguageStyle:
        return LanguageStyle.GEN_Z


class _Retriever:
    def retrieve(self, query: str, score_threshold: float) -> list[Document]:
        return [
            Document(page_content="local duplicate", metadata={"term": "No Cap"}),
            Document(page_content="local term", metadata={"term": "Circle back"}),
        ]


class _API:
    prompt = ""

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return (
            '{"translation":"Honestly","normal_english":"To be honest",'
            '"terms_used":[],'
            '"detected_style":"Gen Z","translation_direction":'
            '"Gen Z Slang → Corporate English"}'
        )


class RAGExtensionTests(unittest.TestCase):
    def test_remote_terms_win_duplicates_and_memory_reaches_prompt(self) -> None:
        api = _API()
        remote = [
            Document(page_content="approved term", metadata={"term": "no cap"})
        ]
        pipeline = RAGPipeline(
            detector=_Detector(),
            retriever=_Retriever(),
            prompt_builder=PromptBuilder(max_context_docs=6),
            api_manager=api,
            extra_retriever=lambda _: remote,
        )

        result = pipeline.translate(
            "no cap",
            conversation_context=[
                {"input_text": "Previous input", "output_text": "Previous output"}
            ],
        )

        self.assertEqual(
            [doc.metadata["term"] for doc in result.retrieved_docs],
            ["no cap", "Circle back"],
        )
        self.assertIn("Previous input", api.prompt)
        self.assertIn("Previous output", api.prompt)
        self.assertEqual(result.normal_english, "To be honest")


if __name__ == "__main__":
    unittest.main()
