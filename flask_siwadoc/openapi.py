from collections import defaultdict
from typing import Dict, List

from flask import Flask

from . import utils


def generate_spec(openapi_version, title, version, app: Flask, models: Dict) -> Dict:
    """
    生成openapi json
    :param openapi_version:  openapi版本号
    :param title:   文档标题
    :param version:  文档版本
    :param app:  flask app
    :param models:  Pydantic model 字典集合
    :return:
    """
    routes: Dict[str:Dict] = dict()
    tags: Dict[str:Dict] = dict()
    groups: Dict[str:List] = defaultdict(list)
    for rule in app.url_map.iter_rules():
        # 视图函数
        func = app.view_functions[rule.endpoint]

        path, parameters = utils.parse_route_to_path_params(str(rule))
        # 只有被siwadoc装饰了函数才加入openapi
        if not getattr(func, '_decorated', None):
            continue

        for method in rule.methods:
            if method in ['HEAD', 'OPTIONS']:
                continue
            if not hasattr(func, 'tags'):
                func.tags = ['default']
            if not hasattr(func, 'group'):
                func.group = ''

            func_group = getattr(func, 'group', "")
            func_tags = [func_group + "/" + tag for tag in getattr(func, 'tags', ['default'])]

            groups[func_group].extend(func_tags)
            tags.update({tag: {"name": tag} for tag in func_tags})

            summary, description = utils.get_func_doc(func)
            spec = {
                'summary': summary or func.__name__.capitalize(),
                'description': description or '',
                'operationID': func.__name__ + '__' + method.lower(),
                'tags': func_tags,
            }

            if hasattr(func, 'body'):
                spec['requestBody'] = {
                    'content': {
                        'application/json': {
                            'schema': {
                                '$ref': f'#/components/schemas/{func.body}'
                            }
                        }
                    }
                }

            if hasattr(func, 'query'):
                parameters.append({
                    'name': func.query,
                    'in': 'query',
                    'required': False,
                    'schema': {
                        '$ref': f'#/components/schemas/{func.query}',
                    }
                })
            spec['parameters'] = parameters

            spec['responses'] = {}
            has_2xx = False
            if hasattr(func, 'x'):
                for code, msg in func.x.items():
                    if code.startswith('2'):
                        has_2xx = True
                    spec['responses'][code] = {
                        'description': msg,
                    }

            if hasattr(func, 'resp'):
                spec['responses']['200'] = {
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
                spec['responses']['200'] = {'description': 'Successful Response'}

            if any([hasattr(func, schema) for schema in ('query', 'body')]):
                spec['responses']['400'] = {
                    'description': 'Validation Error',
                    'content': {
                        'application/json': {
                            'schema': {
                                "code": 200,
                            }
                        }
                    },
                }
            routes.setdefault(path, {})[method.lower()] = spec

    definitions = {}
    for _, schema in models.items():
        if 'definitions' in schema:
            for key, value in schema['definitions'].items():
                definitions[key] = value
            del schema['definitions']

    data = {
        'openapi': openapi_version,
        'info': {
            'title': title,
            'version': version,
        },
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
