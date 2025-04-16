from google.cloud import secretmanager
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def get_raid_helper_api_key(project_id, secret_id, json_path):
    if project_id:
        logging.info(f'GCP Project: {project_id}')
        api_key = access_secret_version(project_id=project_id, secret_id=secret_id)
        return api_key
    else:
        try:
            with open(json_path, 'r') as f:
                json_daten = json.load(f)
        except FileNotFoundError:
            print(f"Fehler: Datei nicht gefunden unter '{json_path}'")
            return None
        except json.JSONDecodeError:
            print(f"Fehler: Ungültiges JSON-Format in der Datei '{json_path}'")
            return None
        secret_id_num = secret_id.split("-")[-1]
        for server in json_daten.get("RAID-HELPER", []):
            if server.get("ServerID") == secret_id_num:
                api_key = server.get("ApiKey")
                return api_key


def get_discord_token(project_id, secret_id, json_path):
    if project_id:
        logging.info(f'GCP Project: {project_id}')
        token = access_secret_version(project_id=project_id, secret_id=secret_id)
        return token
    else:
        try:
            with open(json_path, 'r') as f:
                json_daten = json.load(f)
        except FileNotFoundError:
            print(f"Fehler: Datei nicht gefunden unter '{json_path}'")
            return None
        except json.JSONDecodeError:
            print(f"Fehler: Ungültiges JSON-Format in der Datei '{json_path}'")
            return None
        for app in json_daten.get("DISCORD", []):
            if app.get("AppName") == secret_id:
                token = app.get("DiscordToken")
                return token