# converters
#
# check Werkzeug builtin_converters in
# https://werkzeug.palletsprojects.com/en/0.15.x/routing/#builtin-converters

import typing as t


def convert_any(*args, **kwargs):
    """
    Handle converter type "any"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {
        'type': 'array',
        'items': {
            'type': 'string',
            'enum': args,
        }
    }
    return schema


def int_schema(*args, **kwargs):
    """
    Handle converter type "int"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {
        'type': 'integer',
        'format': 'int32',
    }
    if 'max' in kwargs:
        schema['maximum'] = kwargs['max']
    if 'min' in kwargs:
        schema['minimum'] = kwargs['min']
    return schema


def float_schema(*args, **kwargs):
    """
    Handle converter type "float"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {
        'type': 'number',
        'format': 'float',
    }
    return schema


def uuid_schema(*args, **kwargs):
    """
    Handle converter type "uuid"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {
        'type': 'string',
        'format': 'uuid',
    }
    return schema


def convert_path(*args, **kwargs):
    """
    Handle converter type "path"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {
        'type': 'string',
        'format': 'path',
    }
    return schema


def string_schema(*args, **kwargs):
    """
    Handle converter type "string"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {
        'type': 'string',
    }
    for prop in ['length', 'maxLength', 'minLength', 'maxlength']:
        if prop in kwargs:
            schema["minLength"] = kwargs[prop]
    return schema


def convert_default(*args, **kwargs):
    """
    Handle converter type "default"
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    schema = {'type': 'string'}
    return schema


class BaseSchema:
    def __init__(self, _type: str, _format: str = None, *args: t.Any, **kwargs: t.Any) -> None:
        self.type = _type
        self.format = _format or _type

    def schema_json(self):
        return self.__dict__


class StringSchema(BaseSchema):
    def __init__(self, _format: str = None, *args: t.Any, **kwargs: t.Any):
        if 'length' in kwargs:
            self.maxLength = kwargs['length']
            self.minLength = kwargs['length']
        if 'maxlength' in kwargs:
            self.maxLength = kwargs['maxlength']
        if 'minlength' in kwargs:
            self.minLength = kwargs['minlength']
        super().__init__("string", _format)


class NumberSchema(BaseSchema):
    def __init__(self, _type, _format, *args: t.Any, **kwargs: t.Any):
        if 'max' in kwargs:
            self.maximum = kwargs['max']
        if 'min' in kwargs:
            self.minimum = kwargs['min']
        assert _type in ("integer", "number")
        super().__init__(_type, _format=_format)


class IntegerSchema(NumberSchema):
    def __init__(self, *args: t.Any, **kwargs: t.Any):
        super().__init__("integer", _format="int64", *args, **kwargs)


class FloatSchema(NumberSchema):
    def __init__(self, *args: t.Any, **kwargs: t.Any):
        super().__init__("number", _format="number", *args, **kwargs)


class UUIDSchema(StringSchema):
    def __init__(self, *args: t.Any, **kwargs: t.Any):
        super().__init__(_format="uuid", *args, **kwargs)


class PathSchema(StringSchema):
    def __init__(self, *args: t.Any, **kwargs: t.Any):
        super().__init__(_format="path", *args, **kwargs)


class AnySchema(StringSchema):
    def __init__(self, *args: t.Any, **kwargs: t.Any):
        self.enum = args
        super().__init__(_format="enum", **kwargs)


SCHEMAS: t.Mapping[str, t.Type[BaseSchema]] = {
    'any': AnySchema,
    'int': IntegerSchema,
    'float': FloatSchema,
    'uuid': UUIDSchema,
    'path': PathSchema,
    'string': StringSchema,
    'default': StringSchema
}


def get_converter(converter: str, *args, **kwargs):
    """
    Get conveter method from converter map
    :param converter: str: converter type
    :param args:
    :param kwargs:
    :return: return schema dict
    """
    return SCHEMAS[converter](*args, **kwargs)
