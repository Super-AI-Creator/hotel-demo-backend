from datetime import datetime, timedelta, timezone as dt_tz
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from extensions import db
from models import Hotel, BookingSyncLog, UserRole, BookingAutoHistory, RoomLockMatch
from integrations.beds24 import Beds24Client, get_auto_bookings
from integrations.ttlock import TTLockClient
from typing import Optional

sync_bp = Blueprint('sync', __name__)

def _is_admin(jwt_claims):
    return jwt_claims['role'] == UserRole.ADMIN.value

def _to_ts_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def check_new_room_unit(hotel_id, room_id, unit_id):
    log = RoomLockMatch.query.filter_by(
        hotel_id=hotel_id,
        room_id=room_id,
        unit_id=unit_id,
    ).first()
    
    if log:
        return
    else:
        new_entry = RoomLockMatch(
                hotel_id=hotel_id,
                room_id=room_id,
                unit_id=unit_id,
                lock_id = 17549316
            )
        db.session.add(new_entry)
        db.session.commit()
        return    
        
def get_lock_id(hotel_id, room_id, unit_id):
    log = RoomLockMatch.query.filter_by(
        hotel_id=hotel_id,
        room_id=room_id,
        unit_id=unit_id,
    ).first()
    
    print("$$$$$$$$$$$")
    print(log.lock_id)
    if log:
        return log.lock_id   
    else:
        return None
    
def _pin_from_booking(booking_number: str, pin_length: int) -> str:
    digits = ''.join([c for c in (booking_number or '') if c.isdigit()])
    if not digits:
        digits = '0000'
    return digits[-pin_length:].rjust(pin_length, '0')

def _parse_dt(date_str: str, hm: str) -> Optional[datetime]:
    if not date_str:
        return None
    hh, mm = (hm or '00:00').split(':')
    dt_naive = datetime.strptime(f"{date_str} {hh}:{mm}", "%Y-%m-%d %H:%M")
    return dt_naive.replace(tzinfo=dt_tz.utc)

def _auth_hotel_or_owner(hotel_id):
    claims = get_jwt()
    user_id = get_jwt_identity()
    hotel = Hotel.query.get_or_404(hotel_id)
    if not _is_admin(claims) and str(hotel.owner_id) != str(user_id):
        return None, (jsonify(message='forbidden'), 403)
    return hotel, None

