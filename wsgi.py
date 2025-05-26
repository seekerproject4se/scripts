from flask import Flask, request
import importlib

def create_app(script_name):
    module = importlib.import_module(script_name)
    return module.app

app = Flask(__name__)

@app.route('/<script_name>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def load_script(script_name):
    script_app = create_app(script_name)
    return script_app(request.environ, start_response)

def start_response(status, headers):
    return lambda response: (status, headers, response)
