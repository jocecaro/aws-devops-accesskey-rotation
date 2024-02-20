import requests
import json
import os
import sys
from requests.auth import HTTPBasicAuth

# Set the Org, Project, access token, and service connection name (service connection passed as parameter)
SERVICE_CONNECTION = sys.argv[1]  # Passed as parameter to this script
ORGANIZATION_URL = os.environ['ORG_URL']
PROJECT_NAME = os.environ['ORG_PROJECT_NAME']
ACCESS_TOKEN = os.environ['ORG_ACCESSTOKEN']
NEW_USERNAME = os.environ['NEW_USERNAME']
NEW_SECRET = os.environ['NEW_SECRET']

service_connection_name = SERVICE_CONNECTION
http_auth = f"Bearer {ACCESS_TOKEN}"

print(f"http-auth: {http_auth}")

# Construct the Get URL to get the service connections unique id for updating
if not ORGANIZATION_URL.endswith("/"):
    ORGANIZATION_URL += "/"

getUrl = f"{ORGANIZATION_URL}{PROJECT_NAME}/_apis/serviceendpoint/endpoints?endpointNames={service_connection_name}&api-version=7.0"


def get_service_connection_details():
    print(f"getUrl : {getUrl}")

    # Get the current configuration of the service connection
    request_headers = { "Authorization": f"Bearer {ACCESS_TOKEN}" }
    response = requests.get(getUrl, headers=request_headers)

    print("Response: ")
    htmlText = response.text
    print(htmlText)
    print(f"status-code: {response.status_code}")
    if response.status_code == 200:
        print(response.status_code)
    else:
        print("rest api call failed...")
        print(f"##vso[task.logissue type=error;]Get Service Connections RestApi call failed response - {response.status_code}")
        print(f"##vso[task.complete result=Failed;]Rest API failed with return code {response.status_code}")
        raise Exception(response.text)

    return json.loads(response.text)


def update_service_connection_details(service_connection_id, service_connection_data):

    updateUrl = f"{ORGANIZATION_URL}_apis/serviceendpoint/endpoints/{service_connection_id}?api-version=7.0"
    try:
        request_headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}" ,
            "Content-Type": "application/json"
        }
        response = requests.put(updateUrl, headers=request_headers, json=service_connection_data)

    except:
        print(f"##vso[task.logissue type=error;]Service Connection update failed! - status_code = {response.status_code}")
        print(f"##vso[task.complete result=Failed;]Rest API failed with return code {response.status_code}")
        sys.exit('rest-api failed')
    else:
        # Print the status code of the response to check for success
        if (response.status_code == 200):
            print(f"Service conneciton udpate successful - {response.status_code}")
        else:
            print("rest api call failed...")
            print(f"##vso[task.logissue type=error;]Update Service Connection RestApi call failed response - {response.status_code}")
            print(f"##vso[task.complete result=Failed;]Rest API failed with return code {response.status_code}")       
            sys.exit('rest-api failed')     



service_connection_config = get_service_connection_details()

if service_connection_config["count"] == 1:
    service_connection_id = service_connection_config["value"][0]["id"]
    updated_service_connection = service_connection_config["value"][0]
    # Update the secret in the configuration
    updated_service_connection["authorization"]["parameters"]["password"] = NEW_SECRET
    updated_service_connection["authorization"]["parameters"]["username"] = NEW_USERNAME
    # Call rest-api to update the service connection details
    update_service_connection_details(service_connection_id, updated_service_connection)
else:
    print("error more than one service connection returned")
    print(f"##vso[task.logissue type=error;]Update Service Connection RestApi call failed response - More than one service connectionion found with this name")
    print(f"##vso[task.complete result=Failed;]Rest API failed - returned more than one service connection")
    sys.exit('rest-api failed')    