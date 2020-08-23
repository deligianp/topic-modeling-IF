import paramiko
from stat import S_ISDIR


def discover_subdirectories_dfs(sftp, directory=None):
    current_dir_path = directory or sftp.getcwd()
    # files = sftp.listdir(current_dir_path)
    # is_dir = [S_ISDIR(file_attr.st_mode) for file_attr in sftp.listdir_attr(current_dir_path)]
    # subdirectories = [current_dir_path + "/" + item[0] for item in zip(files, is_dir) if item[1]]
    subdirectories = [
        current_dir_path + "/" + entry.filename for entry in sftp.listdir_attr(current_dir_path) if
        S_ISDIR(entry.st_mode)
    ]
    inner_subdirectories = list()
    for subdirectory in subdirectories:
        inner_subdirectories += discover_subdirectories_dfs(sftp, directory=subdirectory)
    return subdirectories + inner_subdirectories


def discover_subdirectories_bfs(sftp, directory=None):
    current_dir_path = directory or sftp.getcwd()
    candidate_directories = [current_dir_path]
    for candidate_directory in candidate_directories:
        candidate_directories = [
            candidate_directory + "/" + entry.filename for entry in sftp.listdir_attr(candidate_directory) if
            S_ISDIR(entry.st_mode)
        ]
    return candidate_directories[1:]
