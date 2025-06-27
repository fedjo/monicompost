import json
import requests

from app.config import settings


def get_devices_in_workspace(workspace_id):
        query = '''
            query {
                allDevices(inWorkspace: "%s") {
                    id
                    verboseName
                }
            }
            ''' % workspace_id

        headers = {"Authorization": f"Token {settings.DATACAKE_API_KEY}", "Content-Type": "application/json"}
        response = requests.post(f"{settings.DATACAKE_URL}", json={"query": query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

def get_telemetry_for_device(device_id, fields=[]):
        query = f"""
            query {{
                device(deviceId: "{device_id}") {{
                    history(
                    fields: {json.dumps(fields)},
                    timerangestart:"2025-06-22T00:00",
                    timerangeend:"2025-06-23T00:00",
                    resolution:"60m"
                    )
                }}
            }}
            """
        headers = {"Authorization": f"Token {settings.DATACAKE_API_KEY}", "Content-Type": "application/json"}
        response = requests.post(f"{settings.DATACAKE_URL}", json={"query": query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

def get_telemetry_for_workspace_devices(workspace_id, fields=[]):
        query = f"""
            query {{
                allDevices(inWorkspace: "{workspace_id}") {{
                    id
                    verboseName
                    history(
                    fields: {json.dumps(fields)},
                    timerangestart:"2025-06-22T00:00",
                    timerangeend:"2025-06-23T00:00",
                    resolution:"60m"
                    )
                }}
            }}
            """
        headers = {"Authorization": f"Token {settings.DATACAKE_API_KEY}", "Content-Type": "application/json"}
        response = requests.post(f"{settings.DATACAKE_URL}", json={"query": query}, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data

