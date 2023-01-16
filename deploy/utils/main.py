import os
import boto3
import sys
import json
import time
import click
from halo import Halo
import datetime
import calendar

# Deploy stack by name and template path
from deployer_deploy.deploy_config import default_params
from deployer_deploy.utils.functions import validate_template, bcolors, is_stack_deployed, sync_local_with_s3, \
    get_json_params

# User cli answers
from deployer_deploy.utils.messages import sendMessage, sendMessageTitle

yes = {'yes', 'y', 'ye', 'Y'}
no = {'no', 'n', ''}


# Print deployed stack list
def stack_list_repo(region):

    # initialize client by region
    client = boto3.client("cloudformation", region_name=region)
    stack_list = client.describe_stacks()
    click.clear()

    print("Deployed stacks: ", bcolors.BOLD + str(len(stack_list["Stacks"])) + bcolors.ENDC + "\n")
    for i in range(0, len(stack_list["Stacks"])):
        print(stack_list["Stacks"][i]["StackName"])


# Deploy stack
def deploy_stack(stackname_cli, template_main_cli, params_cli, region_cli):

    # setup arguments, if not specified from CLI (an argument not specified is an empty string), use default value from json params
    get_json_params_stackname = ""
    for i in range(0, len(get_json_params())):
        if get_json_params()[i]["ParameterKey"] == "ProjectName":
            get_json_params_stackname = get_json_params()[i].get("ParameterValue")

    stackname_default = stackname_cli
    stackname = stackname_default if stackname_cli is not "" else get_json_params_stackname
    template_main_default = template_main_cli
    template_main = template_main_default if template_main_cli is not "" else default_params()["templateMain"]
    json_params_default = params_cli
    json_params = json_params_default if params_cli is not "" else default_params()["jsonParams"]
    region = region_cli


    # initialize cloudformation client with specific region
    cloudformation_client = boto3.client("cloudformation", region_name=region)


    # get arguments file absolute paths
    local_path = os.getcwd()
    template_path_absolute = local_path + "/templates/" + template_main
    params_path_absolute = local_path + "/parameters/" + json_params


    # get params from json
    with click.open_file(params_path_absolute, 'r') as f:
        json_content = f.read()
        json_data = json.loads(json_content)

    project_name = json_data[0]["ParameterValue"]


    # get YAML template content
    with open(template_path_absolute, 'r') as yaml_file:
        template_content = yaml_file.read()


    # 1. Validate template
    if validate_template(template_path_absolute):

        # clear screen and validate template
        click.clear()
        print(bcolors.OKGREEN + "\nTemplate is valid" + bcolors.ENDC)

        # sync local project to S3 repo
        spinner = Halo(text='Sync local to S3, please wait..', spinner='dots')
        spinner.start()
        sync_local_with_s3(project_name, params_cli)  # sync
        spinner.stop()


        # if stack IS ALREADY created
        if is_stack_deployed(stackname, region):

            print("Stack already exists.. checking for drift..")

            # check drift status
            # stack_drift_ID = cloudformation_client.detect_stack_drift(StackName = stackname)
            # check_drift = cloudformation_client.describe_stack_drift_detection_status(StackDriftDetectionId = stack_drift_ID["StackDriftDetectionId"])
            rs = boto3.resource('cloudformation', region_name=region)
            stack = rs.Stack(stackname)
            stackStatus = stack.drift_information["StackDriftStatus"]


            # Ask user to continue(y/N)
            ask_for_drift = input("\n> Current drifted status is: " + bcolors.WARNING + stackStatus + bcolors.ENDC + ", do you want to continue and create the change set? (y/N) ")

            # User choose to continue(y)
            if ask_for_drift in yes:

                # Create change set for UPDATE stack
                change_set_update = create_update_change_set(stack, stackname, template_content, region)

                # Change set description - print current status
                if change_set_update["Status"] != "FAILED":
                    # print("\nChange set status: " + change_set_update["Status"] + ", please wait.. ")

                    # Print change set repo
                    _cs_changes = change_set_update["Changes"]
                    _total_cs_changes = str(len(_cs_changes))

                    print("\n" + bcolors.BOLD + "Change set" + bcolors.ENDC + ": " + _total_cs_changes)
                    for i in range(0, len(_cs_changes)):
                        _cs_action = change_set_update["Changes"][i]["ResourceChange"]["Action"]
                        if _cs_action == "Add":
                            action_bcolor = bcolors.OKGREEN
                        elif _cs_action == "Modify":
                            action_bcolor = bcolors.OKBLUE
                        else:
                            action_bcolor = bcolors.FAIL

                        print(action_bcolor + _cs_action + bcolors.ENDC + " ---> " + change_set_update["Changes"][i]["ResourceChange"]["LogicalResourceId"])


                    # Ask user to continue and execute change set
                    if change_set_update["Status"] == "CREATE_COMPLETE":
                        ask_for_change_set = input("\n> Change set is ready, continue? (y/N) ")

                        # Execute change set -> YES
                        if ask_for_change_set in yes:

                            # loading spinner
                            spinner = Halo(text='Update in progress..', spinner='dots')
                            spinner.start()

                            # change set execute
                            execute_change_set_response = cloudformation_client.execute_change_set(
                                ChangeSetName=change_set_update["ChangeSetName"],
                                StackName=stackname
                            )

                            # update stack
                            waiter_update = cloudformation_client.get_waiter('stack_update_complete')
                            waiter_update.wait(StackName=stackname)

                            spinner.stop()

                            # sendMessageTitle("Stack updated!", stackname)
                            print(bcolors.OKGREEN + bcolors.BOLD + "\nStack updated!" + bcolors.ENDC)

                        # Execute change set -> NO
                        elif ask_for_change_set in no:
                            print("Change set execution canceled")


                # change set failed
                elif change_set_update["Status"] == "FAILED":

                    #print("\n" + bcolors.FAIL + change_set_update["Status"] + bcolors.ENDC + ": " + change_set_update["StatusReason"] + "\n** Please delete change-set from the web console and do some modifies to the template.yaml (this should be an AWS cache fact)\n")
                    print("\n" + bcolors.FAIL + change_set_update["Status"] + bcolors.ENDC + "\n** Please delete change-set from the web console and do some modifies to the template.yaml (this should be an AWS cache fact)\n")
                    ask_delete_change_set = input("\n> Delete current change set? (y/N)")

                    # Delete change set -> YES
                    if ask_delete_change_set in yes:

                        # delete change set
                        delete_change_set_response = cloudformation_client.delete_change_set(
                            StackName = stackname,
                            ChangeSetName = change_set_update["Id"]
                        )

                        print("\nChange set deleted correctly. Please modify the template and try again the operation")
                        sys.exit()


                    # Delete change set -> NO
                    elif ask_delete_change_set in no:
                        print("\n Operation stopped")
                        sys.exit()


            # User choose to not continue the drift check
            elif ask_for_drift in no:
                print('Better wait and check manually...')
                sys.exit()

            else:
                print("Something went wrong")
                sys.exit()


        # Stack doesn't exists, create a new one
        else:
            # ask user confirm to create new stack
            ask_for_create_stack = input(f"\n> Stack " + bcolors.BOLD + stackname + bcolors.ENDC + " not yet created, create new? (y/N) ")

            # Create new stack -> YES
            if ask_for_create_stack in yes:

                # Create new stack
                create_stack(stackname, template_content, json_data, region)

            # Create new stack -> NO
            else:
                print("Operation stopped")
                sys.exit()

    # Template validation failed
    else:
        print(bcolors.FAIL + '\nFAILED! Template not valid' + bcolors.ENDC)
        sys.exit()


