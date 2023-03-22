import os
from functools import wraps
from typing import Optional, Type, Dict, Callable, TypeVar, Any

import pydantic
from flask import Blueprint, request, Flask, render_template, typing as ft
from flask import jsonify
from pydantic import BaseModel
from pydantic.typing import Literal

from . import utils, openapi, error
from .error import ValidationError
from pydantic import ValidationError as PydanticError
from pydantic.errors import MissingError, ListMaxLengthError
from pydantic.error_wrappers import ErrorWrapper
import uuid

__all__ = ["SiwaDoc", "ValidationError"]

__version__ = "0.2.0"

SUPPORTED_UI = ('redoc', 'swagger', 'rapidoc')
T_route = TypeVar("T_route", bound=ft.RouteCallable)


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
        self.models: Dict[str, Dict] = {}
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
            form: Optional[Type[BaseModel]] = None,
            files=None,
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

        # 当formdata中有文件时，将文件参数添加到form schema中。需要将form动态创建一个子类，保证schema不冲突。
        if files and form:
            form = type(f'{form.__name__}-{uuid.uuid1()}', (form,), {})

        def decorate_validate(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                query_data, body_data, form_data, files_data = None, None, None, None
                # 注解参数
                query_in_kwargs = func.__annotations__.get("query")
                body_in_kwargs = func.__annotations__.get("body")
                form_in_kwargs = func.__annotations__.get("form")
                files_in_kwargs = func.__annotations__.get("files")
                query_model = query_in_kwargs or query
                body_model = body_in_kwargs or body
                form_model = form_in_kwargs or form

                if query_model:
                    query_params = utils.convert_query_params(request.args, query_model)
                    try:
                        query_data = query_model(**query_params)
                    except pydantic.error_wrappers.ValidationError as e:
                        raise ValidationError(e)

                if body_model is not None:
                    try:
                        body_data = body_model(**(request.get_json(force=True, silent=True) or {}))
                    except pydantic.error_wrappers.ValidationError as e:
                        raise ValidationError(e)

                if form_model:
                    try:
                        form_data = form_model(**request.form)
                    except pydantic.error_wrappers.ValidationError as e:
                        raise ValidationError(e)

                    if files:
                        request_files = request.files
                        files_data = {}
                        for file_field, file_conf in files.items():
                            is_required_ = file_conf.get('required', False)
                            is_single_file_ = file_conf.get('single', True)
                            file_list = request_files.getlist(file_field)
                            if is_required_ and not file_list:
                                raise ValidationError(PydanticError(errors=[ErrorWrapper(exc=MissingError(), loc=(file_field,))], model=form_model))

                            if file_list and is_single_file_ and len(file_list) > 1:
                                raise ValidationError(PydanticError(errors=[ErrorWrapper(exc=ListMaxLengthError(limit_value=1), loc=(file_field,))], model=form_model))

                            if file_list:
                                files_data[file_field] = file_list[0] if is_single_file_ else file_list

                if query_in_kwargs:
                    kwargs["query"] = query_data
                if body_in_kwargs:
                    kwargs["body"] = body_data
                if form_in_kwargs:
                    kwargs["form"] = form_data
                if files_in_kwargs:
                    kwargs["files"] = files_data

                return func(*args, **kwargs)

            for model, name in zip(
                    (query, header, cookie, body, form, resp), ('query', 'header', 'cookie', 'body', 'form', 'resp')
            ):
                if model:
                    assert issubclass(model, BaseModel)
                    schema = model.schema()

                    if name == 'form' and files:
                        # 将files中定义的字段填充到form的schema中
                        assert isinstance(files, dict)
                        for field, conf in files.items():
                            is_single_file = conf.get('single', True)
                            if is_single_file:
                                file_schema = {'title': field, 'type': 'string', 'format': 'binary'}
                            else:
                                file_schema = {'title': field, 'type': 'array', 'items': {'type': 'string', 'format': 'binary'}}
                            schema['properties'][field] = file_schema

                            is_required = conf.get('required', False)
                            if is_required:
                                required_fields = schema.get('required', [])
                                required_fields.append(field)
                                schema['required'] = required_fields

                    self.models[model.__name__] = schema
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

    def blueprint(self, *args, **kwargs):
        return SiwaBlueprint(self, *args, **kwargs)


class SiwaBlueprint(Blueprint):
    siwa: SiwaDoc
    tags = []
    group = None

    def __init__(self, siwa: SiwaDoc, *args, **kwargs):
        self.siwa = siwa
        if 'tags' in kwargs:
            self.tags = kwargs.pop('tags')
        if 'group' in kwargs:
            self.group = kwargs.pop('group')

        super().__init__(*args, **kwargs)

    def route(self,
              rule,
              *,
              query: Optional[Type[BaseModel]] = None,
              header: Optional[Type[BaseModel]] = None,
              cookie: Optional[Type[BaseModel]] = None,
              body: Optional[Type[BaseModel]] = None,
              form: Optional[Type[BaseModel]] = None,
              files=None,
              resp=None,
              x=[],
              tags=[],
              group=None,
              summary=None,
              description=None,
              ignore=False,
              **options: Any) -> Callable[[T_route], T_route]:

        # 忽略不使用 siwadoc 的接口
        if ignore:
            return super().route(rule, **options)

        def decorator(func) -> T_route:
            view_func = self.siwa.doc(query,
                                      header,
                                      cookie,
                                      body,
                                      form,
                                      files,
                                      resp,
                                      x,
                                      tags or self.tags,
                                      group or self.group,
                                      summary,
                                      description)(func)
            view = self.__blueprint_route(view_func, rule, **options)

            @wraps
            def inner(*args, **kwargs):
                return view(*args, **kwargs)

            return inner

        return decorator

    def __blueprint_route(self, view_func, rule, **options):
        return super().route(rule, **options)(view_func)
