import base64
import gzip


def decompress_data(value):
    try:
        bytes = base64.b64decode(value)
        data = gzip.decompress(bytes)
        return data.decode('utf-8')
    except AttributeError:
        return value.decode('zlib')


def compress_data(data):
    try:
        encoded = data.encode('utf-8')
        bytes = gzip.compress(encoded)
        return str(base64.b64encode(bytes), 'utf-8')
    except AttributeError:
        return data.encode('zlib')
