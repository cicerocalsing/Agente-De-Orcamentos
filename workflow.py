from langgraph.graph import StateGraph, START, END
from nodes.classifier_node import ClassifierNode
from nodes.manual_normalizer_node import ManualNormalizerNode
from nodes.clothing_normalizer_node import ClothingNormalizerNode
from nodes.faucet_service_node import FaucetServiceNode
from nodes.tshirt_service_node import TshirtServiceNode
from nodes.pants_service_node import PantsServiceNode

def build_workflow():
    g=StateGraph(dict)
    classifier=ClassifierNode(); mnorm=ManualNormalizerNode(); cnorm=ClothingNormalizerNode()
    faucet=FaucetServiceNode(); tshirt=TshirtServiceNode(); pants=PantsServiceNode()
    
    def klass(state): 
        out=classifier.run(state['task_text']); out['task_text']=state['task_text']
        if 'current_date' in state: out['current_date']=state['current_date']
        return out
    def mfn(state): return {'normalized_task': mnorm.run(state['original_task'], state.get('current_date'))}
    def cfn(state): return {'normalized_task': cnorm.run(state['original_task'], state.get('current_date'))}
    def ffn(state): out=faucet.run(state['normalized_task']); return {'task':out['task'],'suppliers':out['suppliers']}
    def tfn(state): out=tshirt.run(state['normalized_task']); return {'task':out['task'],'suppliers':out['suppliers']}
    def pfn(state): out=pants.run(state['normalized_task']); return {'task':out['task'],'suppliers':out['suppliers']}
    g.add_node('classifier', klass); g.add_node('manual_normalizer', mfn); g.add_node('clothing_normalizer', cfn)
    g.add_node('faucet_service', ffn); g.add_node('tshirt_service', tfn); g.add_node('pants_service', pfn)
    g.add_edge(START,'classifier')
    g.add_conditional_edges('classifier', lambda s: s.get('category','manual_process'),
        {'manual_process':'manual_normalizer','clothing':'clothing_normalizer'})
    g.add_conditional_edges('manual_normalizer', lambda s: (s.get('normalized_task') or {}).get('service_type'),
        {'faucet_repair':'faucet_service'})
    g.add_conditional_edges('clothing_normalizer', lambda s: (s.get('normalized_task') or {}).get('service_type'),
        {'tshirt_sale':'tshirt_service','pants_sale':'pants_service'})
    return g.compile()
