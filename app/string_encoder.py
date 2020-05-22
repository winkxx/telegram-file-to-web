import base64
import Crypto.Cipher.ARC4


class StringCoder:
    @staticmethod
    def decode(text, key='438yf9wedi%$^sbj3'):
        crypto_obj = Crypto.Cipher.ARC4.new(key=key.encode())
        decoded_byte = base64.urlsafe_b64decode(text)
        plain = crypto_obj.decrypt(decoded_byte).decode()
        return plain

    @staticmethod
    def encode(text, key='438yf9wedi%$^sbj3'):
        crypto_obj = Crypto.Cipher.ARC4.new(key=key.encode())
        encrypted_byte = crypto_obj.encrypt(text.encode())
        return base64.urlsafe_b64encode(encrypted_byte).decode()
