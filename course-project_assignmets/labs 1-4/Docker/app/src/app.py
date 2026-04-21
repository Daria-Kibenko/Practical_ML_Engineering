import os
from flask import Flask

app = Flask(__name__)


@app.route('/')
def hello():
    return 'Backend app is running!'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
