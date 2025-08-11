from datetime import datetime

from db.mongo import db

def _brl(v):
    try:
        return ('R$' + '{:,.2f}'.format(float(v))).replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return f'R${v}'

def _ddmmyyyy(s):
    try:
        return datetime.fromisoformat(s).strftime('%d/%m/%Y')
    except:
        return s or '-'

class BudgetGeneratorNode:
    def run(self, data: dict) -> dict:
        offers = data.get('offers', [])
        task = data.get('task', {})

        intro = 'Olá! Seguem as opções que atendem ao seu pedido:'
        lines = []
        for o in offers:
            parts = [o.get('name', 'Fornecedor')]
            if o.get('price') is not None:
                parts.append(f'Preço: {_brl(o["price"])}')
            if task.get('desired_date'):
                parts.append(f'Data: {_ddmmyyyy(task["desired_date"])}')
            if task.get('time_window'):
                parts.append({'morning': 'pela manhã', 'afternoon': 'à tarde', 'evening': 'à noite'}.get(task['time_window'], ''))
            if o.get('notes'):
                parts.append(f'Obs: {o["notes"]}')
            lines.append('- ' + ' • '.join([p for p in parts if p]))

        outro = 'Deseja seguir com alguma dessas opções ou quer que eu verifique mais fornecedores?'
        full_message = intro + '\n\n' + '\n'.join(lines) + '\n\n' + outro

        try:
            db.quotes.insert_one({
                "run_id": task.get("run_id"),
                "created_at": datetime.utcnow(),
                "task": task,
                "offers": offers,
                "message": full_message
            })
        except Exception:
            pass

        return {'message': full_message}
