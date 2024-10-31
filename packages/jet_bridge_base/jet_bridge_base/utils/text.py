import re


def clean_alphanumeric(str):
    return re.sub('[^0-9a-zA-Z.]+', '-', str)
