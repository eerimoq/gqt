_EXPERIMENTAL = False

def set_experimental(value):
    global _EXPERIMENTAL
    _EXPERIMENTAL = value

def is_experimental():
    return _EXPERIMENTAL
