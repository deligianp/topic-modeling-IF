from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.core.cache import cache

from admin_tasks.management.commands import fetch_src_files as fsf
from admin_tasks.management.commands import lda_model


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
    return {
        "result_message": "OK"
    }


@shared_task(bind=True)
def create_model(self, model_name, path, description, training_context, is_main, topn, preprocessor_name, use_tfidf):
    task_description = "Registering LDA model \"{}\"".format(model_name)
    task_id = self.request.id
    updater = TaskUpdater(task_id, progress_margin=5, task_description=task_description)
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
    return {
        "result_message": "Registered model \"{}\" with \"{}\" topics from \"{}\".".format(
            *list(result[:3])
        ) + (
                              "The model was set as the main LDA model." if result[3] else ""
                          )
    }
