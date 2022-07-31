from flask import Flask, request
from flask.views import MethodView
from pydantic import BaseModel

from example.dto import LoginModel, UserModel, QueryModel
from flask_siwadoc import SiwaDoc

app = Flask(__name__)

siwa = SiwaDoc(app, title="siwadocapi", description="一个自动生成openapi文档的库")



class UpdatePasswordModel(BaseModel):
    password: str



class TestView(MethodView):
    @siwa.doc()
    def get(self):
        """
        method view description
        """
        return "hello"

    @siwa.doc()
    def post(self):
        return "post"

@app.route("/hello", methods=["GET"])
@siwa.doc()
def hello():
    return "hello siwadoc"
app.add_url_rule('/counter', view_func=TestView.as_view('counter'))

if __name__ == '__main__':
    app.run()
