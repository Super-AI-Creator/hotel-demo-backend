from datetime import datetime, time
from extensions import db
from sqlalchemy import Enum as SAEnum
import enum


class UserRole(str, enum.Enum):
    ADMIN = 'ADMIN'
    HOTEL = 'HOTEL'


class UserStatus(str, enum.Enum):
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'
    BLOCKED = 'BLOCKED'


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(SAEnum(UserRole), default=UserRole.HOTEL, nullable=False)
    status = db.Column(SAEnum(UserStatus), default=UserStatus.PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # hotels = db.relationship('Hotel', backref='owner', lazy=True)


class Hotel(db.Model):
    __tablename__ = 'hotels'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.String(128))  # 4 or 6
    owner_id = db.Column(db.String(128))
    checkInStart = db.Column(db.String(128))
    checkInEnd = db.Column(db.String(128))
    checkOutEnd = db.Column(db.String(128))

    name = db.Column(db.String(255),  nullable=True)
    timezone = db.Column(db.String(64), default='UTC')

    # PMS (Beds24) connection
    beds24_prop_key = db.Column(db.String(128),  nullable=True)
    beds24_api_key = db.Column(db.String(256), nullable=True)

    # TTLock connection
    ttlock_client_id = db.Column(db.String(128), nullable=True)
    ttlock_client_secret = db.Column(db.String(256), nullable=True)
    ttlock_user_id = db.Column(db.String(512), nullable=True)
    ttlock_user_password = db.Column(db.String(512), nullable=True)
    default_lockid = db.Column(db.String(128))
    pin_length = db.Column(db.Integer, default=4)  # 4 or 6

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doors = db.relationship('Door', backref='hotel', lazy=True, cascade='all,delete')
    logs = db.relationship('BookingSyncLog', backref='hotel', lazy=True, cascade='all,delete')


class DoorType(str, enum.Enum):
    FRONT = 'FRONT'
    HALLWAY = 'HALLWAY'
    ROOM = 'ROOM'


class Door(db.Model):
    __tablename__ = 'doors'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)
    type = db.Column(SAEnum(DoorType), nullable=False)

    # For hallway ranges like 1-10, 2-20 etc we can store ranges
    label = db.Column(db.String(128), nullable=False)
    number = db.Column(db.Integer, nullable=True)  # for ROOM number or FRONT code if needed
    range_start = db.Column(db.Integer, nullable=True)
    range_end = db.Column(db.Integer, nullable=True)


class BookingSyncLog(db.Model):
    __tablename__ = 'booking_sync_logs'
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=False)

    booking_number_internal = db.Column(db.String(64))
    booking_number_portal = db.Column(db.String(64))
    guest_name = db.Column(db.String(255))
    room_number = db.Column(db.String(64))

    access_start = db.Column(db.DateTime)
    access_end = db.Column(db.DateTime)
    pin_code = db.Column(db.String(12))

    status = db.Column(db.String(32))  # CREATED / UPDATED / FAILED
    message = db.Column(db.Text)

    ttlock_payload = db.Column(db.JSON)
    method = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    

class BookingAutoHistory(db.Model):
    __tablename__ = 'booking_auto_hitory'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer)
    success = db.Column(db.String(128))
    
    
    
class RoomLockMatch(db.Model):
    __tablename__ = "room_lock_match"

    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer)
    room_id = db.Column(db.Integer)
    unit_id = db.Column(db.Integer)
    lock_id = db.Column(db.String)

    def to_dict(self):
        return {
            "id": self.id,
            "hotel_id": self.hotel_id,
            "room_id": self.room_id,
            "unit_id": self.unit_id,
            "lock_id": self.lock_id,
        }