from __future__ import absolute_import, unicode_literals
from admin_tasks.management.commands import lda_model
from admin_tasks.management.commands import fetch_src_files as fsf
from celery import shared_task
from celery_progress.backend import ProgressRecorder, Progress
from django.db import transaction
from django.db import IntegrityError
from pickle import UnpicklingError
import json
import random
import time
from django.core.cache import cache


class TaskUpdater:

    def __init__(self, task_id, progress_margin=1, task_description=""):
        self.task_id = task_id
        self.progress_margin = progress_margin
        self.task_description = task_description

        self.task_progress = 0.0
        cache.set("active_admin_task", {
            "task_id": self.task_id,
            "progress": self.task_progress,
            "status": "RUNNING",
            "task_description": self.task_description,
            "progress_description": ""
        }, 86400)

    def update(self, current_progress, progress_max=100, progress_description=""):
        current_progess_percentage = int(10000 * current_progress / progress_max) / 100
        if current_progess_percentage == 0 or current_progess_percentage - self.task_progress > self.progress_margin:
            # Update memcache
            cache.set("active_admin_task", {
                "task_id": self.task_id,
                "progress": current_progess_percentage,
                "status": "RUNNING",
                "task_description": self.task_description,
                "progress_description": progress_description
            }, 86400)
            self.task_progress = current_progess_percentage

    def mark_finished(self):
        cache.set("active_admin_task", None)


@shared_task(bind=True)
def fetch_src_files(self, host, username, password, directory, *file_names):
    print(file_names)
    task_description = "Retrieving resource files \"{}\"".format("\", \"".join(file_names))
    task_id = self.request.id
    updater = TaskUpdater(task_id, progress_margin=1, task_description=task_description)

    try:
        result = fsf.fetch_src_files(host, username, password, directory, *file_names,
                                     callback=lambda c, t, m: updater.update(c, progress_max=t, progress_description=m))
    finally:
        updater.mark_finished()
    # updater.update(100, 100, 1, progress_description="Registered model \"{}\" with \"{}\" topics from \"{}\".".format(
    #     *list(result[:3])
    # ) + ("The model was set as the main LDA model." if result[3] else ""))
    return {
        "result_message": "OK"
    }


@shared_task(bind=True)
def create_model(self, model_name, path, description, training_context, is_main, topn, preprocessor_name, use_tfidf):
    # progress_recorder = ProgressRecorder(self)
    task_description = "Registering LDA model \"{}\"".format(model_name)
    task_id = self.request.id
    # progress_recorder.set_progress(0, 100, description={
    #     "task_description": task_description,
    #     "progress_description": ""
    # })
    # AdminTask.objects.filter(is_active=True).update(is_active=False)
    # task = AdminTask(task_id=task_id, is_active=True, progress=0, status=0, task_description=task_description,
    #                  progress_description="Loading model file")
    # task.save()
    updater = TaskUpdater(task_id, progress_margin=5, task_description=task_description)
    # updater.update(0, 100, 0, progress_description="Loading model file")
    try:
        result = lda_model.create_model(model_name, path, description,
                                        training_context=training_context,
                                        main=is_main,
                                        topn=topn,
                                        preprocessor_name=preprocessor_name,
                                        use_tfidf=use_tfidf,
                                        callback=lambda c, t, m: updater.update(c, progress_max=t,
                                                                                progress_description=m))
    except Exception as ex:
        raise ex
    finally:
        updater.mark_finished()
    # updater.update(100, 100, 1, progress_description="Registered model \"{}\" with \"{}\" topics from \"{}\".".format(
    #     *list(result[:3])
    # ) + ("The model was set as the main LDA model." if result[3] else ""))
    return {
        "result_message": "Registered model \"{}\" with \"{}\" topics from \"{}\".".format(
            *list(result[:3])
        ) + (
                              "The model was set as the main LDA model." if result[3] else ""
                          )
    }

# @shared_task(bind=True)
# def proxy_worker_job(self, referenced_task_id=None):
#     print(self.request.id)
# if referenced_task_id is not None:
#     foo_job.delay(100)
# else:
#     progress_report = Progress(referenced_task_id)
#     progress_info = progress_report.get_info()
#     if progress_info["complete"]:
#         if progress_info["success"] is not None:
#             if progress_info["success"]:  # Case: Referenced task finished successfully
#                 admin_task_object = AdminTask.objects.get()
#                 admin_task_object.is_active = False
#                 admin_task_object.status = 1
#                 admin_task_object.description = json.dumps({"task_description": str(res)})
#                 admin_task_object.save()
#                 # result_string = progress_report.result.get()
#                 # referenced_result = {
#                 #     "task_id": ereferenced_task_id,
#                 #     "execution": "SUCCESSFUL",
#                 #     "task_description": str(result_string),
#                 #     "worker_description": "Task successful"
#                 # }
#             else:  # Case: Referenced task failed with an error
#                 admin_task_object = AdminTask.objects.get()
#                 admin_task_object.is_active = False
#                 admin_task_object.save()
#                 # err_string = str(progress_report.result.result)
#                 # referenced_result = {
#                 #     "task_id": prereferenced_task_id,
#                 #     "execution": "FAILED",
#                 #     "task_description": err_string,
#                 #     "worker_description": "Task failed"
#                 # }
#         else:  # Case: Referenced task's state is unknown
#             admin_task_object = AdminTask.objects.get()
#             admin_task_object.is_active = False
#             admin_task_object.save()
#             # referenced_result = {
#             #     "task_id": prereferenced_task_id,
#             #     "execution": "UNKNOWN",
#             #     "task_description": "Task could not be tracked",
#             #     "worker_description": "Task status unknown"
#             # }
#     else:
#         referenced_result = {
#             "task_id": prereferenced_task_id,
#             "execution": "RUNNING",
#             "current": progress_info["progress"]["current"],
#             "total": progress_info["progress"]["total"],
#             "worker_description": progress_info["progress"]["description"]["task_description"],
#             "task_description": progress_info["progress"]["description"]["progress_description"]
#         }
#         return JsonResponse({
#             "worker_status": "RUNNING",
#             "task": referenced_result
#         })
