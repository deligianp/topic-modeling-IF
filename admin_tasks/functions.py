import json
from django_celery_results.models import TaskResult
from stat import S_ISDIR
import os


def fetch_task(referenced_task_id):
    task_result = TaskResult.objects.get(task_id=referenced_task_id)
    if task_result.status == "SUCCESS":
        result_message = ""
        try:
            result_dictionary = json.loads(task_result.result)
            result_message = result_dictionary["result_message"]
        except json.JSONDecodeError:
            result_message = task_result.result
        return {
            "task_id": task_result.task_id,
            "progress": 100.0,
            "status": "SUCCESS",
            "task_description": "Task successful",
            "progress_description": result_message
        }
    elif task_result.status == "FAILURE":
        error_message_list = json.loads(task_result.result)["exc_message"]
        return {
            "task_id": task_result.task_id,
            "progress": 0.0,
            "status": "FAILURE",
            "task_description": "Task failed",
            "progress_description": ", ".join([str(item) for item in error_message_list])
        }
    else:
        return {
            "task_id": task_result.task_id,
            "progress": 0.0,
            "status": "UNKNOWN",
            "task_description": "Task final state unknown",
            "progress_description": "Task finished but couldn't determine if it was successful or not. "
                                    "This is not supposed to occur."
        }


def sftp_discover_subdirectories(sftp_handle, root_directory=""):
    subdirectories_paths = sorted(
        [
            os.path.join(root_directory, str(file.filename)) for file in sftp_handle.listdir_attr(root_directory)
            if S_ISDIR(file.st_mode)
        ]
    )

    for directory in subdirectories_paths:
        subdirectories_paths.extend([
            os.path.join(directory, str(file.filename)) for file in sftp_handle.listdir_attr(directory)
            if S_ISDIR(file.st_mode)
        ])
    return subdirectories_paths
