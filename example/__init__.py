from flask import Flask, request
from flask.views import MethodView
from pydantic import BaseModel

from example.dto import LoginModel, UserModel, QueryModel
from flask_siwadoc import SiwaDoc

app = Flask(__name__)

siwa = SiwaDoc(app, title="siwadocapi", description="一个自动生成openapi文档的库")


# 或者使用工厂模式
# siwa = SiwaDoc(title="siwadocapi", description="一个自动生成openapi文档的库")
# siwa.init_app(app)

class UpdatePasswordModel(BaseModel):
    password: str


USERS = [
    {"username": "siwa1", "id": 1},
    {"username": "siwa2", "id": 2},
    {"username": "siwa3", "id": 3},
]


@app.route("/hello", methods=["GET"])
@siwa.doc()
def hello():
    return "hello siwadoc"


@app.route("/users", methods=["GET"])
@siwa.doc(query=QueryModel, resp=UserModel)
def users_list(query: QueryModel):
    """
    user list
    """
    return {"data": USERS[:query.size]}


class TokenModel(BaseModel):
    token: str


@app.route("/me", methods=["GET"])
@siwa.doc(header=TokenModel, tags=['auth'], group='admin')
def param_in_header():
    token = request.headers.get("token")
    print("token:", token)
    return {"token": token}


@app.route("/home", methods=["GET"])
@siwa.doc(summary="主页", description="这是一段描述")
def home():
    return "this is home"


@app.route("/admin/login", methods=["POST"])
@siwa.doc(body=LoginModel, resp=UserModel, tags=['auth'], group='admin', summary="用户登录")
def admin_login(body: LoginModel):
    """
    这是一段接口的描述文字
    hello world
    """
    return {"username": body.username, "id": 1}


@app.route("/admin/users/<int(min=1):user_id>", methods=["POST"])
@siwa.doc(query=QueryModel, body=UpdatePasswordModel, resp=UserModel, tags=['auth'], group="admin")
def update_password(user_id):
    """
    update password
    """
    return {"username": "siwa", "id": user_id}


@app.route("/users/<int:user_id>", methods=["GET"])
@siwa.doc(resp=UserModel, tags=["user"])
def users(user_id):
    """
    user detail
    """
    for user in USERS:
        if user_id == user.id:
            return user
    else:
        return {}


@app.route("/user/login", methods=["POST"])
@siwa.doc(body=LoginModel, tags=['auth'])
def user_login(body: LoginModel):
    return {
        "username": body.username,
        "password": body.password,
        "id": 1}


class CookieModel(BaseModel):
    foo: str


@app.route("/cookie", methods=["GET"])
@siwa.doc(cookie=CookieModel, tags=['auth'])
def param_in_cookie():
    foo = request.cookies.get("foo")
    print("foo:", foo)
    return {"foo": foo}


class TestView(MethodView):
    @siwa.doc(query=QueryModel)
    def get(self):
        """
        method view description
        """
        return "hello"

    @siwa.doc(cookie=CookieModel, tags=['auth'])
    def post(self):
        """
        this is a post method
        """
        return "post"


app.add_url_rule('/counter', view_func=TestView.as_view('counter'))

if __name__ == '__main__':
    app.run()
