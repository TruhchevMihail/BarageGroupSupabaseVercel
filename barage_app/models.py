from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from barage_app.constants import ROLE_LABELS, STATUS_WAREHOUSE
from barage_app.extensions import db


location_technicians = db.Table(
    'location_technicians',
    db.Column('location_id', db.Integer, db.ForeignKey('location.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, index=True)
    assigned_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), index=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    is_active = db.Column(db.Boolean, default=True)
    phone_number = db.Column(db.String(20), nullable=True)

    assigned_location = db.relationship('Location', foreign_keys=[assigned_location_id])
    subordinates = db.relationship('User', backref=db.backref('manager', remote_side=[id]))

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str):
        return check_password_hash(self.password_hash, raw_password)

    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role)

    def __str__(self):
        return self.full_name

    def can_manage_user(self, target):
        from barage_app.routes import can_manage_user

        return can_manage_user(self, target)


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    type = db.Column(db.String(30), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    city = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    gps_location = db.Column(db.String(100), nullable=True)
    courier_locations = db.Column(db.String(255), nullable=True)
    technicians = db.relationship('User', secondary=location_technicians, backref='managed_locations')
    technical_lead_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', name='fk_location_technical_lead_id_user', use_alter=True),
        nullable=True,
    )
    technical_lead = db.relationship('User', foreign_keys=[technical_lead_id])

    def __str__(self):
        return self.name


class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    asset_type = db.Column(db.String(30), nullable=True, default='Машина', index=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), nullable=True)
    alias_name = db.Column(db.String(120), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    invoice_number = db.Column(db.String(100), nullable=True)
    company_name = db.Column(db.String(150), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True, index=True)
    supplier_company = db.Column(db.String(150), nullable=True)
    warranty = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default=STATUS_WAREHOUSE, index=True)
    condition = db.Column(db.String(50), nullable=False, default='Работи', index=True)
    current_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), index=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_moved_at = db.Column(db.DateTime, nullable=True, index=True)

    current_location = db.relationship('Location', foreign_keys=[current_location_id])
    responsible_user = db.relationship('User', foreign_keys=[responsible_user_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    images = db.relationship('AssetImage', backref='asset', cascade='all, delete-orphan', order_by='AssetImage.created_at.asc()')

    def __str__(self):
        return f'{self.inventory_number} / {self.name}'


class AssetImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class TransferRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False, index=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False, index=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False, index=True)
    request_type = db.Column(db.String(30), nullable=False, default='transfer')
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='pending', index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    processed_at = db.Column(db.DateTime, nullable=True)

    asset = db.relationship('Asset')
    from_location = db.relationship('Location', foreign_keys=[from_location_id])
    to_location = db.relationship('Location', foreign_keys=[to_location_id])
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])


class AssetHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False, index=True)
    action = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, nullable=False)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    asset = db.relationship('Asset')
    performed_by = db.relationship('User')


class AssetServiceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False, index=True)
    service_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    problem = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text, nullable=False)
    service_provider = db.Column(db.String(150), nullable=True)
    price = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    attachment_url = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    asset = db.relationship('Asset')
    created_by = db.relationship('User')
