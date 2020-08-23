from django.urls import path, re_path
from . import views

app_name = "admin_tasks"
urlpatterns = [
    path('', views.index, name="index"),
    path("register-model/", views.register_model, name="register_model"),
    path("delete-model-<model_name>/", views.delete_model),
    path("list-models/model-<model_name>/", views.update_model, name="update_model"),
    path("list-models/", views.list_models, name="list_models"),
    path("list-file-groups/", views.list_file_groups, name="list_file_groups"),
    path("list-file-groups/file-group-<group_name>/", views.update_file_group, name="update_file_group"),
    path("register-data-processing-node/", views.register_data_processing_node, name="register_data_processing_node"),
    path("delete-data-processing-node-<host_user>/", views.delete_data_processing_node,
         name="delete_data_processing_node"),
    path("list-data-processing-nodes/", views.list_data_processing_nodes, name="list_data_processing_nodes"),
    path("list-data-processing-nodes/data-processing-node-<host_user>/", views.update_data_processing_node,
         name="update_data_processing_node"),
    path("load_corpus/", views.load_corpus, name="load_corpus"),
    path("list_artictles/", views.list_articles, name="list_articles"),
    path("list_articles/article-<article_identifier>", views.update_article, name="update_article"),
    path("delete_article-<article_identifier>/", views.delete_article, name="delete_article"),
    path("add_comparison/", views.add_comparison, name="add_comparison"),
    path("list_comparisons/", views.list_comparisons, name="list_comparisons"),
    path("list_comparisons/<comparison_name>", views.update_comparison, name="update_comparison"),
    path("delete-comparison-<comparison_name>/", views.delete_comparison, name="delete_comparison"),
    path("ajax/active-tasks/", views.ajax_polling_task_progress, name="poll_active_tasks"),
    path("ajax/check-model-name-availability/", views.ajax_ensure_unique_model_name,
         name="check_model_name_availability"),
    path("sftp-resources-withdrawal/", views.sftp_resource_withdrawal, name="sftp_resources_withdrawal")

    # TODO: can we make something smart that fills the links of each page
    # re_path(r'a\d',views.index),
    # re_path(r'([.]\/)*',views.index)
]
