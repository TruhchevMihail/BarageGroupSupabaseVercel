-- Supabase/Postgres schema for Machinery Barage Group
-- Run in Supabase SQL Editor only for a fresh, empty project/schema.
-- For existing deployments prefer Alembic: flask --app app.py db upgrade.

CREATE TABLE "user" (
	id SERIAL NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(30) NOT NULL, 
	assigned_location_id INTEGER, 
	manager_id INTEGER, 
	is_active BOOLEAN, 
	phone_number VARCHAR(20), 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE INDEX ix_user_manager_id ON "user" (manager_id);

CREATE INDEX ix_user_role ON "user" (role);

CREATE INDEX ix_user_assigned_location_id ON "user" (assigned_location_id);

CREATE TABLE location (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	type VARCHAR(30) NOT NULL, 
	is_active BOOLEAN, 
	city VARCHAR(100), 
	address VARCHAR(255), 
	gps_location VARCHAR(100), 
	courier_locations VARCHAR(255), 
	technical_lead_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE INDEX ix_location_type ON location (type);

CREATE TABLE location_technicians (
	location_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	PRIMARY KEY (location_id, user_id), 
	FOREIGN KEY(location_id) REFERENCES location (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

CREATE TABLE asset (
	id SERIAL NOT NULL, 
	inventory_number VARCHAR(50) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(100), 
	asset_type VARCHAR(30), 
	brand VARCHAR(100) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	serial_number VARCHAR(100), 
	alias_name VARCHAR(120), 
	image_url VARCHAR(255), 
	invoice_number VARCHAR(100), 
	company_name VARCHAR(150), 
	purchase_date DATE, 
	supplier_company VARCHAR(150), 
	warranty VARCHAR(150), 
	notes TEXT, 
	status VARCHAR(50) NOT NULL, 
	condition VARCHAR(50) NOT NULL, 
	current_location_id INTEGER, 
	responsible_user_id INTEGER, 
	created_by_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	last_moved_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (inventory_number), 
	FOREIGN KEY(current_location_id) REFERENCES location (id), 
	FOREIGN KEY(responsible_user_id) REFERENCES "user" (id), 
	FOREIGN KEY(created_by_id) REFERENCES "user" (id)
);

CREATE INDEX ix_asset_responsible_user_id ON asset (responsible_user_id);

CREATE INDEX ix_asset_condition ON asset (condition);

CREATE INDEX ix_asset_created_at ON asset (created_at);

CREATE INDEX ix_asset_asset_type ON asset (asset_type);

CREATE INDEX ix_asset_last_moved_at ON asset (last_moved_at);

CREATE INDEX ix_asset_status ON asset (status);

CREATE INDEX ix_asset_current_location_id ON asset (current_location_id);

CREATE INDEX ix_asset_purchase_date ON asset (purchase_date);

CREATE INDEX ix_asset_created_by_id ON asset (created_by_id);

CREATE TABLE asset_image (
	id SERIAL NOT NULL, 
	asset_id INTEGER NOT NULL, 
	file_path VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES asset (id)
);

CREATE INDEX ix_asset_image_asset_id ON asset_image (asset_id);

CREATE INDEX ix_asset_image_created_at ON asset_image (created_at);

CREATE TABLE transfer_request (
	id SERIAL NOT NULL, 
	asset_id INTEGER NOT NULL, 
	from_location_id INTEGER NOT NULL, 
	to_location_id INTEGER NOT NULL, 
	request_type VARCHAR(30) NOT NULL, 
	reason TEXT, 
	status VARCHAR(30) NOT NULL, 
	requested_by_id INTEGER NOT NULL, 
	approved_by_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	processed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES asset (id), 
	FOREIGN KEY(from_location_id) REFERENCES location (id), 
	FOREIGN KEY(to_location_id) REFERENCES location (id), 
	FOREIGN KEY(requested_by_id) REFERENCES "user" (id), 
	FOREIGN KEY(approved_by_id) REFERENCES "user" (id)
);

CREATE INDEX ix_transfer_request_to_location_id ON transfer_request (to_location_id);

CREATE INDEX ix_transfer_request_asset_id ON transfer_request (asset_id);

CREATE INDEX ix_transfer_request_status ON transfer_request (status);

CREATE INDEX ix_transfer_request_from_location_id ON transfer_request (from_location_id);

CREATE INDEX ix_transfer_request_created_at ON transfer_request (created_at);

CREATE INDEX ix_transfer_request_approved_by_id ON transfer_request (approved_by_id);

CREATE INDEX ix_transfer_request_requested_by_id ON transfer_request (requested_by_id);

CREATE TABLE asset_history (
	id SERIAL NOT NULL, 
	asset_id INTEGER NOT NULL, 
	action VARCHAR(120) NOT NULL, 
	details TEXT NOT NULL, 
	performed_by_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES asset (id), 
	FOREIGN KEY(performed_by_id) REFERENCES "user" (id)
);

CREATE INDEX ix_asset_history_performed_by_id ON asset_history (performed_by_id);

CREATE INDEX ix_asset_history_created_at ON asset_history (created_at);

CREATE INDEX ix_asset_history_asset_id ON asset_history (asset_id);

CREATE TABLE asset_service_record (
	id SERIAL NOT NULL, 
	asset_id INTEGER NOT NULL, 
	service_date TIMESTAMP WITHOUT TIME ZONE, 
	problem TEXT NOT NULL, 
	action_taken TEXT NOT NULL, 
	service_provider VARCHAR(150), 
	price VARCHAR(50), 
	notes TEXT, 
	attachment_url VARCHAR(255), 
	created_by_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES asset (id), 
	FOREIGN KEY(created_by_id) REFERENCES "user" (id)
);

CREATE INDEX ix_asset_service_record_service_date ON asset_service_record (service_date);

CREATE INDEX ix_asset_service_record_created_at ON asset_service_record (created_at);

CREATE INDEX ix_asset_service_record_asset_id ON asset_service_record (asset_id);

ALTER TABLE "user" ADD FOREIGN KEY(assigned_location_id) REFERENCES location (id);

ALTER TABLE "user" ADD FOREIGN KEY(manager_id) REFERENCES "user" (id);

ALTER TABLE location ADD FOREIGN KEY(technical_lead_id) REFERENCES "user" (id);
