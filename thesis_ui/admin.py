from django.contrib import admin, messages
from django import forms
from resources.configuration import CONFIG_VALUES

from .models import Article, ArticleTopicDistribution, ReportedError, LdaModel, Comparison, Topic, TopicsComparison, \
    TopicTermDistribution, Term, Word
import numpy as np

# Register your models here.


admin.site.register(Article)
admin.site.register(ReportedError)
# admin.site.register(Topic)
# admin.site.register(TopicsComparison)
admin.site.register(ArticleTopicDistribution)
# admin.site.register(TopicTermDistribution)
# admin.site.register(Term)


@admin.register(LdaModel)
class LdaModelAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)  # Saves the model. The LDA model is inside
        if not change:

            TOP_N_TOPIC_TERMS = CONFIG_VALUES["TOP_N_TOPIC_TERMS"]

            path = obj.path

            from gensim.models import LdaModel
            lda_model = LdaModel.load(path)
            is_main = obj.is_main
            topic_terms = lda_model.get_topics()

            id2word = lda_model.id2word

            # Step 1: Save dictionary
            terms_index_list = [Term.objects.get_or_create(string=id2word[term_id])[0] for term_id in id2word]
            num_topics = topic_terms.shape[0]
            num_terms = topic_terms.shape[1]
            topics_index_list = [Topic(index=topic_index, parent_model=obj) for topic_index in range(num_topics)]
            Topic.objects.bulk_create(topics_index_list)
            sorted_indexes = np.flip(np.argsort(topic_terms, axis=1), axis=1)[:, :TOP_N_TOPIC_TERMS]
            topic_term_distributions = list()
            for topic_index in range(num_topics):
                # Step 2: Save topic
                for term_index in sorted_indexes[topic_index]:
                    topic_term_distributions.append(
                        TopicTermDistribution(topic=topics_index_list[topic_index], term=terms_index_list[term_index],
                                              value=topic_terms[topic_index][term_index]))
            TopicTermDistribution.objects.bulk_create(topic_term_distributions)


