BASE62_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'


def base62_encode(byte_data):
    num = int.from_bytes(byte_data, 'big')
    if num == 0:
        return BASE62_ALPHABET[0]
    encoded = ""
    while num > 0:
        num, rem = divmod(num, 62)
        encoded = BASE62_ALPHABET[rem] + encoded
    return encoded


def base62_decode(encoded_str):
    num = 0
    for char in encoded_str:
        num = num * 62 + BASE62_ALPHABET.index(char)
    # Calculate the number of bytes needed
    byte_length = (num.bit_length() + 7) // 8
    return num.to_bytes(byte_length, 'big')


def utf8_to_base62(s):
    return base62_encode(s.encode('utf-8'))


def base62_to_utf8(encoded_str):
    return base62_decode(encoded_str).decode('utf-8')
