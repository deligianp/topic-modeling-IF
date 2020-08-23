from django import forms
from django.conf import settings
from django.db import ProgrammingError

from admin_tasks.models import FileGroup, DataProcessingNode
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, ButtonHolder, Submit
from resources import readers


class LdaModelForm(forms.Form):
    name = forms.SlugField(max_length=30, min_length=1, help_text="Name of the LDA model. Use only letters, numbers, "
                                                                  "hyphens or underscores. NOTE: Model's name will be "
                                                                  "normalized by getting decapitalized")
    path = forms.FilePathField(settings.RESOURCES_DIRECTORY, match=settings.LDA_MODEL_NAME_SYNTAX, recursive=True,
                               help_text="Path to the gensim model file inside the RESOURCES folder defined inside the "
                                         "settings.py")
    description = forms.CharField(max_length=50, min_length=1, help_text="A small description for the model",
                                  required=False)
    training_context = forms.CharField(max_length=200, min_length=0, required=False, widget=forms.Textarea(attrs={
        "rows": 10, "cols": 50
    }),
                                       help_text="A description regarding the training parameters (dataset, filtering, "
                                                 "preprocessing, topics)")
    top_N_terms = forms.IntegerField(min_value=50, help_text="Number of terms to be recorded for each topic. NOTE: "
                                                             "While not restricted, a big amount of terms may result "
                                                             "in a very big database that has poor retrieval "
                                                             "efficiency with very little detail gained on the topics' "
                                                             "representations. For this reason the "
                                                             "default and minimum value of 50 terms per topic",
                                     initial=50)
    is_main = forms.BooleanField(required=False, label="Assign this model as the main LDA model")
    preprocessor_name = forms.CharField(max_length=64, min_length=0, required=False,
                                        help_text="The new preprocessor name as defined inside the "
                                                  "resources.preprocessors module. If not defined the \"default\" "
                                                  "preprocessor is used. Ideally the preprocessor used for the "
                                                  "training of the model should be used when performing topic analysis "
                                                  "on custom texts")
    use_tfidf = forms.BooleanField(required=False, label="Use tf-idf vectorization when performing topic analysis on "
                                                         "custom texts")

    def __init__(self, *args, update=False, **kwargs):
        super(LdaModelForm, self).__init__(*args, **kwargs)
        # update = kwargs.get("update", False)
        self.helper = FormHelper()
        self.helper.form_tag = False
        layout = [
            Field("name", autocomplete="off"),
        ]
        if not update:
            layout = [
                Field("name", autocomplete="off"),
                Field("path"),
                Field("description"),
                Field("training_context"),
                Field("top_N_terms"),
                Field("is_main"),
                Field("preprocessor_name"),
                Field("use_tfidf"),
                ButtonHolder(
                    Submit('submit', 'Submit', css_class='btn btn-dark')
                )
            ]
        else:
            layout = [
                Field("name", autocomplete="off"),
                Field("description"),
                Field("training_context"),
                Field("is_main"),
                Field("preprocessor_name"),
                Field("use_tfidf"),
                ButtonHolder(
                    Submit('submit', 'Submit', css_class='btn btn-dark')
                )
            ]
        self.helper.layout = Layout(*layout)


class SFTPWithdrawalForm(forms.Form):
    associated_name = forms.CharField(max_length=50, min_length=1,
                                      help_text="Name that the files share before the extension", required=True)

    files_type = forms.ChoiceField()

    data_node_host = forms.ChoiceField()

    host_password_field = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(SFTPWithdrawalForm, self).__init__(*args, **kwargs)

        self.fields["files_type"].choices = [(file_group.name, file_group.description) for file_group in FileGroup.objects.all()]

        self.fields["data_node_host"].choices = [
            (
                "{}@{}".format(registered_data_node.username, registered_data_node.host),
                "{}@{}".format(registered_data_node.username, registered_data_node.host)
            ) for registered_data_node in DataProcessingNode.objects.all()
        ]

        # update = kwargs.get("update", False)
        self.helper = FormHelper()
        self.helper.form_tag = False
        layout = [
            Field("associated_name", autocomplete="off"),
            Field("files_type", autocomplete="off"),
            Field("data_node_host", autocomplete="off"),
            Field("host_password_field", autocomplete="off"),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='btn btn-dark')
            )
        ]
        self.helper.layout = Layout(*layout)


class FileGroupForm(forms.Form):
    description = forms.CharField(max_length=64, min_length=1,
                                  help_text="A readable name or description for the file group")
    extensions = forms.CharField(max_length=160, min_length=1,
                                 help_text="Extensions to be associated with this file group. Extensions should be "
                                           "defined without the leading \".\" and delimited by SPACE. For example, for "
                                           "the files \"file.json\", \"file.txt\", extensions should be defined as "
                                           "\"json txt\"")

    def __init__(self, *args, **kwargs):
        super(FileGroupForm, self).__init__(*args, **kwargs)
        # update = kwargs.get("update", False)
        self.helper = FormHelper()
        self.helper.form_tag = False
        layout = [
            Field("description", autocomplete="off"),
            Field("extensions", autocomplete="off"),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='btn btn-dark')
            )
        ]
        self.helper.layout = Layout(*layout)


class DataProcessingNodeForm(forms.Form):
    host_address = forms.GenericIPAddressField(protocol="IPv4", help_text="The IPv4 address to the host")

    host_username = forms.CharField(max_length=32, min_length=1,
                                    help_text="The user name to login into the defined host")

    withdrawal_directory = forms.CharField(max_length=512, min_length=1, help_text="Path to the directory where "
                                                                                   "resource files will be retrieved "
                                                                                   "from")

    def __init__(self, *args, **kwargs):
        super(DataProcessingNodeForm, self).__init__(*args, **kwargs)
        # update = kwargs.get("update", False)
        self.helper = FormHelper()
        self.helper.form_tag = False
        layout = [
            Field("host_address", autocomplete="off"),
            Field("host_username", autocomplete="off"),
            Field("withdrawal_directory", autocomplete="off"),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='btn btn-dark')
            )
        ]
        self.helper.layout = Layout(*layout)


class CorpusLoadingForm(forms.Form):
    corpus_files_paths = forms.CharField(
        help_text="Server local file path(s) that point to files that will be used from the selected reader in order "
                  "to retrieve the articles. Different paths should be defined in different lines, by pressing ENTER "
                  "after a path has beed defined",
        widget=forms.Textarea()
    )
    reader_to_use = forms.ChoiceField(
        choices=[(reader_name, reader_name) for reader_name in readers.available_readers], widget=forms.Select,
        help_text="The corpus reader to be used for retrieving the corpus articles"
    )

    def __init__(self, *args, **kwargs):
        super(CorpusLoadingForm, self).__init__(*args, **kwargs)
        # update = kwargs.get("update", False)
        self.helper = FormHelper()
        self.helper.form_tag = False
        layout = [
            Field("corpus_files_paths", autocomplete="off"),
            Field("reader_to_use", autocomplete="off"),
            ButtonHolder(
                Submit('submit', 'Submit', css_class='btn btn-dark')
            )
        ]
        self.helper.layout = Layout(*layout)
