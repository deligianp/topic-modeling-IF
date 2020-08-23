from django.shortcuts import render
from thesis_ui import models
from resources import lda_query
from django.http import JsonResponse, Http404
from django.db.models import Count, Min, Max, Subquery, F
from django.db import transaction
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.search import SearchRank, SearchQuery
from django.db import IntegrityError
import resources.configuration as config
from resources.static import generate_navbar
import os
import re
import json
import bz2
import pickle
import numpy as np
from .forms import SearchForm, NewArticleForm


# Create your views here.
def home(request):
    navbar_json = generate_navbar(config.NAV_BAR_ADDRESSES, {"home"})
    template_context = dict()
    template_context["data"] = {
        "text": {
            "text_title": "Placeholder title",
            "text_meta": [],
            "text_content": "<p>This is a placeholder text that is supposed to contain information about the interface"
        }
    }
    template_context["navbar"] = navbar_json
    return render(context=template_context, template_name='home.html', request=request)


def search_articles(request):
    navbar_json = generate_navbar(config.NAV_BAR_ADDRESSES, {"search_articles"})
    template_context = dict()
    template_context["navbar"] = navbar_json
    if request.method == "POST":
        search_form = SearchForm(request.POST)
        if search_form.is_valid():
            input_text = search_form.cleaned_data["search_field"]
            search_context = search_form.cleaned_data["search_context"]
            results_list = None
            if search_context == "articles":
                query = SearchQuery(input_text)
                results = models.Article.objects.filter(search_vector=query) \
                              .annotate(rank=SearchRank(F("search_vector"), query)) \
                              .order_by("-rank") \
                              .values("identifier", "title")[:config.CONFIG_VALUES["TOP_N_SEARCH_RESULTS"]]
                results_list = [
                    {
                        "url": os.path.join("/topics", "article-" + result["identifier"]),
                        "description": result["title"]
                    }
                    for result in results
                ]
            else:
                target_topic_index = int(input_text)
                results = models.ArticleTopicDistribution.objects.filter(
                    topic__index=target_topic_index,
                    topic__parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"],
                    id__in=Subquery(
                        models.ArticleTopicDistribution.objects.filter(
                            topic__index=target_topic_index,
                            topic__parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"]
                        ).order_by(
                            "article__identifier", "-value"
                        ).distinct(
                            "article__identifier"
                        ).values(
                            "id"
                        )
                    )
                ).order_by(
                    "-value"
                ).values(
                    "article__identifier", "article__title"
                )[:config.CONFIG_VALUES["TOP_N_SEARCH_RESULTS"]]
                results_list = [
                    {
                        "url": os.path.join("/topics", "article-" + result["article__identifier"]),
                        "description": result["article__title"]
                    }
                    for result in results
                ]
            template_context["search_results"] = {
                "query": input_text,
                "list": results_list
            }
    else:
        search_form = SearchForm()
    template_context["search_form"] = search_form
    return render(request, template_name='p_search_articles.html', context=template_context)


