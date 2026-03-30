import io
import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd

from azure_doc_processing.document_intelligence import (DocumentIntelligence,
                                                        fix_pdf_files)


class TestDocumentIntelligenceInit(unittest.TestCase):
    """Unit tests for DocumentIntelligence initialization."""

    @patch("azure_doc_processing.document_intelligence.DocumentIntelligenceClient")
    @patch("azure_doc_processing.document_intelligence.AzureKeyCredential")
    def test_init_with_key(self, mock_credential, mock_client_cls):
        """Should create client with AzureKeyCredential when key is provided."""
        di = DocumentIntelligence(endpoint="https://endpoint.cognitiveservices.azure.com", key="mykey")

        mock_credential.assert_called_once_with("mykey")
        mock_client_cls.assert_called_once()
        self.assertIsNotNone(di.client)

    @patch("azure_doc_processing.document_intelligence.DocumentIntelligenceClient")
    @patch("azure_doc_processing.document_intelligence.DefaultAzureCredential")
    def test_init_without_key(self, mock_credential, mock_client_cls):
        """Should create client with DefaultAzureCredential when key is not provided."""
        di = DocumentIntelligence(endpoint="https://endpoint.cognitiveservices.azure.com")

        mock_credential.assert_called_once()
        mock_client_cls.assert_called_once()
        self.assertIsNotNone(di.client)


class TestDocumentIntelligenceAnalyzeDoc(unittest.TestCase):
    """Unit tests for analyze_doc."""

    def _make_di(self):
        with patch("azure_doc_processing.document_intelligence.DocumentIntelligenceClient"):
            with patch("azure_doc_processing.document_intelligence.DefaultAzureCredential"):
                di = DocumentIntelligence(endpoint="https://endpoint.cognitiveservices.azure.com")
        di.client = MagicMock()
        return di

    def test_analyze_doc_with_url(self):
        """Should call begin_analyze_document with url_source."""
        di = self._make_di()
        mock_poller = MagicMock()
        mock_poller.result.return_value = {"content": "test"}
        di.client.begin_analyze_document.return_value = mock_poller

        result = di.analyze_doc(model_id="prebuilt-document", doc_url="https://blob/doc.pdf")

        di.client.begin_analyze_document.assert_called_once()
        self.assertEqual(result, {"content": "test"})

    def test_analyze_doc_with_bytes(self):
        """Should call begin_analyze_document with bytes_source."""
        di = self._make_di()
        mock_poller = MagicMock()
        mock_poller.result.return_value = {"content": "test"}
        di.client.begin_analyze_document.return_value = mock_poller

        result = di.analyze_doc(model_id="prebuilt-document", doc_bytes=b"fakepdf")

        di.client.begin_analyze_document.assert_called_once()
        self.assertIsNotNone(result)

    def test_analyze_doc_no_source_returns_none(self):
        """Should return None when neither url nor bytes is provided."""
        di = self._make_di()

        result = di.analyze_doc(model_id="prebuilt-document")

        self.assertIsNone(result)
        di.client.begin_analyze_document.assert_not_called()

    def test_analyze_doc_both_sources_returns_none(self):
        """Should return None when both url and bytes are provided."""
        di = self._make_di()

        result = di.analyze_doc(
            model_id="prebuilt-document",
            doc_url="https://blob/doc.pdf",
            doc_bytes=b"fakepdf",
        )

        self.assertIsNone(result)
        di.client.begin_analyze_document.assert_not_called()

    def test_analyze_doc_with_features(self):
        """Should pass features to begin_analyze_document."""
        di = self._make_di()
        mock_poller = MagicMock()
        mock_poller.result.return_value = {}
        di.client.begin_analyze_document.return_value = mock_poller

        di.analyze_doc(
            model_id="prebuilt-document",
            doc_url="https://blob/doc.pdf",
            features=["ocrHighResolution"],
        )

        call_kwargs = di.client.begin_analyze_document.call_args
        self.assertEqual(call_kwargs.kwargs.get("features") or call_kwargs[1].get("features"), ["ocrHighResolution"])


class TestDocumentIntelligenceProcessKeyValuePairs(unittest.TestCase):
    """Unit tests for process_key_value_pairs."""

    def _make_di(self):
        with patch("azure_doc_processing.document_intelligence.DocumentIntelligenceClient"):
            with patch("azure_doc_processing.document_intelligence.DefaultAzureCredential"):
                di = DocumentIntelligence(endpoint="https://endpoint.cognitiveservices.azure.com")
        return di

    def test_process_key_value_pairs(self):
        """Should extract key-value pairs from the result."""
        di = self._make_di()
        kv_pair_with_value = MagicMock()
        kv_pair_with_value.key.content = "Name"
        kv_pair_with_value.value.content = "John"

        kv_pair_without_value = MagicMock()
        kv_pair_without_value.key.content = "Phone"
        kv_pair_without_value.value = None

        result = {"keyValuePairs": [kv_pair_with_value, kv_pair_without_value]}

        processed = di.process_key_value_pairs(result)

        self.assertEqual(processed, {"Name": "John", "Phone": None})

    def test_process_key_value_pairs_empty(self):
        """Should return empty dict when no key-value pairs exist."""
        di = self._make_di()

        processed = di.process_key_value_pairs({})

        self.assertEqual(processed, {})


