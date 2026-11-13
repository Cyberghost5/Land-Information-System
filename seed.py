import os
import json
from models import db, User, Parcel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_PATH = os.path.join(BASE_DIR, 'output_file.geojson')

def seed_database(app):
    """Initializes tables and seeds default admin and cadastral parcel data."""
    with app.app_context():
        db.create_all()

        # 1. Seed Default Administrator if none exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@ogunland.gov.ng')
            admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'Admin123!')
            
            admin_user = User(
                full_name="Bureau Administrator",
                email=admin_email,
                phone="+2348030000000",
                address="Bureau of Lands & Survey, Oke-Mosan, Abeokuta, Ogun State",
                role="admin",
                is_verified=True
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"[DB INIT] Default administrator created: {admin_email} (Password: {admin_password})")

        # 2. Seed Cadastral Parcels from output_file.geojson if table is empty
        parcel_count = Parcel.query.count()
        if parcel_count == 0 and os.path.exists(GEOJSON_PATH):
            try:
                with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                features = data.get('features', [])
                parcels_to_add = []
                for feat in features:
                    props = feat.get('properties', {})
                    geom = feat.get('geometry', {})
                    pid = props.get('Parcel_ID')
                    if not pid:
                        continue
                    
                    p = Parcel(
                        parcel_id=str(pid).strip(),
                        owner=props.get('Par_Owner'),
                        landuse=props.get('landuse'),
                        area=props.get('Area'),
                        status=props.get('Status', 'Unverified'),
                        location=props.get('Location', 'Abeokuta'),
                        lga=props.get('LGA', 'Abeokuta South'),
                        state=props.get('State', 'Ogun'),
                        country=props.get('Country', 'Nigeria'),
                        title_number=props.get('Title_numb'),
                        survey_plan=props.get('Surv_plan'),
                        rec_date=props.get('Rec_date'),
                        properties_json=json.dumps(props),
                        geometry_json=json.dumps(geom)
                    )
                    parcels_to_add.append(p)

                db.session.bulk_save_objects(parcels_to_add)
                db.session.commit()
                print(f"[DB INIT] Successfully seeded {len(parcels_to_add)} cadastral parcels from {GEOJSON_PATH}")
            except Exception as e:
                db.session.rollback()
                print(f"[DB INIT ERROR] Failed to seed parcels: {e}")
