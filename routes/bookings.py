from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt,get_jwt_identity
from extensions import db
from models import Hotel, Door, DoorType, UserRole
from integrations.beds24 import get_hotels

bookings_bp = Blueprint('bookings', __name__)


def _is_admin(jwt_claims):
    
    return jwt_claims['role'] == UserRole.ADMIN.value


@bookings_bp.get('/')
@jwt_required()
def list_bookings():
    user_id = get_jwt_identity()
    claims = get_jwt()
    hotel_list = get_hotels()
    hotel_real_list = []
    print(user_id)
    if _is_admin(claims):
        hotel_real_list = hotel_list
    else:
        for hotel in hotel_list:
            if str(hotel["account"]["ownerId"]) == str(user_id):
                hotel_real_list.append(hotel)

    if _is_admin(claims):
        hotels = Hotel.query.all()
    else:
        hotels = Hotel.query.filter_by(owner_id=user_id).all()
    
    for pms_hotel in hotel_real_list:
        new_flag = 1
        for hotel in hotels:
            if str(hotel.hotel_id) == str(pms_hotel["id"]):
                new_flag = 0
                break
        if new_flag == 1:
            print("----")
            new_hotel = Hotel(
                hotel_id=str(pms_hotel["id"]),  # set actual data
                owner_id=str(user_id),
                name=pms_hotel["name"],
                checkInStart=str(pms_hotel["checkInStart"]),
                checkInEnd=str(pms_hotel["checkInEnd"]),    
                checkOutEnd=str(pms_hotel["checkOutEnd"]),
            )
            db.session.add(new_hotel) 
    db.session.commit() 
            
    
    if _is_admin(claims):
        hotels = Hotel.query.all()
    else:
        hotels = Hotel.query.filter_by(owner_id=user_id).all()        
    return jsonify([
        {
            'id': h.id,
            'hotel_id': h.hotel_id,
            'name': h.name,
            'beds24_prop_key':h.beds24_prop_key,
            'beds24_api_key':h.beds24_api_key,
            'ttlock_client_id':h.ttlock_client_id,
            'ttlock_client_secret':h.ttlock_client_secret,
            'ttlock_user_id':h.ttlock_user_id,
            'ttlock_user_password':h.ttlock_user_password,
            'timezone': h.timezone,
            'pin_length': h.pin_length,
            'checkInStart': h.checkInStart,
            'checkOutEnd': h.checkOutEnd,
            'default_lockid': h.default_lockid,
        } for h in hotels
    ])

