from flask import Blueprint, request, jsonify
from extensions import db
from models import User, UserRole, UserStatus
from utils.security import hash_password, verify_password
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from integrations.beds24 import get_users, get_token_from_invite_code,set_pms
from datetime import datetime,timedelta

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    # print("!2312312312")
    email = data.get('userId', '').strip().lower()
    password = data.get('password', '')
    invite_code = data.get('inviteCode', '')
    if not email or not password:
        return jsonify(message='email and password required'), 400

    if User.query.filter_by(email=email).first():
        return jsonify(message='email already registered'), 409

    result = get_token_from_invite_code(invite_code)
    now = datetime.utcnow().isoformat()
    if result["success"]=="valid":
        user = User(email=email, password_hash=hash_password(password), role=UserRole.HOTEL, token = result["token"], refresh_token = result["refreshToken"], token_refresh_date = now)
    else:
        print("12312312321")
        return jsonify(message=result["msg"]), 201
    db.session.add(user)
    db.session.commit()
    return jsonify(message='success'), 200


@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    email = data.get('email', '')
    password = data.get('password', '')
    hashed = hash_password('password123')   
    user = User.query.filter_by(email=email).first()
    # set_pms(user.token)
     
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

    user_role = user.role.value
    pms_token = user.token
    pms_user_list = get_users(pms_token)
    
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
    # Use identity as string or int
    token = create_access_token(identity=str(pms_user_id), additional_claims={'role': user_role }, expires_delta=timedelta(days=3))
    return jsonify(access_token=token, role=user_role, pms_token = pms_token)


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
