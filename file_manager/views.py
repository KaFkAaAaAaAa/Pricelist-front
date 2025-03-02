import os
from django.core.files import File
from django.core.files.storage import FileSystemStorage

from Pricelist.settings import MAX_FILE_SIZE, TRANSACTION_ROOT

fs = FileSystemStorage(location=TRANSACTION_ROOT)


def _sanitize_path(path):
    """Sanitize a path against directory traversal attacks."""
    path = os.path.normpath(os.path.join(fs.base_location, path))
    if not path.startswith(fs.base_location):
        raise ValueError("Invalid file path detected!")
    return path


def _list_transaction_dir(transaction_uuid):
    if transaction_uuid not in fs.listdir("/")[0]:
        return False
    return fs.listdir(os.path.normpath(transaction_uuid))


def _get_file_from_transaction(transaction_uuid, file_name):
    path = _sanitize_path(os.path.join(transaction_uuid, file_name))
    file_list = _list_transaction_dir(transaction_uuid)
    if not file_list:
        return False
    if file_name in file_list[0]:
        return fs.listdir(path)
    elif file_name in file_list[1]:
        with fs.open(path) as f:
            return f.read()
    return False


def _put_file_from_transaction(transaction_uuid, file_name, file_content,
                         overwrite=False):
    transaction_path = os.path.join(fs.base_location, transaction_uuid)
    if not os.path.exists(transaction_path):
        os.makedirs(transaction_path, exist_ok=True)

    path = _sanitize_path(os.path.join(transaction_uuid, file_name))

    if fs.exists(path):
        if not overwrite:
            return False
        fs.delete(path)

    file_content = File(file_content)
    if file_content.size > MAX_FILE_SIZE:
        return False

    return fs.save(path, file_content)
