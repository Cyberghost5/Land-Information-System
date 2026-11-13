from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user' or 'admin'
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_parcels = db.relationship('SavedParcel', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'role': self.role,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Parcel(db.Model):
    __tablename__ = 'parcels'

    id = db.Column(db.Integer, primary_key=True)
    parcel_id = db.Column(db.String(80), unique=True, nullable=False, index=True)
    owner = db.Column(db.String(150), nullable=True)
    landuse = db.Column(db.String(80), nullable=True)
    area = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), nullable=True, default='Unverified')
    location = db.Column(db.String(100), nullable=True)
    lga = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(80), nullable=True, default='Ogun')
    country = db.Column(db.String(80), nullable=True, default='Nigeria')
    title_number = db.Column(db.String(100), nullable=True)
    survey_plan = db.Column(db.String(100), nullable=True)
    rec_date = db.Column(db.String(50), nullable=True)
    properties_json = db.Column(db.Text, nullable=True)   # JSON string of all feature properties
    geometry_json = db.Column(db.Text, nullable=False)     # GeoJSON geometry dictionary string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_properties(self):
        if self.properties_json:
            try:
                return json.loads(self.properties_json)
            except Exception:
                pass
        return {
            'Parcel_ID': self.parcel_id,
            'Par_Owner': self.owner,
            'landuse': self.landuse,
            'Area': self.area,
            'Status': self.status,
            'Location': self.location,
            'LGA': self.lga,
            'State': self.state,
            'Country': self.country,
            'Title_numb': self.title_number,
            'Surv_plan': self.survey_plan,
            'Rec_date': self.rec_date
        }

    def get_geometry(self):
        try:
            return json.loads(self.geometry_json)
        except Exception:
            return {}

    def to_geojson_feature(self):
        return {
            'type': 'Feature',
            'properties': self.get_properties(),
            'geometry': self.get_geometry()
        }


class SavedParcel(db.Model):
    __tablename__ = 'saved_parcels'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    parcel_id = db.Column(db.String(80), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'parcel_id', name='uq_user_parcel'),
    )

    @property
    def parcel(self):
        return Parcel.query.filter(db.func.lower(Parcel.parcel_id) == self.parcel_id.lower()).first()

    def to_dict(self):
        # Fetch parcel info if available
        parcel = Parcel.query.filter_by(parcel_id=self.parcel_id).first()
        return {
            'id': self.id,
            'user_id': self.user_id,
            'parcel_id': self.parcel_id,
            'notes': self.notes,
            'saved_at': self.saved_at.strftime('%Y-%m-%d %H:%M:%S') if self.saved_at else '',
            'parcel_details': parcel.get_properties() if parcel else None
        }