class ComparisonModelForm(forms.ModelForm):
    comparison_measurement_file = forms.FilePathField(path=CONFIG_VALUES["RESOURCES_PATH"], recursive=True,
                                                      match=CONFIG_VALUES["COMPARISON_FILE_EXTENSION"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.m0_topics_index = None
        self.m1_topics_index = None
        self.comparison_matrix = None

    # def save(self, commit=True):
    #     print("You entered \"{}\"".format(self.cleaned_data.get('comparison_measurement_file', None)))
    #     return super(ComparisonModelForm, self).save(commit=commit)

    # def clean_comparison_measurement_file(self):
    #     self.comparison_measurement_file.
    #     comparison_measurement_file = self.cleaned_data.get("comparison_measurement_file")
    #     if self.on_change:
    #         return None
    #     else:
    #         raise forms.ValidationError("Bruh")

    def clean(self):
        cleaned_data = super().clean()
        m0_reference = cleaned_data.get("lda_model_0")
        m1_reference = cleaned_data.get("lda_model_1")
        if m0_reference is not None and m1_reference is not None:
            if m0_reference == m1_reference:
                raise forms.ValidationError("\"Lda model 0\" and \"Lda model 1\" must be different", code="different")

            m0_topics_index = Topic.objects.filter(parent_model=m0_reference).order_by("index")
            m1_topics_index = Topic.objects.filter(parent_model=m1_reference).order_by("index")

            comparison_file_path = cleaned_data.get('comparison_measurement_file', None)

            import bz2
            import pickle
            with bz2.BZ2File(comparison_file_path, "rb") as fhandle:
                upickler = pickle.Unpickler(fhandle)

                comparison_matrix = upickler.load()

                fhandle.close()

            if len(comparison_matrix) != len(m0_topics_index):
                raise forms.ValidationError(
                    "Comparison file measurements can't be mapped for model 0. Model 0 topics: {}, comparison model 0 "
                    "topics: {}".format(len(m0_topics_index), len(comparison_matrix)))
            if len(comparison_matrix[0]) != len(m1_topics_index):
                raise forms.ValidationError(
                    "Comparison file measurements can't be mapped for model 1. Model 1 topics: {}, comparison model 1 "
                    "topics: {}".format(len(m1_topics_index), len(comparison_matrix[0])))
            self.m0_topics_index = m0_topics_index
            self.m1_topics_index = m1_topics_index
            self.comparison_matrix = comparison_matrix
        return cleaned_data

    class Meta:
        model = Comparison
        fields = ["name", "description", "type_of_comparison", "lower_bound", "upper_bound", "lda_model_0",
                  "lda_model_1"]


@admin.register(Comparison)
class ComparisonAdmin(admin.ModelAdmin):
    form = ComparisonModelForm

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # self.exclude = ("lda_model_0",)
        self.fields = ["name", "description", "type_of_comparison", "lower_bound", "upper_bound"]
        return super().change_view(request, object_id, form_url, extra_context)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("comparison_measurement_file",)
        return self.readonly_fields

    def get_form(self, request, obj=None, change=False, **kwargs):
        self.fields = ["name", "description", "type_of_comparison", "lower_bound", "upper_bound"]
        if not change:
            self.fields.extend(["comparison_measurement_file", "lda_model_0", "lda_model_1"])
        else:
            self.exclude = ("comparison_measurement_file",)
        form = super().get_form(request, obj, change, **kwargs)
        # if change:
        #     form.comparison_measurement_file.required = False
        return form

    # def get_fields(self, request, obj=None):
    #     return ["name", "description", "type_of_comparison", "lower_bound", "upper_bound"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            topics_comparisons = list()
            for topic_index_0 in range(len(form.m0_topics_index)):
                for topic_index_1 in range(len(form.m1_topics_index)):
                    topics_comparisons.append(TopicsComparison(topic_0=form.m0_topics_index[topic_index_0],
                                                               topic_1=form.m1_topics_index[topic_index_1],
                                                               parent_comparison=obj,
                                                               value=form.comparison_matrix[topic_index_0][
                                                                   topic_index_1]))
            TopicsComparison.objects.bulk_create(topics_comparisons)


# @admin.register(TopicTermDistribution)
# class TopicTermDistributionAdmin(admin.ModelAdmin):
#     actions = None
#     enable_change_view = False
#
#     def get_list_display_links(self, request, list_display):
#         if self.list_display_links or list_display:
#             return self.list_display_links
#         else:
#             return (None,)
#
#     def change_view(self, request, object_id, form_url='', extra_context=None):
#         """
#         The 'change' admin view for this model.
#
#         We override this to redirect back to the changelist unless the view is
#         specifically enabled by the "enable_change_view" property.
#         """
#         if self.enable_change_view:
#             return super().change_view(
#                 request,
#                 object_id,
#                 form_url,
#                 extra_context
#             )
#         else:
#             from django.urls import reverse
#             from django.http import HttpResponseRedirect
#
#             opts = self.model._meta
#             url = reverse('admin:{app}_{model}_changelist'.format(
#                 app=opts.app_label,
#                 model=opts.model_name,
#             ))
#             return HttpResponseRedirect(url)
#
#     def has_add_permission(self, request):
#         return False
#
#     def has_delete_permission(self, request, obj=None):
#         return False


class WordForm(forms.ModelForm):
    load_from = forms.FilePathField(path=CONFIG_VALUES["RESOURCES_PATH"], recursive=True,
                                    match=CONFIG_VALUES["NSTEMMED_DICTIONARY_FILE_EXTENSION"])

    def clean(self):
        clean_data = super().clean()

        dictionary_path = clean_data["load_from"]
        import bz2
        import pickle
        with bz2.BZ2File(dictionary_path, "rb") as fhandle:
            upickler = pickle.Unpickler(fhandle)
            clean_data["load_from"] = upickler.load()
            fhandle.close()
        return clean_data


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    # can create (hopefully change name of create link, erase past data and paste new)
    # can delete all as action on the link list
    # cannot change, redirect back to link list view

    form = WordForm

    actions = ["truncate"]
    enable_change_view = False

    @staticmethod
    def truncate(*args, **kwargs):
        Word.truncate()
    truncate.short_description = "Truncate all words"

    def save_model(self, request, obj, form, change):
        # Get all terms currently in database
        all_terms_qs = Term.objects.all()
        word_load_queue = list()
        for term in all_terms_qs:
            if term.string in form.cleaned_data["load_from"]:
                term_entries = [
                    Word(string=form.cleaned_data["load_from"][term.string][word_rank], rank=word_rank + 1,
                         stemmed=term)
                    for word_rank in range(min(len(form.cleaned_data["load_from"][term.string]), 3))]  # TODO: config
                word_load_queue += term_entries
        # Delete existing mappings
        Word.truncate()

        # Save new mappings
        Word.objects.bulk_create(word_load_queue)

    def get_form(self, request, obj=None, change=False, **kwargs):
        self.fields = ("load_from",)
        self.exclude = ("string", "rank", "stemmed")
        return super().get_form(request, obj, change, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        self.readonly_fields += ("string", "rank", "stemmed")
        return self.readonly_fields

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """
        The 'change' admin view for this model.

        We override this to redirect back to the changelist unless the view is
        specifically enabled by the "enable_change_view" property.
        """
        if self.enable_change_view:
            return super().change_view(
                request,
                object_id,
                form_url,
                extra_context
            )
        else:
            from django.urls import reverse
            from django.http import HttpResponseRedirect

            opts = self.model._meta
            url = reverse('admin:{app}_{model}_changelist'.format(
                app=opts.app_label,
                model=opts.model_name,
            ))
            return HttpResponseRedirect(url)
