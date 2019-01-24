import os

from jet_bridge import settings


class MediaCache(object):
    max_cache_size = 1024 * 1024 * 50
    files = []
    size = 0

    def __init__(self):
        self.cache_path = os.path.join(settings.MEDIA_ROOT, '_jet_cache')
        self.update_files()

    def get_files(self):
        files = []
        for dirpath, dirnames, filenames in os.walk(self.cache_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                files.append({
                    'path': fp,
                    'size': os.path.getsize(fp)
                })
        self.sort_files(files)
        return files

    def sort_files(self, files):
        files.sort(key=lambda x: os.path.getmtime(x['path']))

    def get_files_size(self, files):
        total_size = 0
        for file in files:
            total_size += file['size']
        return total_size

    def update_files(self):
        self.files = self.get_files()
        self.size = self.get_files_size(self.files)

    def add_file(self, path):
        size = os.path.getsize(path)

        self.files.append({
            'path': path,
            'size': size
        })
        self.size += size
        self.sort_files(self.files)

    def clear_cache_if_needed(self):
        while self.size > self.max_cache_size:
            os.remove(self.files[0]['path'])
            self.size -= self.files[0]['size']
            self.files.remove(self.files[0])

    def full_path(self, path):
        return os.path.join(self.cache_path, path)

cache = MediaCache()
