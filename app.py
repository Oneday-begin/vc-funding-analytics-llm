"""WSGI entry point. Run locally with `python app.py`."""
import os
from webapp import create_app

app = create_app()
engine = app.extensions['database']

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)
