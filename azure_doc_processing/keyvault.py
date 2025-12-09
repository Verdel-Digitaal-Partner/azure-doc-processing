import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def get_secret_from_key_vault(key_vault_url, secret_name):
    """
    Retrieve a secret from an Azure Key Vault.

    :param vault_name: The name of the Azure Key Vault (without https:// prefix)
    :param secret_name: The name of the secret in the Key Vault
    :return: The secret value
    """
    try:
        # Authenticate with Azure Key Vault using DefaultAzureCredential
        credential = DefaultAzureCredential()

        # Create a client for the Key Vault
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

        # Retrieve the secret
        secret = secret_client.get_secret(secret_name)

        return secret.value

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    # Replace with your Azure Key Vault name and the secret name
    key_vault_name = os.getenv("AZURE_KEYVAULT_URL")
    secret_name = "Azure-OpenAI-Endpoint"

    secret_value = get_secret_from_key_vault(key_vault_name, secret_name)

    if secret_value:
        print(f"The value of the secret '{secret_name}' is: {secret_value}")
    else:
        print(f"Failed to retrieve the secret '{secret_name}'.")
