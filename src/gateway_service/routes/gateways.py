from flask import Blueprint, jsonify, g
from auth_module.middleware.jwt_validation import jwt_required

gateway_bp = Blueprint('gateway_bp', __name__)


@gateway_bp.route('/protected', methods=['GET'])
@jwt_required
def protected_route():
    user = g.user
    return jsonify({'protected': True, 'user': user})
