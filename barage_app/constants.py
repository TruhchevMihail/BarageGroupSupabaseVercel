ROLE_USER = 'user'
ROLE_WAREHOUSE_WORKER = 'warehouse_worker'
ROLE_USER_PLUS = 'user_plus'
ROLE_SUPERUSER = 'superuser'
FIELD_ROLES = (ROLE_USER, ROLE_WAREHOUSE_WORKER)
OPERATIONAL_TEAM_ROLES = (ROLE_USER, ROLE_WAREHOUSE_WORKER, ROLE_USER_PLUS, ROLE_SUPERUSER)
ROLE_LABELS = {
    ROLE_USER: 'Технически ръководител',
    ROLE_WAREHOUSE_WORKER: 'Складов работник',
    ROLE_USER_PLUS: 'Проектов ръководител',
    ROLE_SUPERUSER: 'Администратор',
}

LOC_WAREHOUSE = 'warehouse'
LOC_SITE = 'site'
LOC_SERVICE = 'service'
LOC_SCRAP = 'scrap'

STATUS_WAREHOUSE = 'В склад'
STATUS_SITE = 'На обект'
STATUS_SERVICE = 'В сервиз'
STATUS_SCRAP = 'Брак'
STATUS_PENDING = 'Чака одобрение'

ROLE_META = {
    ROLE_USER: {'label': ROLE_LABELS[ROLE_USER], 'chip': 'chip-role-tech'},
    ROLE_WAREHOUSE_WORKER: {'label': ROLE_LABELS[ROLE_WAREHOUSE_WORKER], 'chip': 'chip-role-warehouse'},
    ROLE_USER_PLUS: {'label': ROLE_LABELS[ROLE_USER_PLUS], 'chip': 'chip-role-lead'},
    ROLE_SUPERUSER: {'label': ROLE_LABELS[ROLE_SUPERUSER], 'chip': 'chip-role-admin'},
}

MULTI_LOCATION_ROLES = (ROLE_USER_PLUS, ROLE_SUPERUSER)

LOCATION_META = {
    LOC_WAREHOUSE: {'label': 'Склад', 'icon': '🏭', 'chip': 'chip-warehouse'},
    LOC_SITE: {'label': 'Обект', 'icon': '🏗️', 'chip': 'chip-site'},
    LOC_SERVICE: {'label': 'Сервиз', 'icon': '🔧', 'chip': 'chip-repair'},
    LOC_SCRAP: {'label': 'Брак', 'icon': '♻️', 'chip': 'chip-scrap'},
}

LOCATION_MINIMAL_TYPES = {LOC_SERVICE, LOC_SCRAP}
LOCATION_NO_LEAD_TYPES = {LOC_WAREHOUSE}

STATUS_META = {
    STATUS_WAREHOUSE: {'chip': 'chip-warehouse'},
    STATUS_SITE: {'chip': 'chip-site'},
    STATUS_SERVICE: {'chip': 'chip-repair'},
    STATUS_SCRAP: {'chip': 'chip-scrap'},
    STATUS_PENDING: {'chip': 'chip-pending'},
}

STATUS_TO_LOCATION_TYPE = {
    STATUS_WAREHOUSE: LOC_WAREHOUSE,
    STATUS_SITE: LOC_SITE,
    STATUS_SERVICE: LOC_SERVICE,
    STATUS_SCRAP: LOC_SCRAP,
    'Склад': LOC_WAREHOUSE,
    'Обект': LOC_SITE,
    'Сервиз': LOC_SERVICE,
}

LOCATION_TYPE_TO_STATUS = {
    LOC_WAREHOUSE: STATUS_WAREHOUSE,
    LOC_SITE: STATUS_SITE,
    LOC_SERVICE: STATUS_SERVICE,
    LOC_SCRAP: STATUS_SCRAP,
}

REQUEST_STATUS_META = {
    'pending': {'label': 'Чакаща', 'chip': 'chip-pending'},
    'approved': {'label': 'Одобрена', 'chip': 'chip-approved'},
    'rejected': {'label': 'Отказана', 'chip': 'chip-rejected'},
}

ACTION_LABELS = {
    'asset_created': 'Добавяне',
    'asset_updated': 'Редакция',
    'asset_transferred': 'Преместване',
    'asset_status_changed': 'Статус',
    'asset_service_added': 'Добавен сервизен запис',
    'asset_returned_from_scrap': 'Върната от брак',
    'request_created': 'Заявка',
    'request_approved': 'Одобрение',
    'request_rejected': 'Отказ',
    'service_added': 'Добавен сервизен запис',
    'service_updated': 'Редактиран сервизен запис',
    'service_deleted': 'Изтрит сервизен запис',
}

ASSET_TYPE_OPTIONS = [
    'Машина',
    'Инструмент',
    'Оборудване',
    'Комплект',
    'Друго',
]

ASSET_STATUS_OPTIONS = [
    'В склад',
    'На обект',
    'В сервиз',
    'За ремонт',
    'Брак',
    'Липсва',
    'Откраднат',
    'Архивиран',
]

ASSET_CONDITION_OPTIONS = [
    'Работи',
    'Има забележки',
    'За ремонт',
    'Неизправен',
    'Бракуван',
    'Липсващ',
    'Откраднат',
]
