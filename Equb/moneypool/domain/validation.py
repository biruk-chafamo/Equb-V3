
def is_blank_email(email) -> bool:
    return email == '' or email is None


def passwords_match(password, password2) -> bool:
    return password == password2


