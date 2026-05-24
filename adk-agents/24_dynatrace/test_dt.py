import requests
import os
from dotenv import load_dotenv
load_dotenv('dynatrace_agent_01/.env')

tenant = os.environ.get("DYNATRACE_TENANT")
token = os.environ.get("DYNATRACE_API_TOKEN")

url = f"https://{tenant}.live.dynatrace.com/api/v2/otlp/v1/traces"
headers = {
    "Authorization": f"Api-Token {token}",
    "Content-Type": "application/x-protobuf"
}

resp = requests.post(url, headers=headers, data=b"invalid-payload", timeout=5)
print(f"Status: {resp.status_code}")
print(f"Text: {resp.text}")
