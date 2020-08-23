import os

CONFIG_VALUES = {
    "HOST_DOMAIN_ROOT": "83.212.72.179",
    "TOP_N_TOPIC_TERMS": 1000,
    "RESOURCES_PATH": "/home/mosquito/site-resources/",
    "LDA_MODEL_FILE_EXTENSION": r"^.+\.lda$",
    "COMPARISON_FILE_EXTENSION": r"^.+\.comparison$",
    "NSTEMMED_DICTIONARY_FILE_EXTENSION": r"^.+\.dict$",
    "TOP_N_TOPIC_TERMS_TO_PRINT": 50,
    "TOP_N_SEARCH_RESULTS": 50,
    "TOP_N_DOCUMENT_TOPICS": 3,
    "MAIN_LDA_MODEL_NAME": "dblp_750_200_05_20_0"
}

NAV_BAR_ADDRESSES = [
    {
        "home": {
            "label": "Home",
            "url": "/"
        }
    },
    {
        "topics": {
            "label": "Topics",
            "url": "#",
            "children": [
                {
                    "search_articles": {
                        "label": "Topics of existing articles",
                        "url": "/search-articles"
                    }
                },
                {
                    "new_article": {
                        "label": "Topics of new article",
                        "url": "/new-article"
                    }
                }
            ]
        }
    }
]
