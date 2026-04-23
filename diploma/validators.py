import re
import hashlib
import urllib.request
from django.core.exceptions import ValidationError

class ComplexityValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Пароль повинен містити хоча б одну велику літеру.", code='password_no_upper')
        if not re.search(r'[a-z]', password):
            raise ValidationError("Пароль повинен містити хоча б одну малу літеру.", code='password_no_lower')
        if not re.search(r'\d', password):
            raise ValidationError("Пароль повинен містити хоча б одну цифру.", code='password_no_number')
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError("Пароль повинен містити хоча б один спеціальний символ (наприклад, @, #, $, %).", code='password_no_symbol')

    def get_help_text(self):
        return "Пароль повинен містити великі та малі літери, цифри та спеціальні символи."

class PwnedPasswordValidator:
    def validate(self, password, user=None):
        # Хешуємо пароль (ми відправляємо лише перші 5 символів хешу, сам пароль ніхто не дізнається)
        sha1_password = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1_password[:5], sha1_password[5:]
        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Glibyna-4.0-Security'})
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    hashes = (line.decode('utf-8').split(':') for line in response)
                    for h, count in hashes:
                        if h == suffix:
                            raise ValidationError(f"Цей пароль був знайдений у витоках даних {count} разів. З міркувань безпеки виберіть інший.", code='password_is_pwned')
        except ValidationError:
            raise
        except Exception:
            # Fail-Open: Якщо сервіс лежить чи заблокований, пропускаємо перевірку
            pass

    def get_help_text(self):
        return "Пароль перевіряється на наявність у відомих витоках даних."