from db.mongo import db
def list_suppliers_by_service(collection: str, service_type: str):
    return list(db[collection].find({'service_type': service_type}, {'_id':0}))
