import os

from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db import IntegrityError, DataError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.text import slugify
from django_celery_results.models import TaskResult

from admin_tasks import forms as atforms
from admin_tasks import functions
from admin_tasks import models as atmodels
from admin_tasks import tasks
from admin_tasks.celery import app as app_worker
from admin_tasks.management.commands import lda_model, data_processing_node, file_group
from thesis_ui import models as thesis_models

inspector = app_worker.control.inspect()


# Create your views here.

@staff_member_required
def index(request):
    # result = fetch_src_files.delay("83.212.72.179", "deligiannis", "Z09!@mPQAL", "/mnt/vdb/data",
    #                                "native_nstemmed.dict")
    return render(request, 'admin_tasks/tasks_map.html')


def ajax_polling_task_progress(request):
    if request.user.is_staff:
        if request.method == "POST":
            referenced_task_id = request.POST.get("task_id", None)
            if referenced_task_id == "":
                referenced_task_id = None
            active_task = cache.get("active_admin_task", None)

            worker_status = "IDLE"
            referenced_task_result = None
            new_task_result = None

            if not referenced_task_id:
                if active_task:
                    new_task_result = {
                        "task_id": active_task["task_id"],
                        "progress": active_task["progress"],
                        "status": active_task["status"],
                        "task_description": active_task["task_description"],
                        "progress_description": active_task["progress_description"]
                    }
                    worker_status = "RUNNING"
            else:
                if not active_task:
                    try:
                        referenced_task_result = functions.fetch_task(referenced_task_id)
                        worker_status = "IDLE"
                    except TaskResult.DoesNotExist:
                        pass
                else:
                    worker_status = "RUNNING"
                    if active_task["task_id"] == referenced_task_id:
                        referenced_task_result = {
                            "task_id": active_task["task_id"],
                            "progress": active_task["progress"],
                            "status": active_task["status"],
                            "task_description": active_task["task_description"],
                            "progress_description": active_task["progress_description"]
                        }
                    else:
                        try:
                            referenced_task_result = functions.fetch_task(referenced_task_id)
                        except TaskResult.DoesNotExist:
                            pass
                        new_task_result = {
                            "task_id": active_task["task_id"],
                            "progress": active_task["progress"],
                            "status": active_task["status"],
                            "task_description": active_task["task_description"],
                            "progress_description": active_task["progress_description"]
                        }
            return JsonResponse({
                "worker_status": worker_status,
                "referenced_task": referenced_task_result,
                "new_task": new_task_result
            })


def ajax_ensure_unique_model_name(request):
    if request.user.is_staff:
        if request.method == "POST":
            model_name = request.POST.get("model_name", None)
            if model_name is not None:
                try:
                    thesis_models.LdaModel.objects.get(name=model_name)
                except thesis_models.LdaModel.DoesNotExist:
                    return JsonResponse({"model_name": model_name, "availability": "AVAILABLE"})
                return JsonResponse({"model_name": model_name, "availability": "UNAVAILABLE"})


# ==================================================================================================================== #
# ==================================================================================================================== #
# ==================================================================================================================== #

@staff_member_required
def register_model(request):
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "Register model"}
    ]
    if request.method == "GET":
        task_form = atforms.LdaModelForm()
    else:
        task_form = atforms.LdaModelForm(request.POST)
        if task_form.is_valid():
            active_task = cache.get("active_admin_task", None)
            if active_task is None:
                new_model_name = slugify(task_form.cleaned_data["name"])
                path = task_form.cleaned_data["path"]
                if thesis_models.LdaModel.objects.filter(name=new_model_name).exists():
                    task_form.add_error("name",
                                        "Another LDA model with named as \"{}\" already exists".format(new_model_name))
                elif thesis_models.LdaModel.objects.filter(path=path).exists():
                    task_form.add_error("path",
                                        "Another LDA model that points to the model file at \"{}\" already "
                                        "exists".format(path))
                else:
                    description = task_form.cleaned_data["description"]
                    training_context = task_form.cleaned_data["training_context"]
                    topn = task_form.cleaned_data["top_N_terms"]
                    is_main = task_form.cleaned_data["is_main"]
                    preprocessor_name = task_form.cleaned_data["preprocessor_name"]
                    use_tfidf = task_form.cleaned_data["use_tfidf"]
                    tasks.create_model.delay(new_model_name, path, description, training_context, is_main, topn,
                                             preprocessor_name, use_tfidf)
                    return redirect("/admin-tasks/list-models/")
            else:
                template_context["form_error"] = "New model cannot be registered because another task is currently " \
                                                 "active"
    template_context["task_form"] = task_form
    template_context["form_heading"] = "Register a model"
    return render(request, 'admin_tasks/task_form.html', context=template_context)


