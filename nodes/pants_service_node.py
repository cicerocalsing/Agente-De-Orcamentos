from nodes.service_common import list_suppliers_by_service
class PantsServiceNode:
    def run(self, task: dict) -> dict:
        suppliers=list_suppliers_by_service('suppliers_pants', task.get('service_type'))
        return {'task': task, 'suppliers': suppliers}
