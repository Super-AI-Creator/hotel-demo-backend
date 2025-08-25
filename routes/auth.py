from flask import Blueprint, request, jsonify
from extensions import db
from models import User, UserRole, UserStatus
from utils.security import hash_password, verify_password
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from integrations.beds24 import get_users

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify(message='email and password required'), 400

    if User.query.filter_by(email=email).first():
        return jsonify(message='email already registered'), 409

    user = User(email=email, password_hash=hash_password(password), role=UserRole.HOTEL)
    db.session.add(user)
    db.session.commit()
    return jsonify(message='registered, pending approval'), 201


@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    email = data.get('email', '')
    password = data.get('password', '')
    hashed = hash_password('password123')
    pms_user_list = get_users()
    
    pms_user_flag = 0
    pms_user_id = ""
    for user in pms_user_list:
        if user["username"] == email:
            pms_user_flag = 1
            pms_user_id = user["id"]
            print("-------------------------")
    
    print(pms_user_list)
    if pms_user_flag == 0:
        return jsonify(
            message="Unregistered user. Please contact support.",
            code=403
        ), 403
        
    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify(
            message="Invalid Credential.",
            code=405
        ), 405

    if user.status != UserStatus.ACTIVE:
        return jsonify(
            message="No Active User.",
            code=401
        ), 401


    # Use identity as string or int
    
    token = create_access_token(identity=str(pms_user_id), additional_claims={'role': user.role.value})

    print(token)
    return jsonify(access_token=token, role=user.role.value)


@auth_bp.post('/admin/approve/<int:user_id>')
@jwt_required()
def approve_user(user_id):
    claims = get_jwt()
    if claims['sub']['role'] != UserRole.ADMIN.value:
        return jsonify(message='admin only'), 403

    user = User.query.get_or_404(user_id)
    user.status = UserStatus.ACTIVE
    db.session.commit()
    return jsonify(message='approved')


@auth_bp.post('/admin/block/<int:user_id>')
@jwt_required()
def block_user(user_id):
    claims = get_jwt()
    if claims['sub']['role'] != UserRole.ADMIN.value:
        return jsonify(message='admin only'), 403

    user = User.query.get_or_404(user_id)
    user.status = UserStatus.BLOCKED
    db.session.commit()
    return jsonify(message='blocked')
