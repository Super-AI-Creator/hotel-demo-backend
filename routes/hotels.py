from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt,get_jwt_identity
from extensions import db
from models import Hotel, Door, DoorType, UserRole, RoomLockMatch
from integrations.beds24 import get_hotels
from integrations.ttlock import TTLockClient

hotels_bp = Blueprint('hotels', __name__)


def _is_admin(jwt_claims):
    
    return jwt_claims['role'] == UserRole.ADMIN.value


@hotels_bp.post('')
@jwt_required()
def create_hotel():
    claims = get_jwt()
    data = request.get_json() or {}

    user_id = get_jwt_identity()
    hotel = Hotel(
        owner_id=str(user_id),
        name=data['name'],
        address=data.get('address'),
        timezone=data.get('timezone', 'UTC'),
        beds24_prop_key=data['beds24_prop_key'],
        beds24_api_key=data['beds24_api_key'],
        ttlock_client_id=data.get('ttlock_client_id'),
        ttlock_client_secret=data.get('ttlock_client_secret'),
        ttlock_uesr_id=data.get('ttlock_uesr_id'),
        ttlock_user_password=data.get('ttlock_user_password'),
        default_checkin_time=data.get('default_checkin_time', '14:00'),
        default_checkout_time=data.get('default_checkout_time', '10:00'),
        pin_length=int(data.get('pin_length', 4)),
    )
    db.session.add(hotel)
    db.session.commit()
    return jsonify(id=hotel.id), 201


@hotels_bp.get('/')
@jwt_required()
def list_hotels():
    user_id = get_jwt_identity()
    claims = get_jwt()
    hotel_list = get_hotels()
    hotel_real_list = []
    print(user_id)
    if _is_admin(claims):
        hotel_real_list = hotel_list
    else:
        for hotel in hotel_list:
            # print(hotel["account"])
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


@hotels_bp.put('/<int:hotel_id>')
@jwt_required()
def update_hotel(hotel_id):
    claims = get_jwt()
    hotel = Hotel.query.get_or_404(hotel_id)
    user_id = get_jwt_identity()
    if not _is_admin(claims) and str(hotel.owner_id) != str(user_id):
        return jsonify(message='forbidden'), 403

    data = request.get_json() or {}
    for field in ['name', 'address', 'timezone', 'beds24_prop_key', 'beds24_api_key',
                  'ttlock_client_id', 'ttlock_client_secret', 'ttlock_user_id','ttlock_user_password',
                  'default_checkin_time', 'default_checkout_time', 'pin_length','default_lockid']:
        if field in data:
            setattr(hotel, field, data[field])
    db.session.commit()
    return jsonify(message='updated')


@hotels_bp.get('/<int:hotel_id>/locks')
@jwt_required()
def get_locks(hotel_id):
    claims = get_jwt()
    hotel = hotel = Hotel.query.filter_by(hotel_id=hotel_id).first()
    user_id = get_jwt_identity()
    if not _is_admin(claims) and str(hotel.owner_id) != str(user_id):
        return jsonify(message='forbidden'), 403
    ttlock = TTLockClient(
        hotel.ttlock_client_id or '',
        hotel.ttlock_client_secret or '',
        hotel.ttlock_user_id or '',
        hotel.ttlock_user_password or '',
        hotel.beds24_prop_key or ''
    )
    locks_list = ttlock.get_locks()
    return jsonify(data = locks_list,message='updated')

@hotels_bp.get('/<int:hotel_id>/rooms')
@jwt_required()
def get_rooms(hotel_id):
    claims = get_jwt()
    rooms = RoomLockMatch.query.filter_by(hotel_id=hotel_id).all()  # use .all()
    
    # convert rooms to dict/list for jsonify
    rooms_list = [room.to_dict() for room in rooms]  # assuming you have a to_dict() method in your model
    
    return jsonify(data=rooms_list, message='updated')


@hotels_bp.post('/<int:hotel_id>/setlock')
@jwt_required()
def set_room_lockID(hotel_id):
    claims = get_jwt()
    body = request.get_json() or {}
    payload_json = body
    print(payload_json)
    match = RoomLockMatch.query.filter_by(
        room_id=payload_json['room_id'],
        unit_id=payload_json['unit_id']
    ).first()

    print(match)
    if match:
        match.lock_id = str(payload_json['lock_id'])  # Convert to string if needed
        db.session.commit()
        return jsonify(message='success')
    else:
        return jsonify(message='error')

@hotels_bp.post('/<int:hotel_id>/doors')
@jwt_required()
def add_door(hotel_id):
    
    user_id = get_jwt_identity()
    claims = get_jwt()

    hotel = Hotel.query.get_or_404(hotel_id)
    if not _is_admin(claims) and str(hotel.owner_id) != str(user_id):
        return jsonify(message='forbidden'), 403

    data = request.get_json() or {}
    door = Door(
        hotel_id=hotel.id,
        type=DoorType(data['type']),
        label=data['label'],
        number=data.get('number'),
        range_start=data.get('range_start'),
        range_end=data.get('range_end'),
    )
    db.session.add(door)
    db.session.commit()
    return jsonify(id=door.id), 201


@hotels_bp.get('/<int:hotel_id>/doors')
@jwt_required()
def list_doors(hotel_id):
    claims = get_jwt()
    user_id = get_jwt_identity()
    hotel = Hotel.query.get_or_404(hotel_id)
    print(user_id)
    print(hotel.owner_id)
    if not _is_admin(claims) and str(hotel.owner_id) != str(user_id):
        print(hotel.owner_id != user_id)
        return jsonify(message='forbidden'), 403

    return jsonify([
        {
            'id': d.id,
            'type': d.type.value,
            'label': d.label,
            'number': d.number,
            'range_start': d.range_start,
            'range_end': d.range_end,
        } for d in hotel.doors
    ])