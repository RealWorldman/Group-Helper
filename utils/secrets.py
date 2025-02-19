import json
import requests
from google.cloud import secretmanager

GCP_PROJECT = "wow-api-441714"

def access_secret_version(project_id, secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def save_secret_version(project_id, secret_id, payload):
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}/secrets/{secret_id}"
    payload = payload.encode("UTF-8")
    response = client.add_secret_version(
        request={"parent": parent, "payload": {"data": payload}}
    )
    return response

if __name__ == "__main__":
    client_id = access_secret_version(GCP_PROJECT, "wow-api-client-id")
    client_secret = access_secret_version(GCP_PROJECT, "wow-api-client-secret")