# Create new stack
def create_stack(stackname, template_content, json_data, region):

    # initialize cloudformation client with specific region
    cloudformation_client = boto3.client("cloudformation", region_name=region)

    # 1. Create change set for empty stack
    change_set_create_response = cloudformation_client.create_change_set(
        StackName=stackname,
        TemplateBody=template_content,
        ChangeSetName=stackname + "-change-set",
        Parameters=json_data,
        ChangeSetType="CREATE"
    )

    # 2. Create empty stack
    create_stack_response = cloudformation_client.create_stack(
        StackName=stackname,
        TemplateBody=template_content,
        Parameters=json_data,
        Tags=[{"Key": "Owner", "Value": "deployer-Team"}]
    )

    # loading spinner
    spinner = Halo(text='Deploy in progress..', spinner='dots')
    spinner.start()

    # start timer
    # start_time = datetime.datetime.now()

    # check stack status during deploy
    # This function needs to be created internally to call "stackname", or it fails
    # def check_events():
    #     threading.Timer(2.0, check_events).start()
    #     response = cloudformation_client.describe_stack_events(StackName=stackname)
    #     for i in range(0, len(response)):
    #         # print(f"\n\nCreating... {response['StackEvents'][i]['LogicalResourceId']} -> {response['StackEvents'][i]['ResourceStatus']}")
    #         print(response['StackEvents'])
    #
    # check_events()

    # waiter
    waiter_create_new_stack = cloudformation_client.get_waiter("stack_create_complete")
    waiter_create_new_stack.wait(StackName=stackname)
    spinner.stop()

    # 3. Stack created
    # end_time = datetime.datetime.now()
    # calculate_time = end_time - start_time
    # total_time = str(datetime.timedelta(seconds=calculate_time))
    notification = "New stack " + bcolors.OKGREEN + bcolors.BOLD + stackname + bcolors.ENDC + bcolors.ENDC + " created!"
    # sendMessageTitle("Stack created!", stackname)
    print(f"\n" + notification + "\n")
    sys.exit()


