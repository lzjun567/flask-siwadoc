import os
from functools import wraps
from typing import Optional, Type, Dict, Literal

import pydantic
from flask import Blueprint, request, Flask, render_template
from flask import jsonify
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from flask_httpauth import HTTPBasicAuth
from . import utils, openapi, error
from .error import ValidationError
from pydantic import ValidationError as PydanticError
from pydantic.errors import PydanticUserError
from pydantic.v1.error_wrappers import ErrorWrapper
import uuid

__all__ = ["SiwaDoc", "ValidationError"]

__version__ = "0.2.3"

SUPPORTED_UI = ('redoc', 'swagger', 'rapidoc')

auth = HTTPBasicAuth()
users = dict()


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username


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
            siwa_user = self.app.config.get("SIWA_USER")
            siwa_pass = self.app.config.get("SIWA_PASSWORD")
            if siwa_user and siwa_pass:
                global users
                users = {
                    siwa_user: generate_password_hash(siwa_pass),
                }
                login_info = auth.get_auth()
                password = auth.get_auth_password(login_info)
                status = None
                user = auth.authenticate(login_info, password)
                if user in (False, None):
                    status = 401
                elif not auth.authorize(None, user, auth):
                    status = 403
                if status:
                    try:
                        return auth.auth_error_callback(status)
                    except TypeError:
                        return auth.auth_error_callback()
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
            param: Optional[Type[BaseModel]] = None,
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
        if not query:
            query = param
        # 当formdata中有文件时，将文件参数添加到form schema中。需要将form动态创建一个子类，保证schema不冲突。
        if files and form:
            form = type(f'{form.__name__}-{uuid.uuid1()}', (form,), {})

        def decorate_validate(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                query_data, body_data, form_data, files_data = None, None, None, None
                # 注解参数
                query_in_kwargs = func.__annotations__.get("query") or func.__annotations__.get("param")
                body_in_kwargs = func.__annotations__.get("body")
                form_in_kwargs = func.__annotations__.get("form")
                files_in_kwargs = func.__annotations__.get("files")
                query_model = query_in_kwargs or query
                body_model = body_in_kwargs or body
                form_model = form_in_kwargs or form

                if query_model:
                    query_params = utils.convert_query_params(request.args, query_model)
                    query_data = query_model(**query_params)

                if body_model is not None:
                    body_data = body_model(**(request.get_json(force=True, silent=True) or {}))

                if form_model:
                    form_data = form_model(**request.form)

                    if files:
                        request_files = request.files
                        files_data = {}
                        for file_field, file_conf in files.items():
                            is_required_ = file_conf.get('required', False)
                            is_single_file_ = file_conf.get('single', True)
                            file_list = request_files.getlist(file_field)
                            if is_required_ and not file_list:
                                raise PydanticError(errors=[ErrorWrapper(exc=PydanticUserError(), loc=(file_field,))],
                                                    model=form_model)

                            if file_list and is_single_file_ and len(file_list) > 1:
                                raise PydanticError(
                                    errors=[ErrorWrapper(exc=PydanticUserError(limit_value=1), loc=(file_field,))],
                                    model=form_model)

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
                                file_schema = {'title': field, 'type': 'array',
                                               'items': {'type': 'string', 'format': 'binary'}}
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
