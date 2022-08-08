import inspect
import re
from typing import Type, List, Mapping, Any

from pydantic import BaseModel
from pydantic.typing import Literal
from werkzeug.datastructures import MultiDict

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
    解析路径参数
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


_rule_re = re.compile(
    r"""
    (?P<static>[^<]*)                           # static rule data
    <
    (?:
        (?P<converter>[a-zA-Z_][a-zA-Z0-9_]*)   # converter name
        (?:\((?P<args>.*?)\))?                  # converter arguments
        \:                                      # variable delimiter
    )?
    (?P<variable>[a-zA-Z_][a-zA-Z0-9_]*)        # variable name
    >
    """,
    re.VERBOSE,
)


def parse_rule(rule):
    """Parse a rule and return it as generator. Each iteration yields tuples
    in the form ``(converter, arguments, variable)``. If the converter is
    `None` it's a static url part, otherwise it's a dynamic one.

    :internal:
    """
    pos = 0
    end = len(rule)
    do_match = _rule_re.match
    used_names = set()
    while pos < end:
        m = do_match(rule, pos)
        if m is None:
            break
        data = m.groupdict()
        if data["static"]:
            yield None, None, data["static"]
        variable = data["variable"]
        converter = data["converter"] or "default"
        if variable in used_names:
            raise ValueError("variable name %r used twice." % variable)
        used_names.add(variable)
        yield converter, data["args"] or None, variable
        pos = m.end()
    if pos < end:
        remaining = rule[pos:]
        if ">" in remaining or "<" in remaining:
            raise ValueError("malformed url rule: %r" % rule)
        yield None, None, remaining


def parse_converter_args(argstr):
    argstr += ","
    args = []
    kwargs = {}

    for item in _converter_args_re.finditer(argstr):
        value = item.group("stringval")
        if value is None:
            value = item.group("value")
        value = _pythonize(value)
        if not item.group("name"):
            args.append(value)
        else:
            name = item.group("name")
            kwargs[name] = value

    return tuple(args), kwargs


_converter_args_re = re.compile(
    r"""
    ((?P<name>\w+)\s*=\s*)?
    (?P<value>
        True|False|
        \d+.\d+|
        \d+.|
        \d+|
        [\w\d_.]+|
        [urUR]?(?P<stringval>"[^"]*?"|'[^']*')
    )\s*,
    """,
    re.VERBOSE | re.UNICODE,
)

_PYTHON_CONSTANTS = {"None": None, "True": True, "False": False}


def _pythonize(value):
    if value in _PYTHON_CONSTANTS:
        return _PYTHON_CONSTANTS[value]
    for convert in int, float:
        try:
            return convert(value)
        except ValueError:
            pass
    if value[:1] == value[-1:] and value[0] in "\"'":
        value = value[1:-1]
    return str(value)