def topic_evolution(request):
    navbar_json = generate_navbar(config.NAV_BAR_ADDRESSES, {"m_topic_evo"})
    template_context = dict()
    template_context["navbar"] = navbar_json
    stored_comparisons = {row["name"]: row for row in
                          models.Comparison.objects.values("name", "description", "type_of_comparison", "lower_bound",
                                                           "upper_bound").annotate(
                              min_topic_index=Min("topics_measurement__topic_1__index")).annotate(
                              max_topic_index=Max("topics_measurement__topic_1__index"))}
    template_context['ws_required'] = {"evolutions": list(stored_comparisons.values())}
    if request.method == 'GET':
        form_submitted = request.GET.get('submit', "") == "submit"
        if form_submitted:
            selected_comparison = request.GET.get("selected_metric", "")

            # TODO: move to django.forms equivalent implementation
            try:
                target_threshold = float(request.GET.get("threshold_value", None))
                if not stored_comparisons[selected_comparison]["lower_bound"] < target_threshold < \
                       stored_comparisons[selected_comparison]["upper_bound"]:
                    raise ValueError
            except ValueError:
                template_context["server_error"] = True
                template_context["alert_title"] = "Invalid threshold for chosen distance model"
                template_context[
                    "alert_message"] = "For distance model \"{}\": {} ≤ threshold ≤ {}, threshold: real number".format(
                    stored_comparisons[selected_comparison]["description"],
                    stored_comparisons[selected_comparison]["lower_bound"],
                    stored_comparisons[selected_comparison]["upper_bound"])
                return render(context=template_context, template_name='topic-evolution.html', request=request)
            except TypeError:
                template_context["server_error"] = True
                template_context["alert_title"] = "Invalid threshold for chosen distance model"
                template_context["alert_message"] = "Threshold must be a number"
                return render(context=template_context, template_name='topic-evolution.html', request=request)

            try:
                topic_id = int(request.GET.get("topic_id", None))
                if not stored_comparisons[selected_comparison]["min_topic_index"] < topic_id < \
                       stored_comparisons[selected_comparison]["max_topic_index"]:
                    raise ValueError
            except ValueError:
                template_context["server_error"] = True
                template_context["alert_title"] = "Invalid topic index for chosen distance model"
                template_context[
                    "alert_message"] = "For distance model \"{}\": {} ≤ topic index ≤ {}, topic index: natural number".format(
                    stored_comparisons[selected_comparison]["description"],
                    stored_comparisons[selected_comparison]["min_topic_index"],
                    stored_comparisons[selected_comparison]["max_topic_index"])
                return render(context=template_context, template_name='topic-evolution.html', request=request)
            except TypeError:
                template_context["server_error"] = True
                template_context["alert_title"] = "Invalid topic index for chosen distance model"
                template_context["alert_message"] = "Topic index must be a number"
                return render(context=template_context, template_name='topic-evolution.html', request=request)
                # ========================================================

            if stored_comparisons[selected_comparison]["type_of_comparison"] == 0:
                edges = models.TopicsComparison.objects.filter(
                    topic_0__in=Subquery(
                        models.TopicsComparison.objects.filter(
                            parent_comparison__name=selected_comparison,
                            topic_1__index=topic_id,
                            value__gte=target_threshold
                        ).values("topic_0")),
                    value__gte=target_threshold,
                    parent_comparison__name=selected_comparison).values(
                    "parent_comparison__description",
                    "parent_comparison__lda_model_0__name",
                    "parent_comparison__lda_model_0__training_context",
                    "parent_comparison__lda_model_0__description",
                    "parent_comparison__lda_model_1__name",
                    "parent_comparison__lda_model_1__training_context",
                    "parent_comparison__lda_model_1__description",
                    "topic_0__index",
                    "topic_1__index",
                    "value"
                )
            else:
                edges = models.TopicsComparison.objects.filter(
                    topic_0__in=Subquery(
                        models.TopicsComparison.objects.filter(
                            parent_comparison__name=selected_comparison,
                            topic_1__index=topic_id,
                            value__lte=target_threshold
                        ).values("topic_0")),
                    value__lte=target_threshold,
                    parent_comparison__name=selected_comparison).values(
                    "parent_comparison__description",
                    "parent_comparison__lda_model_0__name",
                    "parent_comparison__lda_model_0__training_context",
                    "parent_comparison__lda_model_0__description",
                    "parent_comparison__lda_model_1__name",
                    "parent_comparison__lda_model_1__description",
                    "parent_comparison__lda_model_1__training_context",
                    "topic_0__index",
                    "topic_1__index",
                    "value"
                )
            if len(edges) == 0:
                template_context["server_error"] = True
                template_context["alert_title"] = "No topics for given threshold"
                template_context["alert_message"] = "Cannot infer any topic evolution for topic {}, satisfying the " \
                                                    "{} threshold of {}".format(
                    topic_id,
                    "minimum" if stored_comparisons[selected_comparison]["type_of_comparison"] == 0 else "maximum",
                    target_threshold)
                return render(context=template_context, template_name='topic-evolution.html', request=request)

            # Normalize
            normalized_result = dict()

            template_context["visualization"] = dict()
            template_context["visualization"]["data_description"] = dict()
            template_context["visualization"]["data_description"]["comparison_description"] = edges[0][
                "parent_comparison__description"]
            template_context["visualization"]["data_description"]["lda_model_0_description"] = edges[0][
                "parent_comparison__lda_model_0__description"]
            template_context["visualization"]["data_description"]["lda_model_0_training_context"] = edges[0][
                "parent_comparison__lda_model_0__training_context"]
            template_context["visualization"]["data_description"]["lda_model_1_description"] = edges[0][
                "parent_comparison__lda_model_1__description"]
            template_context["visualization"]["data_description"]["lda_model_1_training_context"] = edges[0][
                "parent_comparison__lda_model_1__training_context"]
            parents_dict = dict()
            for row in edges:
                topic_0_index = row["topic_0__index"]
                topic_1_index = row["topic_1__index"]
                value = row["value"]

                if topic_0_index not in parents_dict:
                    parents_dict[topic_0_index] = {
                        "name": row["parent_comparison__lda_model_0__name"] + "_" + str(topic_0_index),
                        "associations": list()
                    }

                parents_dict[topic_0_index]["associations"].append(
                    {
                        "child": {
                            "name": row["parent_comparison__lda_model_1__name"] + "_" + str(topic_1_index),
                            "highlight": topic_1_index == topic_id
                        },
                        "label": value
                    }
                )

            import json
            template_context["visualization"]["data"] = json.dumps(tuple(parents_dict.values()))
    return render(context=template_context, template_name='topic-evolution.html', request=request)


