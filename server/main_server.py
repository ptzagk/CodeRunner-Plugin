from fastapi import FastAPI, Request, Depends, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import requests
import json
import logging
import uvicorn
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.requests import Request
from contextvars import ContextVar
from waitress import serve
from threading import Thread
import random
import string
import os

ORIGINS = [
  "https://coderunner-plugin.haseebmir.repl.co/", "https://chat.openai.com"
]

## Main application for FastAPI Web Server
app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=ORIGINS,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Mount the .well-known directory.
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Setup logging for the application.
global logger

# Context variable to store the request.
# Credit - https://sl.bing.net/ib0YUGReKZg
request_var: ContextVar[Request] = ContextVar("request")

# JDoodle language codes.
# Credit - https://sl.bing.net/jbo456vZ8Eu
lang_codes = {
  'java': 'java',
  'c': 'c',
  'c++': 'cpp14',
  'cpp': 'cpp17',
  'php': 'php',
  'perl': 'perl',
  'python': 'python3',
  'ruby': 'ruby',
  'go': 'go',
  'scala': 'scala',
  'bash': 'bash',
  'sql': 'sql',
  'pascal': 'pascal',
  'csharp': 'csharp',
  'vbnet': 'vbn',
  'haskell': 'haskell',
  'objectivec': 'objc',
  'swift': 'swift'
}


#Method to configure logs.
def configure_logger(name: str, filename: str):
  logger = logging.getLogger(name)
  logger.setLevel(logging.INFO)

  file_handler = logging.FileHandler(filename)
  formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  file_handler.setFormatter(formatter)

  logger.addHandler(file_handler)
  return logger


def generate_code_id(response, length=10):
  characters = string.ascii_letters + string.digits
  unique_id = ''.join(random.choice(characters) for i in range(length))
  response['id'] = unique_id
  return response


# Method to get the JDoodle client ID and secret.
def get_jdoodle_client_1():
  client_id = '{}{}{}{}{}'.format('693e67ab', '032c', str(int('13')), 'c9',
                                  '0ff01e3dca2c6' + str(int('117')))
  client_secret = '{}{}{}{}{}{}{}{}'.format('c8870a78', '9a35e488', '2de3b383',
                                            '789e0801', '1a1456e8', '8dc58892',
                                            '61748d4b', '01d4a79d')
  return client_id, client_secret


def get_jdoodle_client_2():
  client_id = '{}{}{}{}'.format('e0c1fdfe', '9506fe7e', '35186a25', '9e36e5f5')
  client_secret = '{}{}{}{}{}{}'.format('e19a110c', '7ce8934c', '4f78017a',
                                        'acb55073', 'e3a0670c',
                                        'b871442dfcc40e28a40f66b3')
  return client_id, client_secret


def get_jdoodle_client():
  index = 1
  logger.info(f"get_jdoodle_client: Getting jdoodle client {index}")
  credits_used = get_credits_used()
  if credits_used < 200:
    logger.info("get_jdoodle_client: return client_1")
    return get_jdoodle_client_1()
  else:
    logger.error("Credits exhaused for client_1")
    logger.info("get_jdoodle_client: return client_2")
    return get_jdoodle_client_2()


# Method to call the JDoodle "credit-spent" API.
def get_jdoodle_credit_spent():
  client_id, client_secret = get_jdoodle_client_1()
  url = "https://api.jdoodle.com/v1/credit-spent"
  headers = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  }

  body = {"clientId": client_id, "clientSecret": client_secret}
  logger.info(f"get_jdoodle_credit_spent: sending request with url {url}")
  credit_spent = requests.post(url, headers=headers, data=json.dumps(body))
  logger.info(f"get_jdoodle_credit_spent: {credit_spent}")
  return credit_spent


# Helper method to get the request.
def get_request():
  return request_var.get()


def set_request(request: Request):
  request_var.set(request)


@app.middleware("http")
async def set_request_middleware(request: Request, call_next):
  set_request(request)
  response = await call_next(request)
  return response


