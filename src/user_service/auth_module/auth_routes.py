from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import bcrypt
from jwt import encode
from auth_module.user_model import get_user_by_email
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        # Parse login data
        login_data = request.get_json()
        email = login_data['email']
        password = login_data['password']
        # Make sure both email and password exist
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        # Fetch the user by email
        user = get_user_by_email(email)
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        # Verify password
        hashed_password = user['hashed_password'].encode('utf-8')
        if not bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return jsonify({'error': 'Invalid email or password'}), 401
        # Generate JWT
        payload = {
            'user_id': str(user['_id']),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token, 'message': 'Login successful'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