def ajax_topic_evolution(request, *args, **kwargs):
    if request.method == "POST":
        if "topic_index" in kwargs and "measure_name" in request.POST and "threshold" in request.POST:
            topic_index = int(kwargs["topic_index"])
            measure_name = request.POST["measure_name"]
            threshold = float(request.POST["threshold"])
            relative_comparison = models.Comparison.objects.get(name=measure_name)
            if relative_comparison.type_of_comparison == 0:
                result = models.TopicsComparison.objects.filter(
                    topic_0__in=Subquery(
                        models.TopicsComparison.objects.filter(
                            topic_1__index=topic_index,
                            parent_comparison__lda_model_1__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"],
                            parent_comparison__name=measure_name,
                            value__gte=threshold
                        ) \
                            .order_by("-value") \
                            .values("topic_0")[:4]),
                    parent_comparison__name=measure_name,
                    value__gte=threshold
                ).values(
                    "topic_0__index",
                    "topic_1__index",
                    "parent_comparison__lda_model_0__name",
                    "parent_comparison__lda_model_1__name",
                    "parent_comparison__lda_model_0__description",
                    "parent_comparison__lda_model_1__description",
                    "value"
                )
            else:
                result = models.TopicsComparison.objects.filter(
                    topic_0__in=Subquery(
                        models.TopicsComparison.objects.filter(
                            topic_1__index=topic_index,
                            parent_comparison__lda_model_1__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"],
                            parent_comparison__name=measure_name,
                            value__lte=threshold
                        ) \
                            .order_by("value") \
                            .values("topic_0")[:4]),
                    parent_comparison__name=measure_name,
                    value__lte=threshold
                ).values(
                    "topic_0__index",
                    "topic_1__index",
                    "parent_comparison__lda_model_0__name",
                    "parent_comparison__lda_model_1__name",
                    "parent_comparison__lda_model_0__description",
                    "parent_comparison__lda_model_1__description",
                    "value"
                )
            parents = dict()
            children = dict()
            for edge in result:
                parent_name = edge["parent_comparison__lda_model_0__name"] + "_" + str(edge["topic_0__index"])
                child_name = edge["parent_comparison__lda_model_1__name"] + "_" + str(edge["topic_1__index"])
                if parent_name in parents:
                    parent = parents[parent_name]
                else:
                    parent = {
                        "name": parent_name,
                        "associations": []
                    }
                    parents[parent_name] = parent

                if child_name in children:
                    child = children[child_name]
                else:
                    child = {
                        "name": child_name,
                        "highlight": edge["topic_1__index"] == topic_index
                    }
                    children[child_name] = child
                parent["associations"].append({"child": child, "label": edge["value"]})
            return JsonResponse({"parents": [parents[parent] for parent in parents]})


