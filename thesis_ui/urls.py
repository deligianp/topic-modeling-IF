from django.urls import path, re_path
from . import views

urlpatterns = [
    path("search-articles/", views.search_articles),
    path("topics/article-<article_id>/", views.topic_analysis),
    path("topics/article-<article_id>/ajax/document-topics/", views.ajax_article_topics),
    path("topics/topic-<topic_index>/ajax/topic-evolution/", views.ajax_topic_evolution),
    path("topics/topic-<topic_index>/ajax/topic-terms/", views.ajax_get_topic_terms),
    path("topics/topic-<topic_index>/", views.topic_show),
    path("new-article/", views.new_article_topic_analysis),
    path("new-article/ajax/text-topics/", views.ajax_text_topics),
    path('', views.home),
    # TODO: can we make something smart that fills the links of each page
    # re_path(r'a\d',views.index),
    # re_path(r'([.]\/)*',views.index)
]
