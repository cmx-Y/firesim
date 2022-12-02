#!/usr/bin/env python3

# Runs periodically in it's own workflow in the CI/CD environment to teardown
# instances that have exceeded a lifetime limit

import datetime
from typing import Iterable, Tuple, Any
from xmlrpc.client import DateTime
import pytz
import boto3
import sys

from platform_lib import Platform
from common import get_platform_lib
from github_common import deregister_runners

# Reuse manager utilities
from ci_variables import ci_env
sys.path.append(ci_env['GITHUB_WORKSPACE'] + "/deploy")

# The number of hours a manager instance may exist since its initial launch time
INSTANCE_LIFETIME_LIMIT_HOURS = 8
# The number of hours a fpga instance may exist since its initial launch time
FPGA_INSTANCE_LIFETIME_LIMIT_HOURS = 1

def find_timed_out_resources(hr_limit: int, current_time: DateTime, resource_list: Iterable[Tuple]) -> list:
    """
    Because of the differences in how AWS and Azure store time tags, the resource_list
    in this case is a list of tuples with the 0 index being the instance/vm and the 1 index
    a datetime object corresponding to the time
    """
    timed_out = []
    for resource_tuple in resource_list:
        lifetime_secs = (current_time - resource_tuple[1]).total_seconds()
        if lifetime_secs > (hr_limit * 3600):
            timed_out.append(resource_tuple[0])
    return timed_out

def cull_aws_instances(current_time: DateTime) -> None:
    # Grab all instances with a CI-generated tag
    aws_platform_lib = get_platform_lib(Platform.AWS)
    all_ci_instances = aws_platform_lib.find_all_ci_instances()
    select_ci_instances = aws_platform_lib.find_select_ci_instances()

    client = boto3.client('ec2')

    instances_to_terminate = find_timed_out_resources(FPGA_INSTANCE_LIFETIME_LIMIT_HOURS, current_time, map(lambda x: (x, x['LaunchTime']), select_ci_instances))
    instances_to_terminate += find_timed_out_resources(INSTANCE_LIFETIME_LIMIT_HOURS, current_time, map(lambda x: (x, x['LaunchTime']), all_ci_instances))
    instances_to_terminate = list(set(instances_to_terminate))

    print("Terminated Instances:")
    for inst in instances_to_terminate:
        deregister_runners(ci_env['PERSONAL_ACCESS_TOKEN'], f"aws-{ci_env['GITHUB_RUN_ID']}")
        client.terminate_instances(InstanceIds=[inst['InstanceId']])
        print("  " + inst['InstanceId'])

    if len(instances_to_terminate > 0):
        exit(1)

def cull_azure_resources(current_time: DateTime) -> None:
    azure_platform_lib = get_platform_lib(Platform.AZURE)
    all_azure_ci_vms = azure_platform_lib.find_all_ci_instances()
    select_azure_ci_vms = azure_platform_lib.find_select_ci_instances()

    vms_to_terminate = find_timed_out_resources(FPGA_INSTANCE_LIFETIME_LIMIT_HOURS, current_time, \
        map(lambda x: (x, datetime.datetime.strptime(x['LaunchTime'],'%Y-%m-%d %H:%M:%S.%f%z')), select_azure_ci_vms))
    vms_to_terminate += find_timed_out_resources(INSTANCE_LIFETIME_LIMIT_HOURS, current_time, \
        map(lambda x: (x, datetime.datetime.strptime(x['LaunchTime'],'%Y-%m-%d %H:%M:%S.%f%z')), all_azure_ci_vms))
    vms_to_terminate = list(set(vms_to_terminate))

    print("Terminated VMs:")
    for vm in vms_to_terminate:
        deregister_runners(ci_env['PERSONAL_ACCESS_TOKEN'], f"azure-{ci_env['GITHUB_RUN_ID']}")
        azure_platform_lib.terminate_azure_vms([vm]) #prints are handled in here

    if len(vms_to_terminate > 0):
        exit(1)

def main():
    # Get a timezone-aware datetime instance
    current_time = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)

    cull_aws_instances(current_time)
    #cull_azure_resources(current_time)

if __name__ == "__main__":
    main()
