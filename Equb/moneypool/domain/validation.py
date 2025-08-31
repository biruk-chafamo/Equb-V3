
def is_blank_email(email) -> bool:
    return email == '' or email is None


def passwords_match(password, password2) -> bool:
    return password == password2


def is_member(item, collection) -> bool:
    return item in collection


def is_max_members_too_low(max_members) -> bool:
    return max_members < 2


def is_max_members_too_high(max_members) -> bool:
    return max_members > 20


