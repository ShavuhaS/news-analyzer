import re

endsent_tag_regex = re.compile(r"([^\.])\s*<[^/]*>")
tag_regex = re.compile(r"<[^>]*>")
multispace_regex = re.compile(r"\s+")

def html_sanitize(s: str) -> str:
    s = endsent_tag_regex.sub(r"\1. ", s)
    s = tag_regex.sub(' ', s)
    s = multispace_regex.sub(' ', s)
    return s.strip()