# Delete deployed stack
def delete_current_stack(stackname, params_cli, region):

    # initialize cloudformation client with specific region
    cloudformation_client = boto3.client("cloudformation", region_name=region)

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
    for i in range(0, len(get_json_params())):
        if get_json_params()[i]["ParameterKey"] == "BucketName":
            bucketName = get_json_params()[i].get("ParameterValue")

    # ask user to delete stack
    ask_for_delete_stack = input("\n> " + bcolors.WARNING + "[Warning]" + bcolors.ENDC + " Deleting stack " + bcolors.BOLD + stackname + bcolors.ENDC + " - continue? (y/N) ")
    if ask_for_delete_stack in yes:

        # check if stack is already created (add check if is already in deletion)
        if is_stack_deployed(stackname, region):

            # delete stack
            delete_stack_response = cloudformation_client.delete_stack(StackName = stackname)
            spinner = Halo(text='Loading', spinner='dots')
            spinner.start()
            delete_stack_waiter = cloudformation_client.get_waiter('stack_delete_complete')
            delete_stack_waiter.wait(StackName=stackname)

            # delete project from S3
            s3_client = boto3.resource("s3")

            bucket = s3_client.Bucket(bucketName)
            bucket.objects.filter(Prefix=f"{stackname}").delete()
            spinner.stop()

            # print message
            notification = bcolors.OKGREEN + "\nStack deleted correctly!" + bcolors.ENDC
            # sendMessageTitle("Stack deleted correctly!", stackname)
            print(notification)
            sys.exit()

        else:
            print("\nStack already deleted or incorrect name, operation stopped")
            sys.exit()

    elif ask_for_delete_stack in no:
        print("\nOperation stopped")
        sys.exit()


