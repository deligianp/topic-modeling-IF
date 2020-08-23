# import resources.util.errors
# import os
#
# CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
# CORPUS_PATH = os.path.join(CURRENT_DIR, 'corpus')
# CORPUS_ERRORS_PATH = os.path.join(CURRENT_DIR, 'corpus_errors')
# MODELS_PATH = os.path.join(CURRENT_DIR, 'lda_models')
# MODELS_CONFIG_FILE_DELIMITER = '|'
#
#
# def discover_models():
#     target_config_file = os.path.join(MODELS_PATH, 'models.desc')
#     if os.path.exists(target_config_file):
#         config_file_handle = open(target_config_file, 'r', encoding='utf-8')
#         available_models = list()
#         for line in config_file_handle:
#             available_models.append(line.strip().split(MODELS_CONFIG_FILE_DELIMITER))
#         return available_models
#     else:
#         raise resources.util.errors.PathError(0,
#                                               'The lda_models path defined within the __init__.py file does not exist or is not accessible.',
#                                               'Path given: {}'.format(target_config_file))