@staff_member_required
def list_models(request):
    models = thesis_models.LdaModel.objects.all()
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "List models"}
    ]
    template_context["obj"] = {
        "headings": ["Loaded LDA models"],
        "data": [
            {
                "label": str(model) + "@{}".format(model.path),
                "url": "model-" + model.name + "/",
                "name": model.name
            } for model in models
        ],
        "delete_link_prefix": "delete-model-"
    }
    return render(request, 'admin_tasks/db_object_listing.html', context=template_context)


@staff_member_required
def update_model(request, *args, **kwargs):
    model_name = kwargs.get("model_name", None)
    if model_name is not None:
        template_context = dict()
        template_context["path_links"] = [
            {"url": "/admin-tasks", "label": "Admin tasks"},
            {"url": "/admin-tasks/list-models", "label": "List models"},
            {"label": "Update model"}
        ]
        try:
            target_model = thesis_models.LdaModel.objects.get(name=model_name)
        except thesis_models.LdaModel.DoesNotExist as dne:
            return redirect("/admin-tasks/list-models/")
        if request.method == "GET":
            task_form = atforms.LdaModelForm(initial={
                "name": target_model.name,
                "description": target_model.description,
                "training_context": target_model.training_context,
                "is_main": target_model.is_main,
                "preprocessor_name": target_model.preprocessor_name,
                "use_tfidf": target_model.use_tfidf
            }, update=True)
            template_context["task_form"] = task_form
        else:
            task_form = atforms.LdaModelForm(request.POST, update=True)
            backend_error = False
            if task_form.is_valid():
                new_name = task_form.cleaned_data["name"] \
                    if task_form.cleaned_data["name"] != target_model.name else None
                description = task_form.cleaned_data["description"] \
                    if task_form.cleaned_data["description"] != target_model.description else None
                training_context = task_form.cleaned_data["training_context"] \
                    if task_form.cleaned_data["training_context"] != target_model.training_context else None
                set_main = task_form.cleaned_data["is_main"] \
                    if task_form.cleaned_data["is_main"] != target_model.is_main else None
                preprocessor_name = task_form.cleaned_data["preprocessor_name"] \
                    if task_form.cleaned_data["preprocessor_name"] != target_model.preprocessor_name else None
                use_tfidf = task_form.cleaned_data["use_tfidf"] \
                    if task_form.cleaned_data["use_tfidf"] != target_model.use_tfidf else None
                template_context["task_form"] = task_form
                try:
                    lda_model.update_model(model_name, new_name=new_name, description=description,
                                           training_context=training_context, set_main=set_main,
                                           preprocessor_name=preprocessor_name, use_tfidf=use_tfidf)
                except IntegrityError as interr:
                    task_form.add_error("name",
                                        "Another LDA model with named as \"{}\" already exists".format(new_name))
                    # template_context["form_heading"] = "Update model \"{}\"".format(model_name)
                    backend_error = True
                except thesis_models.LdaModel.DoesNotExist as dne:
                    return redirect("/admin-tasks/list-models")
                except Exception as ex:
                    template_context["form_error"] = str(ex)
                    backend_error = True
                if not backend_error:
                    return redirect('/admin-tasks/list-models/')
        template_context["form_heading"] = "Update model {}, loaded from \"{}\"".format(
            target_model.description, target_model.path
        )
        template_context["task_form"] = task_form
        return render(request, 'admin_tasks/task_form.html', context=template_context)
    else:
        return redirect('/admin-tasks/list-models/')


