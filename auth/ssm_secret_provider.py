import boto3

from auth.interfaces import SecretProvider


class SsmSecretProvider(SecretProvider):
    def __init__(self, parameter_name: str, client=None):
        self._parameter_name = parameter_name
        self._client = client or boto3.client("ssm")
        self._cached_value: str | None = None

    def get_secret(self) -> str:
        if self._cached_value is None:
            response = self._client.get_parameter(Name=self._parameter_name, WithDecryption=True)
            self._cached_value = response["Parameter"]["Value"]
        return self._cached_value
