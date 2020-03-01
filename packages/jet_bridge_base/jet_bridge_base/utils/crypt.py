import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


backend = default_backend()


def decrypt(message_encrypted, secret_key):
    message_salt = message_encrypted[-24:]
    message_payload = message_encrypted[:-24]
    salt = base64.b64decode(message_salt)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=backend
    )
    key = base64.urlsafe_b64encode(kdf.derive(bytes(secret_key, encoding='utf8')))
    f = Fernet(key)
    return f.decrypt(bytes(message_payload, encoding='latin1')).decode('utf8')