class TestDocumentIntelligenceProcessTables(unittest.TestCase):
    """Unit tests for process_tables."""

    def _make_di(self):
        with patch("azure_doc_processing.document_intelligence.DocumentIntelligenceClient"):
            with patch("azure_doc_processing.document_intelligence.DefaultAzureCredential"):
                di = DocumentIntelligence(endpoint="https://endpoint.cognitiveservices.azure.com")
        return di

    def test_process_tables(self):
        """Should convert table cells to a pandas DataFrame."""
        di = self._make_di()
        result = {
            "tables": [
                {
                    "rowCount": 3,
                    "columnCount": 2,
                    "cells": [
                        {"rowIndex": 0, "columnIndex": 0, "content": "Name"},
                        {"rowIndex": 0, "columnIndex": 1, "content": "Age"},
                        {"rowIndex": 1, "columnIndex": 0, "content": "Alice"},
                        {"rowIndex": 1, "columnIndex": 1, "content": "30"},
                        {"rowIndex": 2, "columnIndex": 0, "content": "Bob"},
                        {"rowIndex": 2, "columnIndex": 1, "content": "25"},
                    ],
                }
            ]
        }

        tables = di.process_tables(result)

        self.assertEqual(len(tables), 1)
        self.assertIsInstance(tables[0], pd.DataFrame)
        self.assertEqual(list(tables[0].columns), ["Name", "Age"])
        self.assertEqual(len(tables[0]), 2)
        self.assertEqual(tables[0].iloc[0]["Name"], "Alice")

    def test_process_tables_empty(self):
        """Should return empty list when no tables exist."""
        di = self._make_di()

        tables = di.process_tables({})

        self.assertEqual(tables, [])


class TestFixPdfFiles(unittest.TestCase):
    """Unit tests for fix_pdf_files."""

    @patch("azure_doc_processing.document_intelligence.os.remove")
    @patch("azure_doc_processing.document_intelligence.PdfWriter")
    @patch("azure_doc_processing.document_intelligence.PdfReader")
    @patch("builtins.open", mock_open())
    def test_fix_pdf_files_success(self, mock_reader, mock_writer, mock_remove):
        """Should read, rewrite, and upload each PDF file."""
        mock_datalake = MagicMock()
        mock_datalake.read_from_blob.return_value = io.BytesIO(b"fake pdf")

        mock_page = MagicMock()
        mock_reader.return_value.pages = [mock_page]

        result = fix_pdf_files(
            datalake=mock_datalake,
            pdf_files=["folder/attachments/file.pdf"],
            container="docs",
            tmp_dir="/tmp",
            tmp_cleanup=False,
        )

        self.assertEqual(len(result), 1)
        self.assertIn("file.pdf", result[0])
        mock_datalake.write_to_blob.assert_called_once()

    @patch("azure_doc_processing.document_intelligence.os.remove")
    @patch("azure_doc_processing.document_intelligence.PdfWriter")
    @patch("azure_doc_processing.document_intelligence.PdfReader")
    @patch("builtins.open", mock_open())
    def test_fix_pdf_files_with_cleanup(self, mock_reader, mock_writer, mock_remove):
        """Should remove temporary files when tmp_cleanup is True."""
        mock_datalake = MagicMock()
        mock_datalake.read_from_blob.return_value = io.BytesIO(b"fake pdf")
        mock_reader.return_value.pages = [MagicMock()]

        fix_pdf_files(
            datalake=mock_datalake,
            pdf_files=["folder/attachments/file.pdf"],
            container="docs",
            tmp_dir="/tmp",
            tmp_cleanup=True,
        )

        self.assertEqual(mock_remove.call_count, 2)

    def test_fix_pdf_files_error_handled(self):
        """Should catch exceptions and return an empty list for failed files."""
        mock_datalake = MagicMock()
        mock_datalake.read_from_blob.side_effect = Exception("read error")

        result = fix_pdf_files(
            datalake=mock_datalake,
            pdf_files=["path/file.pdf"],
            container="docs",
            tmp_dir="/tmp",
        )

        self.assertEqual(result, [])

    def test_fix_pdf_files_empty_list(self):
        """Should return empty list when no files are provided."""
        mock_datalake = MagicMock()

        result = fix_pdf_files(
            datalake=mock_datalake,
            pdf_files=[],
            container="docs",
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
