from django import forms


class SearchForm(forms.Form):
    search_field = forms.CharField(widget=forms.TextInput(
        attrs={
            "class": "form-control",
            "placeholder": "Search for articles",
            "autocomplete": "off"
        }
    ))
    search_context_choices = (("articles", "Articles"), ("topics", "Topics"))
    search_context = forms.ChoiceField(choices=search_context_choices, widget=forms.RadioSelect(attrs={
        "class": "form-check-input"
    }), initial="articles")


class NewArticleForm(forms.Form):
    article_text_field = forms.CharField(widget=forms.Textarea(
        attrs={
            "class": "form-control",
            "placeholder": "Text to analyze to topics",
            "autocomplete": "off",
            "style": "resize:none"
        }
    ))