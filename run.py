from app import app
import os

port = int(os.environ.get("PORT", 5001))

if __name__ == '__main__':
    app.run(debug=True, port=port)