@staff_member_required
def delete_model(request, *args, **kwargs):
    model_name = kwargs["model_name"]
    if request.method == "POST":
        try:
            lda_model.delete_model(model_name)
        except thesis_models.LdaModel.DoesNotExist as dne:
            pass
    return redirect("/admin-tasks/list-models/")


@staff_member_required
def sftp_resource_withdrawal(request):
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "Withdraw resource files"}
    ]
    template_context["form_heading"] = "Withdraw resource files from host"
    if request.method == "GET":
        sftp_form = atforms.SFTPWithdrawalForm()
    else:
        sftp_form = atforms.SFTPWithdrawalForm(request.POST)
        active_task = cache.get("active_admin_task", None)
        if active_task is None:
            if sftp_form.is_valid():
                username, data_node_host = sftp_form.cleaned_data["data_node_host"].split("@")
                file_name = sftp_form.cleaned_data["associated_name"]
                file_type = sftp_form.cleaned_data["files_type"]
                password = sftp_form.cleaned_data["host_password_field"]
                file_extensions = atmodels.FileExtension.objects.filter(file_group__name=file_type).values(
                    "extension")
                directory = atmodels.DataProcessingNode.objects.get(host=data_node_host).withdrawal_directory
                target_files = [file_name + "." + extension["extension"] for extension in file_extensions]
                tasks.fetch_src_files.delay(data_node_host, username, password, directory, *target_files)
                return redirect("/admin-tasks/")
        else:
            template_context["form_error"] = "Resource files cannot be retrieved as another administration task is " \
                                             "currently running"
    template_context["task_form"] = sftp_form
    template_context["form_heading"] = "Withdraw resource files through SFTP"
    return render(request, 'admin_tasks/task_form.html', context=template_context)


@staff_member_required
def list_file_groups(request):
    file_groups = atmodels.FileGroup.objects.all()
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "List file groups"}
    ]
    template_context["obj"] = {
        "headings": ["File groups"],
        "data": [
            {"label": group.description, "url": "file-group-" + group.name + "/", "name": group.description}
            for group in file_groups
        ],
        "delete_allowed": False
    }
    return render(request, 'admin_tasks/db_object_listing.html', context=template_context)


@staff_member_required
def update_file_group(request, *args, **kwargs):
    group_name = kwargs.get("group_name", None)
    if group_name is not None:
        template_context = dict()
        template_context["path_links"] = [
            {"url": "/admin-tasks", "label": "Admin tasks"},
            {"url": "/admin-tasks/list-file-groups", "label": "List file groups"},
            {"label": "Update file group"}
        ]

        group_extensions = atmodels.FileGroup.objects.filter(name=group_name).values(
            "description",
            "fileextension__extension"
        )
        if len(group_extensions) > 0:
            group_extensions_object = [group_extensions[0]["description"], " ".join(
                [extension_record["fileextension__extension"] for extension_record in group_extensions])]
            if request.method == "GET":
                group_form = atforms.FileGroupForm(initial={
                    "description": group_extensions_object[0],
                    "extensions": group_extensions_object[1]
                })
            else:
                group_form = atforms.FileGroupForm(request.POST)
                backend_error = False
                if group_form.is_valid():
                    description = group_form.cleaned_data["description"] \
                        if group_form.cleaned_data["description"] != group_extensions_object[0] else None
                    extensions_list = group_form.cleaned_data["extensions"].split() \
                        if group_form.cleaned_data["extensions"] != group_extensions_object[1] else None
                    try:
                        file_group.update_file_group(group_name, description=description,
                                                     extensions_list=extensions_list)
                    except atmodels.FileGroup.DoesNotExist as fg_dne:
                        return redirect("/admin-tasks/list-file-groups/")
                    except Exception as ex:
                        backend_error = True
                        template_context["form_error"] = str(ex)
                    if not backend_error:
                        return redirect("/admin-tasks/list-file-groups/")
                # try:
                #     pass
                # except IntegrityError as interr:
                #     task_form.add_error("name",
                #                         "Another LDA model with named as \"{}\" already exists".format(new_name))
                #     template_context["form_heading"] = "Update model \"{}\"".format(model_name)
                #     return render(request, 'admin_tasks/task_form.html', context=template_context)
                # except thesis_models.LdaModel.DoesNotExist as dne:
                #     pass
            template_context["task_form"] = group_form
            template_context["form_heading"] = "Update extensions or description for file group \"{}\"".format(
                group_extensions_object[0])
            return render(request, 'admin_tasks/task_form.html', context=template_context)
    return redirect('/admin-tasks/list-file-groups/')


