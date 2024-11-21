import bcrypt
from bson.objectid import ObjectId, InvalidId
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError
from mongodb_connection import users_collection, provider_schedules_collection, client
from ..models.appointment import Appointment
from ..models.user import User
from ..models.schedule import Schedule
from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))
from auth_module.middleware.jwt_validation import jwt_required

# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
uri = os.getenv("MONGODB_URI")
# Set blueprint
users_bp = Blueprint('users_bp', __name__)


@users_bp.route('/', methods=['POST'])
def create_user():
    try:
        # Parse request and validate using User model
        user_data = request.get_json()
        if not user_data:
            return jsonify({'message': 'Missing or invalid JSON data'}), 400
        # Extract plain-text password
        plain_password = user_data.pop('password', None)
        if not plain_password:
            return jsonify({'message': 'Missing password'}), 400
        # Hash the password
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        # Add the hashed_password to user_data
        user_data['hashed_password'] = hashed_password.decode('utf-8')
        # Validate and create the user object
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


@users_bp.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Test succeeded!'}), 200


@users_bp.route('/', methods=['GET'])
@jwt_required
def get_user_info():
    # Get user_id from token
    user_id = g.user.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized: Missing user_id in token'}), 403
    try:
        user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    except (InvalidId, ValueError):
        return jsonify({'message': 'Invalid user ID'}), 400
    if user_data:
        user_data['_id'] = str(user_data['_id'])
        return jsonify(user_data), 200
    else:
        return jsonify({'message': 'User not found'}), 404


@users_bp.route('/appointment', methods=['POST'])
@jwt_required
def book_appointment():
    # Get user_id from token
    user_id = g.user.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized: Missing user_id in token'}), 403

    # Extract data from the request body
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Missing or invalid JSON data'}), 400
    # Extract appointment fields from the request body
    provider_id = data.get('provider_id')
    start_datetime = data.get('start_datetime')
    reason = data.get('reason')
    notes = data.get('notes')
    # Validate required fields
    if not provider_id or not start_datetime:
        return jsonify({'message': 'provider_id and start_datetime are required'}), 400
    # Create appointment object and dict
    else:
        appointment = Appointment(_id=str(ObjectId()),
                                  user_id=user_id,
                                  provider_id=provider_id,
                                  start_datetime=start_datetime,
                                  reason=reason,
                                  notes=notes)
        appointment_dict = appointment.model_dump()
    # Proceed with booking logic
    with client.start_session() as session:
        session.start_transaction()
        try:
            # Fetch the user's document from the collection
            user = users_collection.find_one({'_id': ObjectId(user_id)}, session=session)
            # Check in case user does not exist
            if not user:
                return jsonify({'message': 'User not found'}), 404
            # Fetch the provider's schedule
            provider_schedule_dict = provider_schedules_collection.find_one({'provider_id': int(provider_id)},
                                                                            session=session)
            if not provider_schedule_dict:
                return jsonify({'message': 'Provider schedule not found'}), 404
            # Covert dict to object
            provider_schedule = Schedule(**provider_schedule_dict)
            # Check in case provider_schedule does not exist
            # Check that the slot is still available in the schedule
            available = provider_schedule.is_slot_available(start_datetime)
            if not available:
                return jsonify({'message': 'Slot is not available'}), 404
            # Update schedule
            result = provider_schedules_collection.update_one({'provider_id': int(provider_id)},
                                                              {'$set': {'availability.$[slot].is_booked': True}},
                                                              array_filters=[{'slot.start_datetime': start_datetime}],
                                                              session=session)
            if result.modified_count == 0:
                raise ValueError("Failed to update provider's schedule.")
            # Add new appointment
            user_result = users_collection.update_one({'_id': ObjectId(user_id)},
                                                      {'$push': {'appointments': appointment_dict}},
                                                      session=session)
            if user_result.modified_count == 0:
                raise ValueError("Failed to add appointment to user's account.")
            # Close session
            session.commit_transaction()
            return jsonify({'message': 'Appointment successfully booked'}), 200
        except Exception as e:
            session.abort_transaction()
            return jsonify({'error': str(e)}), 500


@users_bp.route('/appointment/<apt_id>', methods=['DELETE'])
@jwt_required
def cancel_appointment(apt_id):
    # Get user_id from token
    user_id = g.user.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized: Missing user_id in token'}), 403
    # Proceed with canceling appointment logic
    with client.start_session() as session:
        session.start_transaction()
        try:
            # Get the user data
            user = users_collection.find_one({'_id': ObjectId(user_id)},
                                             session=session)
            if not user or 'appointments' not in user:
                return jsonify({'message': 'User or Appointment not found'}), 404
            # Find the specific appointment with apt_id
            appointment = next((apt for apt in user['appointments'] if apt['id'] == apt_id), None)
            if not appointment:
                return jsonify({'message': 'Appointment not found'}), 404
            # Delete appointment with apt_id
            result = users_collection.update_one({'_id': ObjectId(user_id)},
                                                 {'$pull': {'appointments': {'id': apt_id}}},
                                                 session=session)
            if result.modified_count == 0:
                raise ValueError("Failed to remove appointment from the user document.")
            # Get the provider_id from the appointment
            provider_id = appointment.get('provider_id')
            # Get the start time from the appointment
            start_datetime = appointment.get('start_datetime')
            # Ensure start_datetime is passed as a string
            if not isinstance(start_datetime, str):
                start_datetime = start_datetime.isoformat()
            # Update the provider's schedule to update appointment time_slot status
            update_result = provider_schedules_collection.update_one({'provider_id': provider_id},
                                                                     {'$set': {
                                                                         'availability.$[slot].is_booked': False}},
                                                                     array_filters=[
                                                                         {'slot.start_datetime': start_datetime}],
                                                                     session=session)
            if update_result.modified_count == 0:
                raise ValueError("Failed to update the provider's schedule.")
            # Close session
            session.commit_transaction()
            return jsonify({'message': 'Appointment successfully canceled'}), 200
        except Exception as e:
            session.abort_transaction()
            return jsonify({'error': str(e)}), 500
