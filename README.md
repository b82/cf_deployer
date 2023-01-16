# deployer
#### Create and manage stacks from CLI without pass from the AWS console

## Installation (tested with python 3.6):


```
virtualenv -p $(which python3) venv
source venv/bin/activate
pip install -r resources/requirements.txt
pip install --editable . # (from the root project to compile tool.py after every modify)
```





# Configuration - Cloudformation parameters
## Deploy is currently available only for N.Virginia and Ireland regions

#### json.parameters
Cloudformation deploy parameters
```
[
    {
        "ParameterKey": "ProjectName",
        "ParameterValue": "deployer-demo"
    },
    {
        "ParameterKey": "Environment",
        "ParameterValue": "demo"
    },
    {
        "ParameterKey": "VPCCIDR",
        "ParameterValue": "10.99.0.0/16"
    },
    {
        "ParameterKey": "KeyPairName",
        "ParameterValue": "deployer-demo"
    },
    {
        "ParameterKey": "CreateRedshift",
        "ParameterValue": "True"
    },
    {
        "ParameterKey": "BucketName",
        "ParameterValue": "deployer-demo-repo"
    },
    {
        "ParameterKey": "InstanceProfile",
        "ParameterValue": "deployer-demo-ec2-role"
    }
]
```

#### deployer_deploy/deploy_config.py
Returns an object with default parameters when no settings (parameters, templates, ...) are specified from the CLI
```
deploy_default_params = {
    "templateMain": "main.yaml",
    "jsonParams": "parameters.json"
}
```


# Commands

### stack-list (default region: us-east-1)

```
deployer stack-list
```
```
deployer stack-list --region eu-west-1
```


### deploy (default region: us-east-1)

Optionals commands if you want to use a specific value
* --stack-name  (stack name)
* --template    (main yaml template - choose file from /template)
* --params      (JSON format params - choose file from /parameters)
* --region      (region where you want to deploy the stack, the default is us-east-1)

```
deployer deploy # (default values from deploy_config.py)
deployer deploy --stack-name my-project-name --template main.yaml --params params.json --region us-east-2
```


### delete-stack (default region: us-east-1)

* --stack-name  (stack name)
* --params      ([optional] JSON format params - choose file from /parameters)
* --region      ([optional] region where you want to deploy the stack, the default is us-east-1)
```
deployer delete-stack --stack-name my-project-name
```
```
deployer delete-stack --stack-name my-project-name --params ./parameters/other.json --region eu-west-1
```


### upload-to-s3 (DISABLED)
* --nested-stack    (nested stack yaml - choose file from /templates/nested)
* --json-params     (JSON format params - choose file from /parameters)

```
deployer upload-to-s3 --nested-stack network.yaml
```
```
deployer upload-to-s3 --json-params parameters.json
```
```
deployer upload-to-s3 --nested-stack network.yaml --json-params parameters.json
```


### version
```
deployer version
```


---


# Infrastructure

* VPC
* EC2 (x4)
  * Ubuntu 18.04
    * 2 volumi
    * MongoDB standalone (/mongodata)
    * deployer Agent
  * Amazon Linux 2
    * MySQL
    * deployer Agent
  * Windows Server 2019 SQL Server 2017 Standard (currently using an ubuntu t3a.micro for billing)
    * InstanceType: t3a.xlarge - $0.704 per Hour
    * deployer Agent
  * Amazon Linux 2 (ec2-user)
    * Wordpress
    * Agentless
* RDS
  * MySQL
  * Oracle
  * Aurora Cluster (optional)
  * MySQL
* Redshift (optional)
  * nodetype: ds2.xlarge - $0.85 per hour
* DynamoDB
