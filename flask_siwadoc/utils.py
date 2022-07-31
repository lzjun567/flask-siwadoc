import inspect
from typing import Type, List, Mapping, Any

from flask.views import View, MethodView
from pydantic import BaseModel
from pydantic.typing import Literal
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


def parse_path_params(route: str) -> (str, List):
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


def parse_other_params(
        location: Literal["query", "header", "cookie"],
        model: Mapping[str, Any],
) -> List[Mapping[str, Any]]:
    params = []
    for name, _schema in model["properties"].items():
        params.append(
            {
                "name": name,
                "in": location,
                "schema": _schema,
                "required": name in model.get("required", []),
                "description": _schema.get("description", ""),
            }
        )
    return params


def get_operation_summary(func) -> str:
    """
    return a summary for operation in the method
    :param func:flask view function
    :return:str
    """
    # print(func)
    return func.summary or func.__qualname__.replace(".", " ").replace("_", " ").title()


def get_operation_description(func) -> str:
    """
    :param func: flask view function
    :return:str
    """
    return func.description or (inspect.getdoc(func) or "").split("\f")[0]


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
