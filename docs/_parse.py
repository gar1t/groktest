from groktest import parse_type


@parse_type("greeting", r"(hello|hi|hola)")
def parse_greeting(s: str):
    return s


@parse_type("uint", r"\d+")
def parse_uint(s: str):
    return int(s)
