import json
import botocore
import click

from deployer_deploy.utils.functions import get_version
from deployer_deploy.utils.main import deploy_stack, delete_current_stack, stack_list_repo, \
    update_file_to_s3


@click.group()
def cli():
    pass


@cli.command("version")
def version():
    get_version()


# @cli.command()
# @click.option("--nested-stack", help="Update yaml template for nested stack")
# @click.option("--json-params", help="Update JSON parameters")
# @click.option("--region", help="(optional) Set the region where you want to update S3 repo", default="us-east-1", show_default=True)
# @click.option("--stack-name", help="Set the name of the stack to be deleted")
# def upload_to_s3(stack_name, nested_stack, json_params, region):
#     try:
#         update_file_to_s3(stack_name, nested_stack, json_params, region)
#     except TypeError:
#         print("\nMissing arguments, check commands with: deployer update-to-s3 --help")
#     except FileNotFoundError:
#         print("\nFile not found")


@cli.command()
@click.option("--region", default="us-east-1", help="(optional) Set region code to see the stack uploaded", show_default=True)
def stack_list(region):
    try:
        stack_list_repo(region)
    except botocore.exceptions.ClientError:
        print("\nAccess Denied: You don't have permission for that region")


@cli.command()
@click.option("--stack-name", help="(optional) Specify the stack name", default="")
@click.option("--template", help="(optional) Yaml template path", default="")
@click.option("--params", help="(optional) JSON format parameters", default="")
@click.option("--region", help="(optional) Set the region where you want to deploy the stack", default="us-east-1", show_default=True)
def deploy(stack_name, template, params, region):
    try:
        deploy_stack(stack_name, template, params, region)
    except TypeError:
        print("\nMissing arguments, check commands with: deployer deploy --help")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "ValidationError":
            print("\nCheck your template, something is wrong or unresolved")


@cli.command()
@click.option("--stack-name", help="Set the name of the stack to be deleted")
@click.option("--params", help="(optional) JSON format parameters", default="")
@click.option("--region", help="(optional) Set the region of the stack", default="us-east-1", show_default=True)
def delete_stack(stack_name, params, region):
    try:
        delete_current_stack(stack_name, params, region)
    except TypeError:
        print("\nMissing arguments, check commands with: deployer delete-stack --help")
