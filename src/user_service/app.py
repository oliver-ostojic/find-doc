from flask import Flask
from dotenv import load_dotenv
from mongodb_connection import test_connection
from booking_module.routes.users import users_bp
from booking_module.routes.provider_schedules import provider_schedules_bp
from auth_module.auth_routes import auth_bp
import os


def create_app():
    # Load environment variables
    load_dotenv()

    app = Flask(__name__)
    # Set secret key for the Flask app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    # Test MongoDB connection
    test_connection()
    # Register blueprints
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(provider_schedules_bp, url_prefix='/provider_schedules')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    print(app.url_map)
    return app


# Add this block to run the app when the script is executed
if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
