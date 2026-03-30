import unittest
from unittest.mock import patch

from langchain_openai import AzureChatOpenAI

from azure_doc_processing.openai_service import OpenAIDeployment


class TestOpenAIDeploymentInit(unittest.TestCase):
    """Unit tests for OpenAIDeployment initialization."""

    @patch("azure_doc_processing.openai_service.AzureChatOpenAI")
    def test_init_with_api_key(self, mock_chat_cls):
        """Should create AzureChatOpenAI client with api_key when provided."""
        deployment = OpenAIDeployment(
            endpoint="https://my-openai.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
            api_key="test-key",
        )

        mock_chat_cls.assert_called_once_with(
            azure_endpoint="https://my-openai.openai.azure.com",
            openai_api_key="test-key",
            openai_api_version="2024-02-01",
            deployment_name="gpt-4",
            temperature=0.0,
        )
        self.assertIsNotNone(deployment.client)

    @patch("azure_doc_processing.openai_service.AzureChatOpenAI")
    @patch("azure_doc_processing.openai_service.get_bearer_token_provider")
    @patch("azure_doc_processing.openai_service.DefaultAzureCredential")
    def test_init_with_default_credential(
        self, mock_credential, mock_token_provider, mock_chat_cls
    ):
        """Should use DefaultAzureCredential when no api_key is provided."""
        mock_token_provider.return_value = "token_provider_func"

        deployment = OpenAIDeployment(
            endpoint="https://my-openai.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
        )

        mock_credential.assert_called_once()
        mock_token_provider.assert_called_once()
        mock_chat_cls.assert_called_once()
        self.assertIsNotNone(deployment.client)

    @patch("azure_doc_processing.openai_service.AzureChatOpenAI")
    def test_model_defaults_to_deployment_name(self, mock_chat_cls):
        """Model should default to deployment_name when model is not provided."""
        deployment = OpenAIDeployment(
            endpoint="https://my-openai.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4o",
            api_key="key",
        )

        self.assertEqual(deployment.model, "gpt-4o")

    @patch("azure_doc_processing.openai_service.AzureChatOpenAI")
    def test_model_override(self, mock_chat_cls):
        """Model should use the explicit model parameter when provided."""
        deployment = OpenAIDeployment(
            endpoint="https://my-openai.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4o",
            api_key="key",
            model="gpt-4o-mini",
        )

        self.assertEqual(deployment.model, "gpt-4o-mini")

    @patch("azure_doc_processing.openai_service.AzureChatOpenAI")
    def test_custom_temperature(self, mock_chat_cls):
        """Should pass custom temperature to AzureChatOpenAI."""
        OpenAIDeployment(
            endpoint="https://my-openai.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
            api_key="key",
            temperature=0.7,
        )

        call_kwargs = mock_chat_cls.call_args
        self.assertEqual(
            call_kwargs.kwargs.get("temperature") or call_kwargs[1].get("temperature"),
            0.7,
        )

    @patch("azure_doc_processing.openai_service.AzureChatOpenAI")
    @patch("azure_doc_processing.openai_service.get_bearer_token_provider")
    @patch("azure_doc_processing.openai_service.DefaultAzureCredential")
    def test_token_provider_scope(self, mock_credential, mock_token_provider, mock_chat_cls):
        """Should request the cognitiveservices scope for DefaultAzureCredential."""
        OpenAIDeployment(
            endpoint="https://my-openai.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
        )

        mock_token_provider.assert_called_once_with(
            mock_credential.return_value,
            "https://cognitiveservices.azure.com/.default",
        )


class TestOpenAIDeploymentLangchainCompatibility(unittest.TestCase):
    """Smoke tests that verify the real AzureChatOpenAI class still accepts the parameters used by OpenAIDeployment."""

    def test_api_key_path_creates_real_client(self):
        """AzureChatOpenAI should still accept the kwargs used in the api_key code path."""
        deployment = OpenAIDeployment(
            endpoint="https://fake-endpoint.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
            api_key="fake-key-for-testing",
        )

        self.assertIsInstance(deployment.client, AzureChatOpenAI)

    @patch("azure_doc_processing.openai_service.get_bearer_token_provider")
    @patch("azure_doc_processing.openai_service.DefaultAzureCredential")
    def test_default_credential_path_creates_real_client(
        self, mock_credential, mock_token_provider
    ):
        """AzureChatOpenAI should still accept the kwargs used in the token-provider code path."""
        mock_token_provider.return_value = lambda: "fake-token"

        deployment = OpenAIDeployment(
            endpoint="https://fake-endpoint.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
        )

        self.assertIsInstance(deployment.client, AzureChatOpenAI)

    def test_temperature_accepted_by_real_client(self):
        """AzureChatOpenAI should still accept the temperature kwarg."""
        deployment = OpenAIDeployment(
            endpoint="https://fake-endpoint.openai.azure.com",
            api_version="2024-02-01",
            deployment_name="gpt-4",
            api_key="fake-key-for-testing",
            temperature=0.7,
        )

        self.assertIsInstance(deployment.client, AzureChatOpenAI)
        self.assertEqual(deployment.client.temperature, 0.7)


if __name__ == "__main__":
    unittest.main()
