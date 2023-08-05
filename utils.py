import os.path as path


# a way to get the 'parent_root/downloads' directory; alternative for nonexistent global immutable
# since app context does not exist where this is called, using app.config will not work
def downloads_path() -> str:
    return path.dirname(path.abspath(__file__)) + '/downloads/'


# dissects a given full path to a file into its components
def dissect_file_name(file_name: str) -> tuple[str, str, str]:
    split_path = file_name.split('/')
    full_name = split_path[-1].split('.')

    folder = ''.join([x + '/' if x and '.' not in x else '' for x in split_path])
    name = full_name[0] if full_name[0] else ''
    ext = '.' + full_name[1] if full_name[0] else ''

    return folder, name, ext