def ajax_get_topic_terms(request, *args, **kwargs):
    target_topic_description = request.POST.get("topic_description", None)
    topic_terms = list()
    if target_topic_description is not None:
        parent_model_name, topic_index = re.match(r"^([A-Za-z0-9_\-\.]+)_([0-9]+)$", target_topic_description).groups()
        top_10_terms = models.Term.objects.filter(parent_topics__index=topic_index,
                                                  parent_topics__parent_model__name=parent_model_name
                                                  ) \
                           .order_by("-topictermdistribution__value") \
                           .values("string")[:10] \
            .annotate(non_stemmed=ArrayAgg("original_word__string"))
        for term_dict in top_10_terms:
            if term_dict["non_stemmed"] != [None]:
                topic_terms.append(", ".join(term_dict["non_stemmed"][:3]))
            else:
                topic_terms.append(term_dict["string"])
        return JsonResponse({"terms": topic_terms})
    return JsonResponse({"terms": None})


def topic_show(request, *args, **kwargs):
    try:
        topic_index = int(kwargs.get("topic_index"))
    except Exception:
        return Http404
    template_context = dict()
    template_context["topic_index"] = topic_index
    navbar_json = generate_navbar(config.NAV_BAR_ADDRESSES, {})
    template_context["navbar"] = navbar_json

    top_n_terms = models.Term.objects.filter(parent_topics__index=topic_index,
                                             parent_topics__parent_model__name=config.CONFIG_VALUES[
                                                 "MAIN_LDA_MODEL_NAME"]).order_by(
        "-topictermdistribution__value").values("topictermdistribution__value", "string").annotate(
        words=ArrayAgg("original_word__string"))[:config.CONFIG_VALUES["TOP_N_TOPIC_TERMS_TO_PRINT"]]
    result = list()
    for term in top_n_terms:
        if len(term["words"]) > 0:
            result.append({
                "term": ", ".join(term["words"]),
                "value": round(100 * term["topictermdistribution__value"], 2)})

    available_comparisons = models.Comparison.objects.filter(
        lda_model_1__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"]).values("name",
                                                                              "lower_bound",
                                                                              "upper_bound",
                                                                              "type_of_comparison",
                                                                              "description",
                                                                              "lda_model_0__description",
                                                                              "lda_model_1__description",
                                                                              "type_of_comparison")
    evolutions = list()
    for available_comparison in available_comparisons:
        evolution = dict()
        evolution["name"] = available_comparison["name"]
        evolution["description"] = available_comparison["description"]
        evolution["lower_bound"] = float(available_comparison["lower_bound"])
        evolution["upper_bound"] = float(available_comparison["upper_bound"])
        evolution["is_score"] = "true " if available_comparison["type_of_comparison"] == 0 else "false"
        evolution["lda_model_0"] = available_comparison["lda_model_0__description"]
        evolution["lda_model_1"] = available_comparison["lda_model_1__description"]
        evolutions.append(evolution)
    template_context["topic_terms"] = result
    template_context["evolutions"] = evolutions

    relevant_articles_result = models.ArticleTopicDistribution.objects.filter(
        topic__index=topic_index,
        topic__parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"],
        id__in=Subquery(
            models.ArticleTopicDistribution.objects.filter(
                topic__index=topic_index,
                topic__parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"]
            ).order_by(
                "article__identifier", "-value"
            ).distinct(
                "article__identifier"
            ).values(
                "id"
            )
        )
    ).order_by(
        "-value"
    ).values(
        "article__identifier", "article__title"
    )[:config.CONFIG_VALUES["TOP_N_SEARCH_RESULTS"]]
    relevant_articles = [
        {
            "url": os.path.join("/topics", "article-" + result["article__identifier"]),
            "description": result["article__title"]
        }
        for result in relevant_articles_result
    ]
    template_context["relevant_articles"] = relevant_articles
    return render(context=template_context, template_name='p_topic.html', request=request)


def new_article_topic_analysis(request):
    navbar_json = generate_navbar(config.NAV_BAR_ADDRESSES, {"new_article"})
    template_context = dict()
    template_context["navbar"] = navbar_json
    if request.method == "POST":
        new_article_form = NewArticleForm(request.POST)
        if new_article_form.is_valid():
            article_text = new_article_form.cleaned_data["article_text_field"]
            article_additional_info = {
                "article_additional_info": [
                    {
                        "text_row": True,
                        "heading": "Text",
                        "content": article_text
                    }
                ]
            }
            template_context["text_info"] = article_additional_info
            template_context["target_text"] = article_text
    else:
        new_article_form = NewArticleForm()
    template_context["new_article_form"] = new_article_form
    return render(request, template_name='p_new_article.html', context=template_context)


