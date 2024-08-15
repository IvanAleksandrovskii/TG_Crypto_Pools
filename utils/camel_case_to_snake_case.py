"""
Needed to convert camel case to snake case. Makes it easier to create tables,
class name automatically becomes the easy-to-read table name
"""


def camel_case_to_snake_case(camel_case_string):
    chars = []
    for c_idx, char in enumerate(camel_case_string):
        if c_idx and char.isupper():
            nxt_idx = c_idx + 1
            flag = nxt_idx >= len(camel_case_string) or camel_case_string[nxt_idx].isupper()
            prev_char = camel_case_string[c_idx - 1]
            if prev_char.isupper() and flag:
                pass
            else:
                chars.append("_")
        chars.append(char.lower())

    return "".join(chars)