@staff_member_required
def register_data_processing_node(request):
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "Register a data processing node"}
    ]
    if request.method == "GET":
        data_processing_node_form = atforms.DataProcessingNodeForm()
    else:
        data_processing_node_form = atforms.DataProcessingNodeForm(request.POST)
        if data_processing_node_form.is_valid():
            host_address = data_processing_node_form.cleaned_data["host_address"]
            username = data_processing_node_form.cleaned_data["host_username"]
            withdrawal_directory = data_processing_node_form.cleaned_data["withdrawal_directory"]
            backend_error = False
            try:
                data_processing_node.register_data_processing_node(host_address, username, withdrawal_directory)
            except IntegrityError as dpn_ie:
                data_processing_node_form.add_error("host_address", str(dpn_ie))
                backend_error = True
            except DataError as dpn_de:
                data_processing_node_form.add_error("host_address", str(dpn_de))
                backend_error = True
            except Exception as ex:
                template_context["form_error"] = str(ex)
                backend_error = True
            if not backend_error:
                return redirect('/admin-tasks/list-data-processing-nodes/')
    template_context["task_form"] = data_processing_node_form
    template_context["form_heading"] = "Register a data processing node"
    return render(request, 'admin_tasks/task_form.html', context=template_context)


@staff_member_required
def list_data_processing_nodes(request):
    data_processing_nodes = atmodels.DataProcessingNode.objects.all()
    next_page_index = int(request.GET.get("page", 1))
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "List data processing nodes"}
    ]
    # template_context["pagination"] = {"current": next_page_index, "max": 13}
    template_context["obj"] = {
        "headings": ["Registered data processing nodes"],
        "data": [
            {
                "label": str(node),
                "url": "data-processing-node-" + node.host.replace(".", "_") + "/",
                "name": node.host
            } for node in data_processing_nodes
        ],
        "delete_link_prefix": "delete-data-processing-node-"
    }
    return render(request, 'admin_tasks/db_object_listing.html', context=template_context)


@staff_member_required
def delete_data_processing_node(request, *args, **kwargs):
    host_user = kwargs["host_user"]
    if request.method == "POST":
        try:
            atmodels.DataProcessingNode.objects.get(host=host_user).delete()
        except thesis_models.LdaModel.DoesNotExist as dne:
            pass
    return redirect("/admin-tasks/list-data-processing-nodes/")


