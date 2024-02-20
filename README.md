[diagram]: ./documentation/keyrotation-pipelines/AwsServiceConnections.drawio.png
[service-connection-pic]: ./documentation/keyrotation-pipelines/AwsTerraformServiceConnections.png
# AWS Access Key Rotation 

This repository contains reference examples of how to automate the rotation of access keys using [Azure DevOps Pipelines](https://learn.microsoft.com/en-us/azure/devops/pipelines/?view=azure-devops)
These user accounts that need automation key rotation can be categorized as
- System accounts in AWS used by [Service Connections](https://learn.microsoft.com/en-us/azure/devops/pipelines/library/service-endpoints?view=azure-devops&tabs=yaml) in Azure DevOps
- System accounts used by other apps/apis/services ex: service connection used by Solarwinds montitoring tool

# Why Rotate Access Keys
The CIS AWS Foundations Benchmarks recommend rotating access keys every 90 days or less.  So why not automate this via CI/CD pipeline

[IAM.3 users' access keys should be rotated every 90 days or less](https://docs.aws.amazon.com/securityhub/latest/userguide/iam-controls.html#iam-3)

# AWS DevOps Service Connections 

There are 2 types of service connections for AWS.  One is a true AWS service connection to run AWS CLI commands, the other is for Terraform, a terraform service connection.  Both use the same aws service account in IAM

![image][service-connection-pic]

## AWS and Terraform Service Connection Key Rotation Pipeline

The diagram below describes how the rotation of keys is setup for the AWS Service Connection in Azure DevOps

![Key rotation diagram][diagram]

---
## 1. Extract Acceses Keys
First step inside the pipeline template is to retrieve the existing keys from AWS using the AWSShellScript@1 task.  The task runs the ```aws iam list-access-keys``` and stores it in an output file for use in the next task which extracts the information from the json file and stores it into task environment variables
```yaml
- task: AWSShellScript@1
inputs:
    awsCredentials: ${{parameters.aws_service_connection}}
    regionName: ${{parameters.aws_region}}
    scriptType: 'inline'
    inlineScript: |
    aws iam list-access-keys --user-name ${{parameters.service_username}} --output json > ./awsCurrentUser.json
displayName: Get the current Access Keys from AWS

# Extract access key (can have up to 2 access keys per user)
- bash: |
    echo ## Extract access key 1 and 2 ##    
    json=$(cat ./awsCurrentUser.json)
    accessKey1=$(echo $json | jq -c '.AccessKeyMetadata' | jq -c '.[0]' | jq -r '.AccessKeyId')
    accessKey2=$(echo $json | jq -c '.AccessKeyMetadata' | jq -c '.[1]' | jq -r '.AccessKeyId')
    keyCount=$(echo $json | jq -r '.AccessKeyMetadata | length')
    echo ## Assign new access key to pipeline variable ##
    echo "##vso[task.setvariable variable=oldAccessKey1;issecret=false]$accessKey1"
    echo "##vso[task.setvariable variable=oldAccessKey2;issecret=false]$accessKey2"
    echo "##vso[task.setvariable variable=totalKeys;issecret=false]$keyCount"
displayName: Extract Existing Credential Keys
```

Required inputs:
| Input | Description | Found in... | Reference
| :--- | :------- | :--- | :--- |
|AWS Service Connection | Name of an AWS service connection from DevOps that has IAM privileges (passed as a parameter) | DevOps Infrastructure Service Connections | [DevOps Service Connections](https://dev.azure.com/jea-org/Infrastructure/_settings/adminservices)
|AWS Region | The AWS Region - needed for the AWSShellScript parameter (passed as a parameter) | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Service Username | The IAM Username to update | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)



---

## 2. Delete > 1 Access Key
In AWS IAM a user (or service account) is only allowed max of 2 access key/secrets per user.  If for some reason there happens to be 2 of them, this step will delete one to make sure that it can create a new one.  There shouldn't 2 keys unless a pipeline script may have failed on the last run.  The task runs an AWSShellScript@1 type task with the ```aws iam delete-access-key``` command.

```yaml
  - task: AWSShellScript@1
    condition: eq(variables.totalKeys, 2)  # Task will run if more than 1 key is there
    inputs:
      awsCredentials: ${{parameters.aws_service_connection}}
      regionName: ${{parameters.aws_region}}
      scriptType: 'inline'
      inlineScript: |
        aws iam delete-access-key --user-name ${{parameters.service_username}} --access-key-id $(oldAccessKey2)
    displayName: Delete if more than one AWS Keys
```

Required inputs:
| Input | Description | Found in... | Reference
| :--- | :------- | :--- | :--- |
|AWS Service Connection | Name of an AWS service connection from DevOps that has IAM privileges (passed as a parameter) | DevOps Infrastructure Service Connections | [DevOps Service Connections](https://dev.azure.com/jea-org/Infrastructure/_settings/adminservices)
|AWS Region | The AWS Region - needed for the AWSShellScript parameter (passed as a parameter) | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Service Username | The IAM Username to update | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Access Key Id to Delete | The IAM Username access key to delete | Retrieve from previous step | Step 1 above

---

## 3. Create New Access Key
Using AWSShellScript@1 task, creates the new access key using the ```aws iam create-access-key``` command
```yaml
  - task: AWSShellScript@1
    inputs:
      awsCredentials: ${{parameters.aws_service_connection}}
      regionName: ${{parameters.aws_region}}
      scriptType: 'inline'
      inlineScript: |
        aws iam create-access-key --user-name ${{parameters.service_username}} --output json > ./awsResults.json
    displayName: New Access Keys from AWS
```

Required inputs:
| Input | Description | Found in... | Reference
| :--- | :------- | :--- | :--- |
|AWS Service Connection | Name of an AWS service connection from DevOps that has IAM privileges (passed as a parameter) | DevOps Infrastructure Service Connections | [DevOps Service Connections](https://dev.azure.com/jea-org/Infrastructure/_settings/adminservices)
|AWS Region | The AWS Region - needed for the AWSShellScript parameter (passed as a parameter) | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Service Username | The IAM Username to create new key for | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)


---
## 4. Update Service Connection
For each of the service connections passed to the template as a service_connection_list parameters, a python script is called to update the DevOps Service Connection with the newly created secrets.  The python script uses the devops serviceendpoints rest api using the pipeline System.AccessToken as the bearer token.

```yaml
  - ${{ each service_connection_to_update in parameters.service_connection_list }}:
    - task: PythonScript@0
      inputs:
        scriptSource: 'filePath'
        scriptPath: '$(System.DefaultWorkingDirectory)/pipelines/pipelinescripts/updateDevOpsServiceConnection.py'
        arguments: '"${{ service_connection_to_update }}"' 
      env:
        ORG_ACCESSTOKEN: ${{ parameters.azure_org_access_token }}
        ORG_URL: ${{ parameters.azure_org_url }}
        ORG_PROJECT_NAME: ${{ parameters.azure_project }}
        NEW_USERNAME: '$(newAccessKeyId)'
        NEW_SECRET: '$(newSecretKey)'
      displayName: Update Service Connection with new credentials
```
Required inputs:
| Input | Description | Found in... | Reference
| :--- | :------- | :--- | :--- |
|AWS Service Connection | Name of an AWS service connection from DevOps that needs to be updated | DevOps Infrastructure Service Connections | [DevOps Service Connections](https://dev.azure.com/jea-org/Infrastructure/_settings/adminservices)
|Org Url | The DevOps organization url (used for calling rest api) | Passed from yaml pipeline (System.TeamFoundationCollectionUri) | [DevOps Predefined variables](https://learn.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=azure-devops&tabs=yaml)
|Project name | Name of the DevOps project | Passed from yaml pipeline (System.TeamProject) | [DevOps Predefined variables](https://learn.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=azure-devops&tabs=yaml)
|New Access Key Id | Newly created access key id | Created in Step 3 above | Step 3
|New Secret Key | Newly created access secret id | Created in Step 3 above | Step 3


---
## 5. Create or Update ScretsManager
Stored the newly created access-key and secret in the AWS SecretsManager service.  Using the azure devops task ```SecretsManagerCreateOrUpdateScript@1```

```yaml
  - task: SecretsManagerCreateOrUpdateSecret@1
    inputs:
      awsCredentials: '${{parameters.aws_service_connection}}'
      regionName: '${{parameters.aws_region}}'
      secretNameOrId: '${{parameters.aws_secrets_name}}'
      description: 'access and secrets auto-rotated from azure devops'
      secretValueSource: 'inline'
      secretValue: '{"accesskey":"$(newAccessKeyId)","secretskey":"$(newSecretKey)"}'
      autoCreateSecret: true
      tags: |
        Name=SecretsKeys
        Stack=AzureDevOps
      logRequest: true
      logResponse: true
    displayName: Update Secrets Manager with new keys
```

Required inputs:
| Input | Description | Found in... | Reference
| :--- | :------- | :--- | :--- |
|AWS Service Connection | Name of an AWS service connection from DevOps that has IAM privileges (passed as a parameter) | DevOps Infrastructure Service Connections | [DevOps Service Connections](https://dev.azure.com/jea-org/Infrastructure/_settings/adminservices)
|AWS Region | The AWS Region - needed for the AWSShellScript parameter (passed as a parameter) | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Secrets Name | The SecretsManager name to update/create | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|New Access Key Id | Newly created access key id | Created in Step 3 above | Step 3
|New Secret Key | Newly created access secret id | Created in Step 3 above | Step 3

---
## 6. Delete Old Access Keys
Once all of the above steps are successful, remove the old access key using the ```AWSShellScript@1``` task.

```yaml
  - task: AWSShellScript@1
    condition: gt(variables.totalKeys, 0)  # Task will run if there is an old key to remove  
    inputs:
      awsCredentials: ${{parameters.aws_service_connection}}
      regionName: ${{parameters.aws_region}}
      scriptType: 'inline'
      inlineScript: |
        aws iam delete-access-key --user-name ${{parameters.service_username}} --access-key-id $(oldAccessKey1)
    displayName: Delete Old AWS Keys
```
Required inputs:
| Input | Description | Found in... | Reference
| :--- | :------- | :--- | :--- |
|AWS Service Connection | Name of an AWS service connection from DevOps that has IAM privileges (passed as a parameter) | DevOps Infrastructure Service Connections | [DevOps Service Connections](https://dev.azure.com/jea-org/Infrastructure/_settings/adminservices)
|AWS Region | The AWS Region - needed for the AWSShellScript parameter (passed as a parameter) | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Service Username | The IAM Username to update | Passed from yaml pipeline | [Build Pipeline](https://dev.azure.com/jea-org/Infrastructure/_build?view=folders&treeState=XGtleS1yb3RhdGlvbnMkXGtleS1yb3RhdGlvbnNcYXdz)
|Access Key Id to Delete | The IAM Username access key to delete | Retrieve from step 1 | Step 1 above

