import os

import boto3
import botocore
import logging
import sys
import yaml
import json
import time
import click

# Colors
from deployer_deploy.deploy_config import default_params
from deployer_deploy.utils.Bcolors import Bcolors
bcolors = Bcolors()


# Check template validation
def validate_template(file_path):
    # Initialize cloudformation client - no region setted, for generic use
    cloudformation_client = boto3.client("cloudformation")
    yaml_tmpl = open(file_path, "r")
    return cloudformation_client.validate_template(
        TemplateBody = yaml_tmpl.read()
    )


# JSON params
def get_json_params():
    local_path = os.getcwd()
    params_path_absolute = local_path + "/parameters/parameters.json"
    with click.open_file(params_path_absolute, 'r') as f:
        json_content = f.read()
        json_data = json.loads(json_content)

    return json_data


# Check if stack already exists (Bool)
def is_stack_deployed(stack_name, region):
    # Interrogo Cloudformation per farmi ritornare la lista completa degli stack nella region corrente
    # check API pagination
    cloudformation_client_specific_region = boto3.client("cloudformation", region_name=region)
    stacks_response = cloudformation_client_specific_region.describe_stacks()

    # Prendo solo la lista degli stack dalla risposta precedente e ottengo un array
    stacks = stacks_response["Stacks"]

    # Creo array vuoto in cui metterò i nomi degli stack
    stacks_names = []

    # Ciclo sull'array stacks, e per ogni oggetto mi prendo il nome dello stack e lo inserisco nell'array stacks_names
    for stack in stacks:
        stacks_names.append(stack["StackName"])

    return stack_name in stacks_names


# Upload to S3 ALL the project before deploy
def sync_local_with_s3(project_name, params_cli):
    local_path = os.getcwd()

    # select the folder to upload
    upload_project(project_name, params_cli, f"{local_path}/templates")
    upload_project(project_name, params_cli, f"{local_path}/parameters")
    upload_project(project_name, params_cli, f"{local_path}/resources")
    upload_project(project_name, params_cli, f"{local_path}/ansible")


# upload project
def upload_project(project_name, params_cli, folder):
    # if params_cli is empty, get json file default
    json_params_default = params_cli
    json_params = json_params_default if params_cli is not "" else default_params()["jsonParams"]

    # get arguments file absolute paths
    local_path = os.getcwd()
    params_path_absolute = local_path + "/parameters/" + json_params

    # get params from json
    with click.open_file(params_path_absolute, 'r') as f:
        json_content = f.read()
        json_data = json.loads(json_content)

    # S3 bucket repo
    bucketName = ""
    for i in range(0, len(json_data)):
        if json_data[i]["ParameterKey"] == "BucketName":
            bucketName = json_data[i].get("ParameterValue")

    # initialize S3 client and create target folder to S3
    if os.path.isdir(folder):
        dirname = os.path.basename(folder)

    # s3_root = f"projects/test/{project_name}/{dirname}/"
    s3_root = f"{project_name}/{dirname}/"
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucketName)
    for subdir, dirs, files in os.walk(folder):
        for file in files:
            full_path = os.path.join(subdir, file)
            with open(full_path, 'rb') as data:
                bucket.upload_file(full_path, s3_root + full_path[len(folder) + 1:])


# get Tag from codecommit
def get_version():
    print("""
    _   __                       __           _
   / | / /___  ____ _   ______  / /___ ______(_)
  /  |/ / __ \/ __ \ | / / __ \/ / __ `/ ___/ /
 / /|  / /_/ / /_/ / |/ / /_/ / / /_/ / /  / /
/_/ |_/\____/\____/|___/\____/_/\__,_/_/  /_/
                        CLI Tool - by beSharp          
                                       v1.0.0         
          """)
