from flask import Flask
from .mongodb_connection import client, test_connection
from .routes.users import users_bp
from bson import ObjectId


def create_app():
    app = Flask(__name__)
    # Test MongoDB connection
    test_connection()
    # Register blueprints
    app.register_blueprint(users_bp, url_prefix='/users')
    return app
