from rest_framework.schemas.openapi import AutoSchema


class AntsSchema(AutoSchema):
    def get_tags(self, path, method):
        return ['ants']


class RegionsSchema(AutoSchema):
    def __init__(self):
        super().__init__(tags=['regions'])


class GeneraSchema(AutoSchema):
    def __init__(self):
        super().__init__(tags=['Genera'])
