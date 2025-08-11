import json
from db.mongo import db
def seed():
    with open('data/suppliers_seed.json','r',encoding='utf-8') as f:
        payload=json.load(f)
    for col in ['suppliers_faucet','suppliers_tshirt','suppliers_pants']:
        db[col].delete_many({})
        db[col].insert_many(payload[col])
    print('✅ Seed data inserted.')
if __name__=='__main__': seed()
