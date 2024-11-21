from mongodb_connection import users_collection


def get_user_by_email(email):
    return users_collection.find_one({"email": email})