@staff_member_required
def update_data_processing_node(request, *args, **kwargs):
    host_user = kwargs.get("host_user", None)
    if host_user is not None:
        template_context = dict()
        template_context["path_links"] = [
            {"url": "/admin-tasks/", "label": "Admin tasks"},
            {"url": "/admin-tasks/list-data-processing-nodes/", "label": "List data processing nodes"},
            {"label": "Update data processing node"}
        ]
        target_host = host_user.replace("_", ".")
        try:
            target_host = atmodels.DataProcessingNode.objects.get(host=target_host)
        except atmodels.DataProcessingNode.DoesNotExist as dne:
            return redirect('/admin-tasks/list-data-processing-nodes/')

        if request.method == "GET":
            data_processing_node_form = atforms.DataProcessingNodeForm(initial={
                "host_address": target_host.host,
                "host_username": target_host.username,
                "withdrawal_directory": target_host.withdrawal_directory
            })
            template_context["form_heading"] = "Update information for data processing node at {}".format(
                target_host.host)
        else:
            data_processing_node_form = atforms.DataProcessingNodeForm(request.POST)
            if data_processing_node_form.is_valid():
                backend_error = False
                host = data_processing_node_form.cleaned_data["host_address"] \
                    if data_processing_node_form.cleaned_data["host_address"] != target_host.host else None
                username = data_processing_node_form.cleaned_data["host_username"] \
                    if data_processing_node_form.cleaned_data["host_username"] != target_host.username else None
                withdrawal_directory = data_processing_node_form.cleaned_data["withdrawal_directory"] \
                    if data_processing_node_form.cleaned_data[
                           "withdrawal_directory"
                       ] != target_host.withdrawal_directory else None
                try:
                    data_processing_node.update_data_processing_node(target_host.host, new_host_ipv4=host,
                                                                     username=username,
                                                                     withdrawal_directory=withdrawal_directory)
                except IntegrityError as dpn_ie:
                    data_processing_node_form.add_error("host_address", str(dpn_ie))
                    backend_error = True
                except DataError as dpn_de:
                    redirect("/admin-tasks/list-data-processing-nodes/")
                except atmodels.DataProcessingNode.DoesNotExist as dpn_dne:
                    redirect("/admin-tasks/list-data-processing-nodes/")
                if not backend_error:
                    redirect("/admin-tasks/list-data-processing-nodes/")
        template_context["task_form"] = data_processing_node_form
        return render(request, "admin_tasks/task_form.html", context=template_context)
    else:
        return redirect('/admin-tasks/list-data-processing-nodes/')


def load_corpus(request):
    template_context = dict()
    template_context["path_links"] = [
        {"url": "/admin-tasks", "label": "Admin tasks"},
        {"label": "Load corpus"}
    ]
    if request.method == "GET":
        corpus_loading_form = atforms.CorpusLoadingForm()
    else:
        corpus_loading_form = atforms.CorpusLoadingForm(request.POST)
        if corpus_loading_form.is_valid():
            corpus_files_paths_input = corpus_loading_form.cleaned_data["corpus_files_paths"]
            reader_to_use = corpus_loading_form.cleaned_data["reader_to_use"]
            backend_error = False

            corpus_files_paths = [os.path.abspath(path) for path in corpus_files_paths_input.split("\r\n")]
            for path in corpus_files_paths:
                if not os.path.exists(path):
                    backend_error = True
                    corpus_loading_form.add_error("corpus_files_paths", "Path \"{}\" does not exist")
                    break
            if not backend_error:
                try:
                    pass
                except IntegrityError as dpn_ie:
                    corpus_loading_form.add_error("corpus_files_paths", str(dpn_ie))
                    backend_error = True
                except DataError as dpn_de:
                    corpus_loading_form.add_error("reader_to_use", str(dpn_de))
                    backend_error = True
                except Exception as ex:
                    template_context["form_error"] = str(ex)
                    backend_error = True
                if not backend_error:
                    return redirect('/admin-tasks/list-articles/')
    template_context["task_form"] = corpus_loading_form
    template_context["form_heading"] = "Load corpus articles into the database"
    return render(request, 'admin_tasks/task_form.html', context=template_context)


def update_article(request, *args, **kwargs):
    pass


def list_articles(request):
    pass


def delete_article(request, *args, **kwargs):
    pass


def add_comparison(request):
    pass


def update_comparison(request, *args, **kwargs):
    pass


def list_comparisons(request):
    pass


def delete_comparison(request, *args, **kwargs):
    pass
