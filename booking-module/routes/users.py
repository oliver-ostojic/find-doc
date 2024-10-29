from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from mongodb_connection import users_collection
from ..models.user import User

users_bp = Blueprint('users_bp', __name__)


@users_bp.route('/', methods=['POST'])
def create_user():
    try:
        # Parse request and validate using User model
        user_data = request.get_json()
        user = User(**user_data)
        # Convert Pydantic model to a dict
        user_dict = user.model_dump()
        # Insert into MongoDB and get inserted ID
        result = users_collection.insert_one(user_dict)
        # Return success response
        return jsonify({'message': 'User successfully created.', 'id': str(result.inserted_id)}), 201
    except ValidationError as e:
        return jsonify({'error': e.errors()}), 422
    except Exception as e:
        return jsonify({'error': str(e)}), 500
