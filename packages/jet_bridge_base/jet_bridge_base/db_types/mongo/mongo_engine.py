from pymongo import MongoClient
from bson.codec_options import TypeDecoder, TypeRegistry
from bson.datetime_ms import DatetimeMS


class DatetimeMSDecoder(TypeDecoder):
    bson_type = DatetimeMS

    def transform_bson(self, value):
        return None


class MongoEngine(object):
    client = None

    def connect(self, url):
        self.url = url
        self.client = MongoClient(
            url,
            datetime_conversion='DATETIME_AUTO',
            type_registry=TypeRegistry([DatetimeMSDecoder()]),
        )

    def get_db(self, name):
        return self.client[name]

    def dispose(self):
        if self.client:
            self.client.close()
            self.client = None

    def __repr__(self):
        return self.url