def topic_analysis(request, *args, **kwargs):
    navbar_json = generate_navbar(config.NAV_BAR_ADDRESSES, {})
    template_context = dict()
    template_context["navbar"] = navbar_json
    article_id = kwargs["article_id"]

    article = \
        models.Article.objects.filter(identifier=article_id).values(
            "identifier", "title", "year", "language", "authors", "abstract"
        )
    if len(article) == 0:
        raise Http404
    else:
        template_context["article"] = article[0]

    return render(context=template_context, template_name='p_topic_analysis.html', request=request)


def ajax_text_topics(request):
    if request.method == "POST":
        text = request.POST.get("text", None)
        if text is not None:
            try:
                top_n_article_topics = lda_query.analyze_text(text)
            except lda_query.PreprocessingError as pe:
                result = {
                    "error": {
                        "title": "Preprocessing error",
                        "message": str(pe)
                    }
                }
                return JsonResponse(result)
            result = {
                "result": [{"topic": topic_distribution[0], "value": topic_distribution[1]}
                           for topic_distribution in top_n_article_topics]
            }
            return JsonResponse(result)
        return JsonResponse(status=500)
    raise Http404


def ajax_article_topics(request, article_id=None):
    if request.method == "POST":
        if article_id is not None:
            article_info = models.Article.objects.filter(
                identifier=article_id
            ).values(
                "identifier",
                "abstract",
            ).order_by(
                "-articletopicdistribution__value"
            ).annotate(
                error=F("reportederror__error_description")
            ).annotate(
                topic=F("articletopicdistribution__topic__index")
            ).annotate(
                value=F('articletopicdistribution__value')
            )
            if len(article_info) == 0:
                # No article was found with the given article id
                # This probably is the case when the AJAX call is after a database transaction that deleted the article
                return JsonResponse(data={"error": {"title": "Internal error", "message": "Text is not available"}})
            else:
                if article_info[0]["error"] is None:
                    if article_info[0]["topic"] is not None:
                        return JsonResponse(
                            data={"result": [{"topic": article_topic["topic"], "value": article_topic["value"]}
                                             for article_topic in article_info]}
                        )
                    try:
                        top_n_article_topics = lda_query.analyze_text(article_info[0]["abstract"])
                    except lda_query.PreprocessingError as pe:
                        result = {
                            "error": {
                                "title": "Preprocessing error",
                                "message": str(pe)
                            }
                        }
                        try:
                            models.ReportedError.objects.get_or_create(
                                article=models.Article.objects.get(
                                    identifier=article_id
                                ),
                                defaults={"error_description": str(pe)}
                            )
                        except IntegrityError:
                            # Possible reasons:
                            # 1. Article is getting deleted after it is being fetched by inner get method
                            # 2. An other article error has been entered for the article, after the check
                            #    that the article has an error or not.
                            # TODO: Can we distinct these two cases without actually parsing the
                            #       IntegrityError message
                            pass
                        return JsonResponse(result)
                    try:
                        relative_article = models.Article.objects.get(identifier=article_id)
                        article_topic_distributions = [
                            models.ArticleTopicDistribution(
                                article=relative_article,
                                topic=models.Topic.objects.get(
                                    parent_model__name=config.CONFIG_VALUES["MAIN_LDA_MODEL_NAME"],
                                    index=article_topic[0]),
                                value=article_topic[1])
                            for article_topic in top_n_article_topics]
                        models.ArticleTopicDistribution.objects.bulk_create(article_topic_distributions)
                    except Exception:
                        pass
                    result = {
                        "result": [{"topic": topic_distribution[0], "value": topic_distribution[1]}
                                   for topic_distribution in top_n_article_topics]
                    }
                    return JsonResponse(result)
                else:
                    result = {
                        "error": {"title": "Preprocessing error", "message": article_info[0]["error"]}
                    }
                    return JsonResponse(result)
        return JsonResponse(data={
            "error": {"title": "Missing information", "message": "Request does not contain the article identifier"}},
            status=422)
    raise Http404
