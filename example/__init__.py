from flask import Flask, request
from pydantic import BaseModel

from example.dto import LoginModel, UserModel, QueryModel
from flask_siwadoc import SiwaDoc

app = Flask(__name__)

siwa = SiwaDoc(app, title="xxx", description="yyy")


# or use factory pattern
# siwa = SiwaDoc()
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
@siwa.doc(resp=UserModel, tags=["user"], group="user")
def users(user_id):
    """
    user detail
    """
    for user in USERS:
        if user_id == user.id:
            return user
    else:
        return {}


@app.route("/users", methods=["GET"])
@siwa.doc(query=QueryModel, tags=["user"], group="user")
def users_list(query: QueryModel):
    """
    user list
    """
    return {"data": USERS[:query.size]}


@app.route("/user/login", methods=["POST"])
@siwa.doc(body=LoginModel, tags=['auth'], group='admin')
def user_login(body: LoginModel):
    return {
        "username": body.username,
        "password": body.password,
        "id": 1}


class TokenModel(BaseModel):
    token: str


@app.route("/me", methods=["GET"])
@siwa.doc(header=TokenModel, tags=['auth'], group='admin')
def param_in_header():
    token = request.headers.get("token")
    print("token:", token)
    return {"token": token}


@app.route("/cookie", methods=["GET"])
@siwa.doc(cookie=TokenModel, resp=UserModel, tags=['auth'], group='admin')
def param_in_cookie():
    token = request.cookies.get("token")
    print("token:", token)
    return {"token": token}


if __name__ == '__main__':
    app.run()
