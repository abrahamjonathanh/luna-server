# encryption_util.py
import logging
import traceback
from datetime import datetime

from cryptography.fernet import Fernet
from django.conf import settings

FERNET_KEY = settings.FERNET_KEY  # dict
APP_ID = settings.APP_NAME # str
EXPIRATION_TIME = 300
SALT = '@@@@'
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class ChiperSetupError(Exception):
    """Does nothing. readability purpose"""


class EncryptError(Exception):
    """Does nothing. readability purpose"""


class DecryptError(Exception):
    """Does nothing. readability purpose"""


def encrypt(plaintext: str) -> str:
    """
    Encrypts the given plaintext into a ciphertext
    """
    # setup, convert to byte
    try:
        plaintext = str(plaintext)
        plainbyte = plaintext.encode()
        encrypt_key_byte = FERNET_KEY.encode()
    except Exception as e:
        raise ChiperSetupError(e) from e

    # ciphering
    try:
        cipher = Fernet(encrypt_key_byte)
        cipherbyte = cipher.encrypt(plainbyte)
        cihpertext = cipherbyte.decode()
    except Exception as e:
        raise EncryptError(e) from e

    return cihpertext


def decrypt(ciphertext: str, decrypt_key: str = FERNET_KEY) -> str:
    """
    Decrypts the given ciphertext into a plaintext
    """
    # setup, convert to byte
    try:
        ciphertext = str(ciphertext)
        cipherbyte = ciphertext.encode()
        decrypt_key_byte = decrypt_key.encode()
    except Exception as e:
        raise ChiperSetupError(e) from e

    # deciphering
    try:
        cipher = Fernet(decrypt_key_byte)
        plainbyte = cipher.decrypt(cipherbyte)
        plaintext = plainbyte.decode()
    except Exception as e:
        raise DecryptError(e) from e

    return plaintext


def encrypt_values_with_salt(*args) -> str:
    """
    Returns a string of ciphertext from args and cipher salt
    args are expected to be string.
    any non-string values will be typecasted to string
    """
    plaintext = SALT.join([str(arg) for arg in args])
    return encrypt(plaintext)


def decrypt_values_with_salt(ciphertext: str) -> tuple:
    """
    Wraps decrypt and split by `SALT` in one function
    """
    plaintext = decrypt(ciphertext)

    return tuple(plaintext.split(SALT))  # tuple consume lest memory compared to list


def is_valid_token(encrypted_token: str) -> bool:
    """
    Validates timestamp & app id from given encrypted token
    """
    (_, datetime_str, app_id) = decrypt_values_with_salt(encrypted_token)
    return is_valid_datetime(datetime_str) and _is_valid_app_id(app_id)


def _is_valid_app_id(app_id: str) -> bool:
    """
    Validates `app_id` to match the one in env variable
    """
    return app_id == APP_ID


def is_valid_datetime(datetime_str: str):
    """
    Validates given `datetime_str` string to match
    today's date and within expiration time set in env variable
    """
    assert isinstance(datetime_str, str)
    is_valid_date = is_same_date(datetime_str)
    is_valid_time = is_within_expiration_time(datetime_str)
    return is_valid_date and is_valid_time


def is_same_date(datetime_str: str) -> bool:
    """
    Validates given `datetime_str` string to match today's date.
    If it fails to parse the date string to date object, it returns False
    """
    # datetime_str YYYY-MM-DD HH:mm:ss
    try:
        now = datetime.now().strftime(DATE_FORMAT)  # YYYY-MM-DD
        date = datetime_str.split(" ")[0]  # YYYY-MM-DD
        return now == date
    except IndexError as split_error:
        print(split_error)
        logging.getLogger("error_logger").error(traceback.format_exc())
        return False
    except Exception as e:
        print(e)
        logging.getLogger("error_logger").error(traceback.format_exc())
        return False


def is_within_expiration_time(datetime_str: str) -> bool:
    """
    Validates given `datetime_str` string to match the
    time difference (usually in seconds) before it "expires".

    Note:
    The expiration here is logic-wise. Not to be confused by
    db-wise expiration
    """
    now = datetime.now().strftime(DATETIME_FORMAT)
    now = datetime.strptime(now, DATETIME_FORMAT)

    to_check = datetime.strptime(datetime_str, DATETIME_FORMAT)

    timedelta = now - to_check if now > to_check else to_check - now

    return int(timedelta.seconds) <= EXPIRATION_TIME