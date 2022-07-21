import os
from functools import wraps
from typing import Optional, Type, Dict, Union, Any

import pydantic
from flask import Blueprint, request, Flask, render_template
from flask import jsonify
from pydantic import BaseModel
from pydantic.typing import Literal
from . import utils, openapi, error
from .config import config
from .error import ValidationError

__all__ = ["SiwaDoc", "ValidationError"]

__version__ = "0.1.2"

SUPPORTED_UI = ('redoc', 'swagger', 'rapidoc')


class SiwaDoc:
    def __init__(self,
                 app: Flask = None,
                 title: str = "SiwaDocAPI",
                 description: str = "",
                 version="latest",
                 doc_url: Optional[str] = "/docs",
                 openapi_url: Optional[str] = "/openapi.json",
                 ui: Literal["redoc", "swagger", "rapidoc"] = "swagger"):
        self.app = app
        self._openapi = None
        self.title = title
        self.description = description
        self.version = version
        self.doc_url = doc_url
        self.openapi_url = openapi_url
        self.openapi_version = "3.0.2"
        self.ui = ui
        self.models: Dict[str: Dict] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self.app = app
        self._register_doc_blueprint()

    def _register_doc_blueprint(self):
        """
        注册文档蓝图
        """
        template_folder = os.path.join(os.path.dirname(__file__), "templates")
        siwa_bp = Blueprint("siwadoc",
                            __name__,
                            template_folder=template_folder,
                            )

        @siwa_bp.route(self.doc_url)
        def doc_html():
            ui = request.args.get("ui") or self.ui
            assert ui in SUPPORTED_UI, f"ui only support with {SUPPORTED_UI}"
            ui_file = f'{ui}.html'
            return render_template(ui_file, spec_url=self.openapi_url)

        @siwa_bp.route(f'{self.openapi_url}')
        def doc_json():
            return jsonify(self.openapi)

        self.app.register_blueprint(siwa_bp)

    @property
    def openapi(self):
        if not self._openapi:
            self._openapi = openapi.generate_openapi(openapi_version=self.openapi_version,
                                                     title=self.title,
                                                     version=self.version,
                                                     description=self.description,
                                                     app=self.app,
                                                     models=self.models)
        return self._openapi

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
