from django.core.management.base import BaseCommand
from admin_tasks.models import DataProcessingNode, FileExtension, FileGroup
import getpass
import paramiko
from admin_tasks.functions import sftp_discover_subdirectories

import os

from thesis_django.settings import RESOURCES_DIRECTORY


class RegisteredHostKeyPolicy(paramiko.client.MissingHostKeyPolicy):

    def missing_host_key(self, client, hostname, key):
        try:
            allowed_hosts = [item["host"] for item in DataProcessingNode.objects.all().values("host")]
        except Exception as ex:
            allowed_hosts = []
        if hostname in allowed_hosts:
            return key
        raise Exception(f"Host \"{hostname}\" is not registered as a known host")


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("files_name", help="The common name of the files to fetch from the registered host")
        parser.add_argument("file_type", help="Acceptable file group types")
        parser.add_argument("host", help="Registered host address. The host must be registered by an administrator")

    def handle(self, *args, **kwargs):
        host_address = kwargs["host"]
        try:
            registered_data_node = DataProcessingNode.objects.get(host=host_address)
        except DataProcessingNode.DoesNotExist as ex:
            print("Host {} is not registered".format(host_address))
            return
        host = registered_data_node.host
        username = registered_data_node.username
        directory = registered_data_node.withdrawal_directory
        password = getpass.getpass(
            prompt="Password for user {}@{}: ".format(username, host))
        file_names = set(kwargs["files_name"] + "." + res["extension"] for res in
                         FileExtension.objects.filter(file_group__name=kwargs["file_type"]).values())
        # print(file_names)
        #
        print("Will fetch files from host {}, for user {}: {}".format(host, username, ", ".join(file_names)))

        callback = lambda c, t, f: print("\rFile \"{}\": {}%".format(f, int(100 * c / t)), end="")

        fetch_src_files(host, username, password, directory, *file_names, callback=callback)

        print()


def fetch_src_files(host, username, password, directory, *file_names, callback=None):
    successful_transmission = False
    ssh_handle = paramiko.SSHClient()
    ssh_handle.set_missing_host_key_policy(RegisteredHostKeyPolicy)
    ssh_handle.connect(host, username=username, password=password, look_for_keys=False)
    try:
        sftp_handle = ssh_handle.open_sftp()
        try:
            sftp_handle.chdir(directory)
            selected_directory = None
            if len(set(file_names).difference(set(sftp_handle.listdir(directory)))) != 0:
                possible_subdirectories = sftp_discover_subdirectories(sftp_handle)
                for subdirectory in possible_subdirectories:
                    if len(set(file_names).difference(set(sftp_handle.listdir(subdirectory)))) == 0:
                        selected_directory = subdirectory

                        break
            else:
                selected_directory = directory
            if selected_directory is not None:
                file_sizes = [sftp_handle.stat(selected_directory + "/" + file_name).st_size for file_name in
                              file_names]
                total_transmission_size = sum(file_sizes)
                for i in range(len(file_names)):
                    # completed = 0 if i ==0 else sum(file_sizes[:i])
                    sftp_handle.get(selected_directory + "/" + file_names[i],
                                    os.path.join(RESOURCES_DIRECTORY, file_names[i]),
                                    callback=lambda c, t: callback(c + sum(file_sizes[:i]), total_transmission_size,
                                                                   "Retrieving \"{}\"".format(file_names[i])))
                successful_transmission = True
            else:
                raise FileNotFoundError(
                    "Could not locate files ({}) under \"{}\"".format(", ".join(file_names), directory))
        finally:
            sftp_handle.close()
    finally:
        ssh_handle.close()
    return successful_transmission