# create change-set
def create_update_change_set(stack, stackname, template_content, region):

    # cloud formation client for specific region
    cloudformation_client = boto3.client("cloudformation", region_name=region)

    # current date and time
    # now = datetime.now()
    timestamp = calendar.timegm(time.gmtime())

    # loading spinner
    spinner = Halo(text='Creating change set..', spinner='dots')
    spinner.start()

    change_set_update_response = cloudformation_client.create_change_set(
        StackName=stackname,
        TemplateBody=template_content,
        ChangeSetName=stackname + "-change-set-" + str(timestamp),
        Parameters=stack.parameters,
        ChangeSetType="UPDATE"
    )

    # waiter has some "bug", it doesn't restart the flow when the change set status is CREATE_COMPLETE
    waiter_create = cloudformation_client.get_waiter('change_set_create_complete')

    while True:
        waiter_create.wait(
            StackName=stackname,
            ChangeSetName=change_set_update_response["Id"]
        )

        # Change set description
        describe_change_set_response = cloudformation_client.describe_change_set(
            StackName=stackname,
            ChangeSetName=change_set_update_response["Id"]
        )

        change_set_status = describe_change_set_response["Status"]

        # break the loop when change-set status is CREATE_COMPLETE and not CREATE_PENDING (or FAILED of course!)
        if change_set_status == "CREATE_COMPLETE":
            break

        elif change_set_status == "FAILED":
            print("Operation failed")
            sys.exit(1)

    spinner.stop()

    # only when status is FAILED, there is "StatusReason field available"
    change_set = {
        "Status": describe_change_set_response["Status"],
        "Changes": describe_change_set_response["Changes"],
        "ChangeSetName": describe_change_set_response["ChangeSetName"]
    }

    return change_set


# Upload to S3 specific files
def update_file_to_s3(project_name, nested_stack_yaml, params_cli, region):

    # if params_cli is empty, get json file default
    json_params_default = params_cli
    json_params = json_params_default if params_cli is not "" else default_params()["jsonParams"]

    # get arguments file absolute paths
    local_path = os.getcwd()
    params_path_absolute = local_path + "/parameters/" + json_params
    nested_stack = local_path + "/templates/nested/" + nested_stack_yaml
    # get params from json
    with click.open_file(params_path_absolute, 'r') as f:
        json_content = f.read()
        json_data = json.loads(json_content)

    # S3 bucket repo
    bucketName = json_data[5]["ParameterValue"]

    # initialize S3 client
    s3_client = boto3.resource("s3", region_name=region)
    s3_bucket = s3_client.Bucket(bucketName)

    # check nested stack
    if nested_stack and validate_template(nested_stack) and json_params is None:
        nested_templates_yaml = os.path.split(nested_stack)
        spinner = Halo(text='Uploading nested stack to S3', spinner='dots')
        spinner.start()
        s3_bucket.upload_file(nested_stack, project_name + "templates/nested/" + nested_templates_yaml[1])
        spinner.stop()
        print("Upload nested stack complete!")

    # check json params
    elif json_params and nested_stack is None:
        if json_params.endswith('.json'):
            json_params_file = os.path.split(json_params)
            spinner = Halo(text='Uploading JSON params to S3', spinner='dots')
            spinner.start()
            s3_bucket.upload_file(json_params, project_name + "parameters/" + json_params_file[1])
            spinner.stop()
            print("Upload json parameters complete!")

        else:
            print("JSON not in correct format, operation stopped")
            sys.exit()

    # check all arguments
    else:
        nested_stack_tmpl = os.path.split(nested_stack)
        json_file = os.path.split(json_params)
        if json_params.endswith('.json'):
            spinner = Halo(text='Uploading nested stack && JSON params to S3', spinner='dots')
            spinner.start()
            s3_bucket.upload_file(nested_stack, project_name + "templates/nested/" + nested_stack_tmpl[1])
            s3_bucket.upload_file(json_params, project_name + "parameters/" + json_file[1])
            spinner.stop()
            print("Upload nested stack and json parameters complete!")

        else:
            print("JSON not in correct format, operation stopped")
            sys.exit()