def get_hotel(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    return hotel, None

def _default_dates(body):
    start_iso = body.get('start')
    end_iso = body.get('end')
    if not start_iso or not end_iso:
        today = datetime.now(dt_tz.utc)
        start_iso = (today - timedelta(days=1)).date().isoformat()
        end_iso = (today + timedelta(days=7)).date().isoformat()
    return start_iso, end_iso

def _fetch_beds24_bookings(hotel: Hotel, payload: dict):
    beds = Beds24Client(hotel.beds24_api_key, hotel.beds24_prop_key)
    bookings = beds.get_bookings(payload)
    return bookings

def _map_booking_preview(b):
    # Normalized for BookingList.jsx
    return {
        "id": str(b.get('id') or ''),
        "guestName": f"{b.get('firstName', '')} {b.get('lastName', '')}".strip(),
        "roomNumber": str(b.get('unitId') or b.get('roomId') or ''),
        "checkInDate": b.get('arrival'),
        "checkOutDate": b.get('departure'),
        "portalId": b.get('apiSourceId'),
        "channel": b.get('channel') or b.get('apiSource') or '',
    }

@sync_bp.post('/bookings/<int:hotel_id>')
@jwt_required()
def list_bookings(hotel_id):
    """
    Preview-only endpoint: fetch bookings for the date window (no TTLock).
    Body: { start?: YYYY-MM-DD, end?: YYYY-MM-DD, hotelId?: number }
    """
    hotel, err = _auth_hotel_or_owner(hotel_id)
    if err:
        return err

    body = request.get_json() or {}
    # start_iso, end_iso = _default_dates(body)
    property_id = body.get('hotelId')
    payload_json = body
    payload_json.pop("hotelId", None)
    payload_json["propertyId"] = property_id
    print(property_id)
    try:
        bookings = _fetch_beds24_bookings(hotel, payload_json)
    except Exception as e:
        return jsonify(message='beds24 fetch failed', error=str(e)), 502

    previews = [_map_booking_preview(b) for b in (bookings or [])]
    print(previews)
    return jsonify(bookings=previews, count=len(previews))



@sync_bp.get('/auto_trigger')
def auto_trigger():
    bookings = get_auto_bookings()
    # print(bookings)
    processed = []
    for b in bookings:
        booking_id = str(b.get('id'))
        # print(b["propertyId"])
        hotel_id=str(b["propertyId"])

        hotel = Hotel.query.filter_by(hotel_id=hotel_id).first()
        
        check_new_room_unit(b["propertyId"], b["roomId"], b["unitId"])
        log = BookingSyncLog.query.filter_by(
            booking_number_internal=booking_id,
            status='CREATED', 
        ).first()
        
        print("-------------")
        print(log)
        if log:
            continue
        
        else:
            
            ttlock = TTLockClient(
                hotel.ttlock_client_id or '',
                hotel.ttlock_client_secret or '',
                hotel.ttlock_user_id or '',
                hotel.ttlock_user_password or '',
                hotel.beds24_prop_key or ''
            )
            
            default_lock_id = getattr(hotel, 'default_lockid', None) or getattr(hotel, 'default_lock_id', None)
            
            internal_no = str(b.get('id') or '')
            portal_no = str(b.get('apiSourceId') or '')
            guest_name = f"{b.get('firstName', '')} {b.get('lastName', '')}".strip()

            checkin_date = b.get('arrival')
            checkout_date = b.get('departure')

            start_dt = _parse_dt(checkin_date, hotel.checkInStart)
            end_dt = _parse_dt(checkout_date, hotel.checkOutEnd)

            # Determine PIN(s)
            if portal_no and portal_no != "0":
                pin_internal = _pin_from_booking(internal_no, hotel.pin_length)
                pin_portal = _pin_from_booking(portal_no, hotel.pin_length)
                pins = [(internal_no, pin_internal), (portal_no, pin_portal)]
            else:
                pin_internal = _pin_from_booking(internal_no, hotel.pin_length)
                pins = [(internal_no, pin_internal)]

            # Create TTLock access on the single default lock
            
            lock_id = get_lock_id(b["propertyId"], b["roomId"], b["unitId"])
            if not lock_id:
                lock_id = default_lock_id
                
            for booking_no, pin_code in pins:
                res = ttlock.create_or_update_pin(
                    lock_id=lock_id,
                    pin_code=pin_code,
                    start_ts_ms=_to_ts_ms(start_dt),
                    end_ts_ms=_to_ts_ms(end_dt),
                    name=f"{guest_name} ({booking_no})",
                    prop_key=hotel.beds24_prop_key,  # keep if your wrapper expects it
                )
                ok = isinstance(res, dict) and not res.get('error')
                status = 'CREATED' if ok else 'FAILED'
                msg = f"PIN {pin_code} -> {status}"

                log = BookingSyncLog(
                    hotel_id=hotel.id,
                    booking_number_internal=internal_no,
                    booking_number_portal=portal_no or None,
                    guest_name=guest_name,
                    room_number=None,
                    access_start=start_dt,
                    access_end=end_dt,
                    pin_code=pin_code,
                    status=status,
                    message=msg,
                    method="auto",
                    ttlock_payload=[{'lock': lock_id, 'result': res}],
                )
                db.session.add(log)
                processed.append({'booking': booking_no, 'pin': pin_code, 'status': status, 'msg': msg})

    db.session.commit()
    return jsonify(processed=processed, count=len(processed))

@sync_bp.post('/trigger/<int:hotel_id>')
@jwt_required()
def trigger_sync(hotel_id):
    """
    Full sync: fetch bookings AND create TTLock PINs for the default lock.
    """
    hotel, err = _auth_hotel_or_owner(hotel_id)
    if err:
        return err

    body = request.get_json() or {}
    start_iso, end_iso = _default_dates(body)
    property_id = body.get('hotelId')

    # property_id = body.get('hotelId')
    payload_json = body
    payload_json.pop("hotelId", None)
    payload_json["propertyId"] = property_id
    
    try:
        bookings = _fetch_beds24_bookings(hotel, payload_json)
    except Exception as e:
        return jsonify(message='beds24 fetch failed', error=str(e)), 502

    print("**************")
    print(bookings)

    ttlock = TTLockClient(
        hotel.ttlock_client_id or '',
        hotel.ttlock_client_secret or '',
        hotel.ttlock_user_id or '',
        hotel.ttlock_user_password or '',
        hotel.beds24_prop_key or ''
    )

    # Resolve default lock id (supports either attribute name)
    default_lock_id = getattr(hotel, 'default_lockid', None) or getattr(hotel, 'default_lock_id', None)
    if not default_lock_id:
        return jsonify(message="default TTLock lock id not configured on hotel"), 400

    processed = []

    for b in bookings or []:
        internal_no = str(b.get('id') or '')
        portal_no = str(b.get('apiSourceId') or '')
        guest_name = f"{b.get('firstName', '')} {b.get('lastName', '')}".strip()
        
        check_new_room_unit(b["propertyId"], b["roomId"], b["unitId"])
        
        checkin_date = b.get('arrival')
        checkout_date = b.get('departure')

        start_dt = _parse_dt(checkin_date, hotel.checkInStart)
        end_dt = _parse_dt(checkout_date, hotel.checkOutEnd)

        # Determine PIN(s)
        if portal_no and portal_no != "0":
            pin_internal = _pin_from_booking(internal_no, hotel.pin_length)
            pin_portal = _pin_from_booking(portal_no, hotel.pin_length)
            pins = [(internal_no, pin_internal), (portal_no, pin_portal)]
        else:
            pin_internal = _pin_from_booking(internal_no, hotel.pin_length)
            pins = [(internal_no, pin_internal)]

        # Create TTLock access on the single default lock
        
        lock_id = get_lock_id(b["propertyId"], b["roomId"], b["unitId"])
        if lock_id == None:
            lock_id = default_lock_id
        print("++++++++++++++")
        print(lock_id)
        for booking_no, pin_code in pins:
            res = ttlock.create_or_update_pin(
                lock_id=lock_id,
                pin_code=pin_code,
                start_ts_ms=_to_ts_ms(start_dt),
                end_ts_ms=_to_ts_ms(end_dt),
                name=f"{guest_name} ({booking_no})",
                prop_key=hotel.beds24_prop_key,  # keep if your wrapper expects it
            )
            ok = isinstance(res, dict) and not res.get('error')
            status = 'CREATED' if ok else 'FAILED'
            msg = f"PIN {pin_code} -> {status}"

            log = BookingSyncLog(
                hotel_id=hotel.id,
                booking_number_internal=internal_no,
                booking_number_portal=portal_no or None,
                guest_name=guest_name,
                room_number=None,
                access_start=start_dt,
                access_end=end_dt,
                pin_code=pin_code,
                status=status,
                message=msg,
                method="manual",
                ttlock_payload=[{'lock': lock_id, 'result': res}],
            )
            db.session.add(log)
            processed.append({'booking': booking_no, 'pin': pin_code, 'status': status, 'msg': msg})

    db.session.commit()
    return jsonify(processed=processed, count=len(processed), start=start_iso, end=end_iso)



@sync_bp.get('/history')
@jwt_required()
def get_history():
    """
    Returns booking sync logs.
    - Admins see all logs.
    - Hotel owners see only their hotels' logs.
    Each log includes the hotel name.
    """
    claims = get_jwt()
    user_id = get_jwt_identity()

    query = BookingSyncLog.query.join(Hotel, BookingSyncLog.hotel_id == Hotel.id)

    if not _is_admin(claims):
        hotels = Hotel.query.filter_by(owner_id=str(user_id)).all()
        hotel_ids = [h.id for h in hotels]
        query = query.filter(BookingSyncLog.hotel_id.in_(hotel_ids))

    logs = query.order_by(BookingSyncLog.created_at.desc()).limit(100).all()

    def log_to_dict(log):
        hotel = Hotel.query.get(log.hotel_id)
        return {
            "id": log.id,
            "hotel_id": log.hotel_id,   
            "hotel_name": hotel.name if hotel else None,
            "booking_number": log.booking_number_internal,
            "guest_name": log.guest_name,
            "room_number": log.room_number,
            "access_start": log.access_start.isoformat() if log.access_start else None,
            "access_end": log.access_end.isoformat() if log.access_end else None,
            "pin_code": log.pin_code,
            "ttlock_payload": log.ttlock_payload,
            "method": log.method,
        }

    return jsonify(logs=[log_to_dict(l) for l in logs])


    