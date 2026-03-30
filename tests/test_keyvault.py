import unittest
from unittest.mock import MagicMock, patch


from azure_doc_processing.keyvault import get_secret_from_key_vault


class TestGetSecretFromKeyVault(unittest.TestCase):
    """Unit tests for get_secret_from_key_vault."""

    @patch("azure_doc_processing.keyvault.SecretClient")
    @patch("azure_doc_processing.keyvault.DefaultAzureCredential")
    def test_get_secret_success(self, mock_credential, mock_client_cls):
        """Should return the secret value when retrieval succeeds."""
        mock_secret = MagicMock()
        mock_secret.value = "my-secret-value"
        mock_client_cls.return_value.get_secret.return_value = mock_secret

        result = get_secret_from_key_vault(
            "https://my-vault.vault.azure.net", "my-secret"
        )

        self.assertEqual(result, "my-secret-value")
        mock_credential.assert_called_once()
        mock_client_cls.assert_called_once()
        mock_client_cls.return_value.get_secret.assert_called_once_with("my-secret")

    @patch("azure_doc_processing.keyvault.SecretClient")
    @patch("azure_doc_processing.keyvault.DefaultAzureCredential")
    def test_get_secret_returns_none_on_error(self, mock_credential, mock_client_cls):
        """Should return None when an exception occurs."""
        mock_client_cls.return_value.get_secret.side_effect = Exception("not found")

        result = get_secret_from_key_vault(
            "https://my-vault.vault.azure.net", "missing-secret"
        )

        self.assertIsNone(result)

    @patch("azure_doc_processing.keyvault.SecretClient")
    @patch("azure_doc_processing.keyvault.DefaultAzureCredential")
    def test_get_secret_credential_error_returns_none(self, mock_credential, mock_client_cls):
        """Should return None when credential creation fails."""
        mock_credential.side_effect = Exception("auth failed")

        result = get_secret_from_key_vault(
            "https://my-vault.vault.azure.net", "my-secret"
        )

        self.assertIsNone(result)

    @patch("azure_doc_processing.keyvault.SecretClient")
    @patch("azure_doc_processing.keyvault.DefaultAzureCredential")
    def test_get_secret_passes_vault_url(self, mock_credential, mock_client_cls):
        """Should pass the vault URL to SecretClient."""
        mock_secret = MagicMock()
        mock_secret.value = "value"
        mock_client_cls.return_value.get_secret.return_value = mock_secret

        get_secret_from_key_vault("https://custom-vault.vault.azure.net", "secret")

        call_kwargs = mock_client_cls.call_args
        self.assertEqual(
            call_kwargs.kwargs.get("vault_url") or call_kwargs[1].get("vault_url"),
            "https://custom-vault.vault.azure.net",
        )


if __name__ == "__main__":
    unittest.main()
