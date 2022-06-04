import inspect
from typing import Type, Tuple, List

from pydantic import BaseModel
from werkzeug.datastructures import MultiDict
from werkzeug.routing import parse_rule, parse_converter_args

from . import schema


def convert_query_params(query_prams: MultiDict, model: Type[BaseModel]) -> dict:
    """
    :param query_prams: flask request.args
    :param model: query parameter's model
    :return resulting parameters
    """
    return {
        **query_prams.to_dict(),
        **{key: value for key, value in query_prams.to_dict(flat=False).items() if
           key in model.__fields__ and model.__fields__[key].is_complex()}
    }


def parse_route_to_path_params(route: str) -> (str, List):
    """
    将flask route url 转换成 openapi的path规范
    :param route: /hello/<int(min=2):age>
    :return
    path: /hello/{age}
    parameters: [{
                        "in": "path",
                        "name": "age",
                        "required": true,
                        "schema": {
                            "format": "int64",
                            "type": "integer"
                        }
                }],
    """
    subs = []
    parameters = []

    # /hello/<int(min=2):age>
    # 会转成两个元素
    # 0:None, None, hello
    # 1:int, min=2, age

    for converter, arguments, variable in parse_rule(route):
        if converter is None:
            subs.append(variable)
            continue
        subs.append(f'{{{variable}}}')

        args, kwargs = [], {}

        if arguments:
            args, kwargs = parse_converter_args(arguments)

        path_param_schema = get_path_param_schema(converter, *args, **kwargs).schema_json()

        parameters.append({
            'name': variable,
            'in': 'path',
            'required': True,
            'schema': path_param_schema,
        })
    path = ''.join(subs)
    return path, parameters


def get_func_doc(func) -> (str, str):
    """
    获取视图函数的文档注释，summary与description之间用 \n\n 分隔
    :param func: flask 视图函数
    :return: (summary,description)
    """
    doc = inspect.getdoc(func)
    if not doc:
        return None, None

    doc = doc.split('\n\n', 1)
    if len(doc) == 1:
        return doc[0], None
    return doc


def get_path_param_schema(converter: str, *args, **kwargs) -> schema.BaseSchema:
    """
    获取路径参数对应的schema
    将werkzeug的转换器转换成openapi所需的schema

    例如路由：Rule('/<string(length=10):lang_code>')
    转换成schema
    "schema": {
              "format": "string",
              "maxLength": 10,
              "minLength": 10,
              "type": "string"
            }
    :param converter: str: converter type  'any'|'int'|'float'|'uuid'|'path'|'string'|'default'
    :param args:
    :param kwargs:
    """
    return schema.SCHEMAS[converter](*args, **kwargs)
