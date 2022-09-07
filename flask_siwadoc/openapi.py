import copy
from collections import defaultdict
from typing import Dict, List, Any

from flask import Flask

from . import utils


def generate_openapi(title: str,
                     version: str,
                     openapi_version: str,
                     app: Flask,
                     models: Dict[str, Dict],
                     description: str = None) -> Dict[str, Any]:
    """
    :param title:
    :param version:
    :param openapi_version:
    :param app:
    :param models:
    :param description:
    """

    routes: Dict[str:Dict] = dict()
    tags: Dict[str:Dict] = dict()
    groups: Dict[str:List] = defaultdict(list)
    for rule in app.url_map.iter_rules():
        # 视图函数
        func = old_func = app.view_functions[rule.endpoint]
        path, parameters = utils.parse_path_params(str(rule))
        methods = rule.methods
        for method in methods:
            if method in ['HEAD', 'OPTIONS']:
                continue
            if getattr(old_func, "view_class", None):
                cls = getattr(old_func, "view_class")
                func = getattr(cls, method.lower(), None)
            # 只有被siwadoc装饰了函数才加入openapi
            if not getattr(func, '_decorated', None):
                continue
            if not hasattr(func, 'tags'):
                func.tags = ['default']
            if not hasattr(func, 'group'):
                func.group = ''

            func_group = getattr(func, 'group', "")
            func_tags = [tag if tag != 'default' else func_group + "/" + tag for tag in
                         getattr(func, 'tags', ['default'])]

            groups[func_group].extend(func_tags)
            tags.update({tag: {"name": tag} for tag in func_tags})
            operation = {
                'summary': utils.get_operation_summary(func),
                'description': utils.get_operation_description(func),
                'operationID': func.__name__ + '__' + method.lower(),
                'tags': func_tags,
            }

            if hasattr(func, 'body'):
                operation['requestBody'] = {
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': f'#/components/schemas/{func.body}'
                            }
                        }
                    }
                }
            parameters = copy.deepcopy(parameters)
            if hasattr(func, 'query'):
                parameters.extend(utils.parse_other_params('query', models[func.query]))
            if hasattr(func, 'header'):
                parameters.extend(utils.parse_other_params('header', models[func.header]))
            if hasattr(func, 'cookie'):
                parameters.extend(utils.parse_other_params('cookie', models[func.cookie]))
            operation['parameters'] = parameters

            operation['responses'] = {}
            has_2xx = False
            if hasattr(func, 'x'):
                for code, msg in func.x.items():
                    if code.startswith('2'):
                        has_2xx = True
                    operation['responses'][code] = {
                        'description': msg,
                    }

            if hasattr(func, 'resp'):
                operation['responses']['200'] = {
                    'description': 'Successful Response',
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': f'#/components/schemas/{func.resp}'
                            }
                        }
                    },
                }
            elif not has_2xx:
                operation['responses']['200'] = {'description': 'Successful Response'}

            if any([hasattr(func, schema) for schema in ('query', 'body')]):
                operation['responses']['400'] = {
                    'description': 'Validation Error',
                    'content': {
                        'application/json': {
                            'schema': {
                                "code": 200,
                            }
                        }
                    },
                }
            routes.setdefault(path, {})[method.lower()] = operation

    definitions = {}
    for _, schema in models.items():
        if 'definitions' in schema:
            for key, value in schema['definitions'].items():
                definitions[key] = value
            del schema['definitions']
    info = {
        'title': title,
        'version': version,
    }
    if description:
        info["description"] = description
    data = {
        'openapi': openapi_version,
        'info': info,
        'tags': list(tags.values()),
        'x-tagGroups': [{"name": k, "tags": list(set(v))} for k, v in groups.items()],
        'paths': {
            **routes
        },
        'components': {
            'schemas': {
                name: schema for name, schema in models.items()
            },
        },
        'definitions': definitions
    }
    return data
