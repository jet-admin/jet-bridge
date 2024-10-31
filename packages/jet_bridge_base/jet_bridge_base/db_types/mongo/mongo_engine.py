from pymongo import MongoClient


class MongoEngine(object):
    client = None

    def connect(self, url):
        self.url = url
        self.client = MongoClient(url)

    def get_db(self, name):
        return self.client[name]

    def dispose(self):
        if self.client:
            self.client.close()
            self.client = None

    def __repr__(self):
        return self.url
