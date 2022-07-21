import os
from functools import wraps
from typing import Optional, Type, Dict

import pydantic
from flask import Blueprint, request, Flask, render_template
from flask import jsonify
from pydantic import BaseModel

from . import utils, openapi, error
from .config import config
from .error import ValidationError

__all__ = ["SiwaDoc", "ValidationError"]

__version__ = "0.1.2"


class SiwaDoc:
    def __init__(self, app: Flask = None):
        self.app = app
        self._spec = None
        self.config = None
        self.models: Dict[str: Dict] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self.app = app
        self.config = config
        self._register_doc_blueprint()

    def _register_doc_blueprint(self):
        """
        注册文档蓝图
        """
        template_folder = os.path.join(os.path.dirname(__file__), "templates")
        blueprint = Blueprint(self.config.name,
                              __name__,
                              url_prefix=self.config.url_prefix,
                              template_folder=template_folder,
                              )

        # /docs
        @blueprint.route(self.config.endpoint)
        def doc_html():
            ui = request.args.get("ui")
            if not ui or ui not in self.config._support_ui:
                ui = self.config.ui
            ui_file = f'{ui}.html'
            return render_template(ui_file, spec_url=self.config.filename)

        # /docs/openapi.json
        @blueprint.route(f'{self.config.endpoint}{self.config.filename}')
        def doc_json():
            return jsonify(self.spec)

        self.app.register_blueprint(blueprint)

    @property
    def spec(self):
        if not self._spec:
            self._spec = self._generate_spec()
        return self._spec

    def _generate_spec(self) -> Dict:
        """
        生成openapi规范文档
        """
        data = openapi.generate_spec(openapi_version=self.config.openapi_veresion,
                                     title=self.config.title,
                                     version=self.config.version,
                                     app=self.app,
                                     models=self.models)
        self._spec = data
        return data

    def doc(self,
            query: Optional[Type[BaseModel]] = None,
            header: Optional[Type[BaseModel]] = None,
            cookie: Optional[Type[BaseModel]] = None,
            body: Optional[Type[BaseModel]] = None,
            resp=None,
            x=[],
            tags=[],
            group=None,
            summary=None,
            description=None,
            ):
        """
        装饰器同时兼具文档生成和请求数据校验功能
        """

        def decorate_validate(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                query_data, body_data = None, None
                # 注解参数
                query_in_kwargs = func.__annotations__.get("query")
                body_in_kwargs = func.__annotations__.get("body")
                query_model = query_in_kwargs or query
                body_model = body_in_kwargs or body

                if query_model:
                    query_params = utils.convert_query_params(request.args, query_model)
                    try:
                        query_data = query_model(**query_params)
                    except pydantic.error_wrappers.ValidationError as e:
                        raise ValidationError(e)

                if body_model is not None:
                    try:
                        body_data = body_model(**(request.get_json(silent=True) or {}))
                    except pydantic.error_wrappers.ValidationError as e:
                        raise ValidationError(e)
                if query_in_kwargs:
                    kwargs["query"] = query_data
                if body_in_kwargs:
                    kwargs["body"] = body_data

                return func(*args, **kwargs)

            for model, name in zip(
                    (query, header, cookie, body, resp), ('query', 'header', 'cookie', 'body', 'resp')
            ):
                if model:
                    assert issubclass(model, BaseModel)
                    self.models[model.__name__] = model.schema()
                    setattr(wrapper, name, model.__name__)

            code_msg = {}
            if code_msg:
                wrapper.x = code_msg

            if tags:
                wrapper.tags = tags
            if group:
                wrapper.group = group
            wrapper.summary = summary
            wrapper.description = description
            wrapper._decorated = True  # 标记判断改函数是否加入openapi
            return wrapper

        return decorate_validate
