# Ogun Land Administration System (OLAS)

An institutional-grade, full-stack Land Information System (LIS) and digital Cadastral Registry built with **Python (Flask)**, **SQLite / SQLAlchemy**, and **Leaflet.js**, featuring role-based access control, SMTP email verification, user impersonation, spatial boundary queries, personal property portfolios, and administrative cadastral CRUD/import operations.

---

## 🌟 Key Capabilities

### 1. Institutional Landing Page
- Public portal welcoming citizens and professionals to the **Ogun Land Administration System (OLAS)**.
- Showcases cadastral statistics (157+ parcels, UTM Zone 31N high accuracy geometries, verified title registries).
- Overview of institutional spatial infrastructure, citizen workflow guides, and instant login/register CTAs.

### 2. Multi-Tiered Authentication & SMTP Verification
- **Dual Roles**: Standard **User (Citizen)** and **Administrator**.
- **Citizen Registration**: Captures Full Name, Email Address, Phone Number, Residential/Office Address, and secure Password.
- **SMTP Email Verification**: Generates a 24-hour tokenized confirmation link sent via SMTP. Unverified accounts cannot log in or access spatial data.
- **Development Fallback**: In local/dev environments, activation links are automatically logged to the terminal and rendered in a testing shortcut box so verification is instantaneous.
- **Session Security**: Password hashing with PBKDF2/SHA256 (`werkzeug.security`) and role-based route decorators (`@login_required`, `@verified_required`, `@admin_required`).

### 3. User Portal: Isolated Cadastral Map
- **Clean Starting Map**: The map loads with standard OpenStreetMap tiles centered on Abeokuta with **no pre-loaded parcels** and **no clickable layers** on start.
- **Isolated Spatial Querying**: Dedicated search input with **no autocomplete or suggestions** (`autocomplete="off"`). Only explicitly searched parcels are rendered and highlighted on the map.
- **Smooth Navigation**: Camera automatically glides (`flyToBounds`) directly to the parcel extent and opens a comprehensive attribute inspector.
- **On-the-Fly Reprojection**: Recursively reprojects coordinates from **EPSG:32631 (UTM Zone 31N)** to **EPSG:4326 (WGS84)** for pinpoint spatial alignment.

### 4. Personal Saved Parcels Portfolio
- **One-Click Bookmarking**: Directly save any inspected parcel to your account portfolio.
- **Portfolio Management (`/saved-parcels`)**: Dedicated page listing all saved parcels, surveyed areas, owners, land use, and title numbers.
- **Direct Map Deep-Linking**: "View on Map" links open `/map?parcel_id=<id>` to instantly render and zoom to that property.
- **AJAX Removal**: Easily remove bookmarks with instant card fade-out.

### 5. Administrator Governance & Cadastral Operations
- **System Dashboard (`/admin`)**: Real-time counters for registered users, parcels, and bookmarks.
- **User Directory**: View all citizen records, phone numbers, addresses, and verification statuses.
- **Live User Impersonation**: One-click impersonation allows administrators to view the system through any citizen's perspective, with a persistent red banner to safely return to the admin console.
- **Role Assignment**: Promote citizens to administrators or adjust privileges with safeguard preventing self-demotion.
- **Cadastral CRUD**: Add new parcels (with custom GeoJSON geometry), edit existing attributes, and delete parcels.
- **Bulk GeoJSON Importer**: Upload `.geojson` or `.json` FeatureCollection datasets to ingest or update hundreds of cadastral boundaries in one batch.

---

## 🔑 Default Administrator Credentials

Upon first startup, the database automatically seeds the initial administrator account:

* **Email**: `admin@ogunland.gov.ng`
* **Password**: `Admin123!`
* **Role**: `admin` (pre-verified)

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- `pip` package manager

### 2. Installation
```bash
git clone https://github.com/Cyberghost5/Land-Information-System.git
cd Land-Information-System
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional for SMTP)
Create a `.env` file in the project root to configure live email dispatching (optional; if omitted, dev console fallback is used automatically):
```ini
SECRET_KEY=your-super-secret-key-2026
DATABASE_URL=sqlite:///lis.db

# Live SMTP Configuration (e.g. Gmail / SendGrid / Custom Mail Server)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@ogunland.gov.ng
```

### 4. Start the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📡 REST API Reference

| Endpoint | Method | Access | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Institutional Landing Page |
| `/register` | `GET`, `POST` | Public | Citizen registration form |
| `/verify-email/<token>` | `GET` | Public | Tokenized email verification activation |
| `/login` | `GET`, `POST` | Public | User and administrator sign-in |
| `/logout` | `GET` | Authenticated | Clears active session |
| `/map` | `GET` | Verified User | Clean, isolated cadastral map |
| `/saved-parcels` | `GET` | Verified User | Portfolio of saved property bookmarks |
| `/api/parcels/search/<id>` | `GET` | Verified User | Queries single parcel; returns GeoJSON with `is_saved` flag |
| `/api/parcels/save` | `POST` | Verified User | Bookmarks a parcel to the user's portfolio |
| `/api/parcels/saved/<id>` | `DELETE` | Verified User | Removes a parcel from the user's saved list |
| `/admin` | `GET` | Administrator | Management console (Users, Parcels, Importer) |
| `/admin/impersonate/<id>` | `POST` | Administrator | Impersonates a target user session |
| `/admin/stop-impersonating`| `POST` | Authenticated | Restores the original administrator session |
| `/admin/parcels/add` | `POST` | Administrator | Adds a new parcel record with geometry |
| `/admin/parcels/edit/<id>` | `POST` | Administrator | Updates parcel attributes and geometry |
| `/admin/parcels/delete/<id>`| `POST` | Administrator | Deletes a parcel from the registry |
| `/admin/parcels/import` | `POST` | Administrator | Bulk-imports a GeoJSON dataset |
| `/admin/users/toggle-role/<id>`| `POST` | Administrator | Toggles user role between user and admin |

---

## 📁 Project Architecture

```
├── app.py                      # Core Flask application, routing & API endpoints
├── models.py                   # SQLAlchemy models (User, Parcel, SavedParcel)
├── auth.py                     # Session helpers, decorators & impersonation logic
├── email_utils.py              # ItsDangerous tokenization & dual-mode SMTP dispatcher
├── seed.py                     # Initial database seeder (Admin & 157 Cadastral Parcels)
├── output_file.geojson         # Cadastral spatial dataset (EPSG:32631 UTM Zone 31N)
├── requirements.txt            # Python dependencies
├── templates/
│   ├── base.html               # Institutional layout with role-aware navbar & impersonation bar
│   ├── landing.html            # Public welcome landing page
│   ├── map.html                # Isolated user map (no pre-loaded parcels, no suggestions)
│   ├── saved_parcels.html      # Personal property portfolio
│   ├── auth/
│   │   ├── register.html       # Citizen sign-up (Full Name, Email, Phone, Address, Password)
│   │   ├── login.html          # Authentication form
│   │   ├── verification_pending.html  # Email dispatch notice with dev link helper
│   │   └── resend_verification.html   # Self-service resend activation token form
│   └── admin/
│       └── dashboard.html      # Comprehensive admin console (Users, Impersonate, CRUD, Import)
└── README.md                   # System documentation
```