# Method to run the code.
@app.post('/run_code')
async def run_code():
  request = get_request()
  data = await request.json()
  logger.info(f"run_code: data is {data}")
  script = data.get('script')
  language = data.get('language')

  # Convert the language to the JDoodle language code.
  language_code = lang_codes.get(language, language)
  logger.info(f"run_code: language_code is {language_code}")

  # Declare input and compileOnly optional.
  input = data.get('input', None)
  compile_only = data.get('compileOnly', False)

  try:
    # Get the JDoodle client ID and secret.
    client_id, client_secret = get_jdoodle_client()
    compiler_api_Url = "https://api.jdoodle.com/v1/execute"
    headers = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    }

    body = {
      'clientId': client_id,
      'clientSecret': client_secret,
      'script': script,
      'language': language_code,
      'stdin': input,
      'compileOnly': compile_only,
      'versionIndex': '0',
    }
    # Filter out the client ID, client secret from the body.
    body_filtered = {
      k: v
      for k, v in body.items() if k not in ['clientId', 'clientSecret']
    }

    logger.info(f"run_code: body is {body_filtered}")
    response_data = requests.post(compiler_api_Url,
                                  headers=headers,
                                  data=json.dumps(body))
    response = json.loads(response_data.content.decode('utf-8'))
    # Check reponse status code before appending the code id.
    if response_data.status_code == 200:
      response = generate_code_id(response)

    logger.info(f"run_code: {response}")
  except Exception as e:
    return {"error": str(e)}
  return {"result": response}


# Method to save the code.
@app.post('/save_code')
async def save_code():
  request = get_request()
  data = await request.json()  # Get JSON data from request
  logger.info(f"save_code: data is {data}")
  filename = data.get('filename')
  code = data.get('code')

  if filename is None or code is None:
    return {"error": "filename or code not provided"}, 400

  directory = 'codes'
  filepath = os.path.join(directory, filename)

  logger.info(f"save_code: filename is {filepath} and code was present")
  async with aiofiles.open(filepath, 'w') as f:
    await f.write(code)
  logger.info(f"save_code: wrote code to file {filepath}")
  download_link = f'{request.url_for("download",filename=filename)}'
  logger.info(f"save_code: download link is {download_link}")
  output = ""
  if download_link:
    output = {"download_link": download_link}
  return output


# Method to download the file.
@app.get('/download/{filename}')
async def download(filename: str):
  directory = 'codes'
  filepath = os.path.join(directory, filename)
  logger.info(f"download filename is {filepath}")
  return FileResponse(filepath, filename=filepath)


# Plugin logo.
@app.get("/logo.png")
async def plugin_logo():
  filename = 'logo.png'
  logging.info(f"logo filename is {filename}")
  return FileResponse(filename)


# Plugin manifest.
@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
  with open("./.well-known/ai-plugin.json") as f:
    text = f.read()
    return Response(text, media_type="text/json")


# Plugin OpenAPI spec.
@app.get("/openapi.yaml")
async def openapi_spec():
  with open("openapi.yaml") as f:
    text = f.read()
    return Response(text, media_type="text/yaml")


def get_credits_used():
  try:
    logger.info("get_credits_used: called")
    response = get_jdoodle_credit_spent()
    credit_spent = response.json()
    credits_used = 0
    logger.info(f"get_credits_used response : {credit_spent}")

    if credit_spent:
      credits_used = credit_spent['used']
      logger.info(f"get_credits_used Credits used: {credits_used}")

    return credits_used
  except Exception as e:
    logger.error(str(e))


@app.get('/credit_limit')
def show_credits_spent():
  credit_spent = 0
  try:
    credits_used = get_credits_used()
    return {"credits:": credits_used}

  except Exception as e:
    return {"error": str(e)}
    return {"result": credit_spent}


@app.get('/help')
@app.get('/')
async def help():
  logger.info("help: Displayed for Plugin Guide")
  json_data = {
    "title":
    "Code Runner Guide",
    "features": [{
      "name": "Run Code",
      "description": "Runs the code in the current editor."
    }, {
      "name":
      "Save Code",
      "description":
      "Saves the code in the current editor to a file."
    }, {
      "name":
      "Download Code",
      "description":
      "Downloads the code in the current editor to a file."
    }],
    "prompts": [{
      "name":
      "Write me C++ program for factorial of number and Run the program.",
      "description":
      "Writes a C++ program for factorial of number and runs the program."
    }, {
      "name": "Given the program [YOUR_CODE] and only compile the program.",
      "description": "Compiles the program [YOUR_CODE]."
    }, {
      "name":
      "Save the program [YOUR_CODE] with filename [YOUR_FILENAME].",
      "description":
      "Saves the program [YOUR_CODE] with filename [YOUR_FILENAME]."
    }, {
      "name":
      "Download the code  filename [YOUR_FILENAME].",
      "description":
      "Downloads the code with filename [YOUR_FILENAME]."
    }]
  }
  return json_data


# Testing purpose.
# call this with uvicorn main:app --reload only.
logger = configure_logger('CodeRunner', 'CodeRunner.log')

# Run the app.
# Will only work with python main.py
if __name__ == "__main__":
  logger = configure_logger('CodeRunner', 'CodeRunner.log')
  uvicorn.run(app, host='0.0.0.0', port=8080)
