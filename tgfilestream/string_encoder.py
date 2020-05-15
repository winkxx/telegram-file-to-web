import base64
import os

if os.name != 'nt':
    import Crypto.Cipher.ARC4


class StringCoder:
    @staticmethod
    def decode(text, key='438yf9wedi%$^sbj3'):
        if os.name == 'nt':
            dec = []
            enc = base64.urlsafe_b64decode(text).decode()
            for i in range(len(enc)):
                key_c = key[i % len(key)]
                dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
                dec.append(dec_c)
            return "".join(dec)
        else:
            crypto_obj = Crypto.Cipher.ARC4.new(key=key)
            decoded_byte = base64.urlsafe_b64decode(text)
            plain = crypto_obj.decrypt(decoded_byte).decode()
            return plain

    @staticmethod
    def encode(text, key='438yf9wedi%$^sbj3'):
        if os.name == 'nt':
            enc = []
            for i in range(len(text)):
                key_c = key[i % len(key)]
                enc_c = chr((ord(text[i]) + ord(key_c)) % 256)
                enc.append(enc_c)
            return base64.urlsafe_b64encode("".join(enc).encode()).decode()
        else:
            crypto_obj = Crypto.Cipher.ARC4.new(key=key)
            encrypted_byte = crypto_obj.encrypt(text)
            return base64.urlsafe_b64encode(encrypted_byte).decode()
