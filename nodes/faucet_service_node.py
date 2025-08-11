from nodes.service_common import list_suppliers_by_service
class FaucetServiceNode:
    def run(self, task: dict) -> dict:
        suppliers=list_suppliers_by_service('suppliers_faucet', task.get('service_type'))
        return {'task': task, 'suppliers': suppliers}
