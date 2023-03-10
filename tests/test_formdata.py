from flask import Flask
from pydantic import BaseModel

from example.dto import UserModel
from flask_siwadoc import SiwaDoc, ValidationError

app = Flask(__name__)

siwa = SiwaDoc(app, title="siwadocapi", description="一个自动生成openapi文档的库")


@app.post('/test/form')
@siwa.doc(form=UserModel)
def test_form(form: UserModel):

    return form.username


@app.post('/test/form_with_files')
@siwa.doc(form=UserModel, files={'file1': {"required": True, "single": False}, 'file2': {"required": False, "single": True}})
def test_form_with_files(form: UserModel, files: dict):

    print(form.username)
    print(files.keys())

    return form.username


@app.post('/test/form_only_files')
@siwa.doc(form=BaseModel, files={'file1': {"required": True, "single": False}, 'file2': {"required": False, "single": True}})
def test_form_only_files(files: dict):
    print(files.keys())

    return 'success'


@app.errorhandler(Exception)
def handle_error(e):
    if isinstance(e, ValidationError):
        return str(e)
    else:
        return 'unknown error'


if __name__ == '__main__':
    app.run(host='0.0.0.0')
