class CaseInsensitiveSlugConverter:
    regex = "\\w+-\\w+"

    def to_python(self, value):
        return value.lower()

    def to_url(self, value):
        return value
