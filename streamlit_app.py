import uuid
import streamlit as st
from datetime import date
from workflow import build_workflow
from nodes.supplier_question_node import SupplierQuestionNode
from nodes.supplier_answer_parser_node import SupplierAnswerParserNode
from nodes.budget_generator_node import BudgetGeneratorNode

st.set_page_config(page_title="Intelligent Quotation System", page_icon="🧠")
st.title("🧠 Intelligent Quotation System")

if "graph" not in st.session_state:
    st.session_state.graph = build_workflow()
if "phase" not in st.session_state:
    st.session_state.phase = "form"
if "queue" not in st.session_state:
    st.session_state.queue = []
if "offers" not in st.session_state:
    st.session_state.offers = []
if "task" not in st.session_state:
    st.session_state.task = {}
if "current_supplier" not in st.session_state:
    st.session_state.current_supplier = None
if "generated_question" not in st.session_state:
    st.session_state.generated_question = ""
if "answer_key" not in st.session_state:
    st.session_state.answer_key = 0
if "run_id" not in st.session_state:
    st.session_state.run_id = None

qnode = SupplierQuestionNode()
anode = SupplierAnswerParserNode()
bnode = BudgetGeneratorNode()

def start_flow(task_text: str):
    today = date.today().isoformat()
    res = st.session_state.graph.invoke({"task_text": task_text, "current_date": today})

    st.session_state.run_id = str(uuid.uuid4())

    st.session_state.task = res.get("task") or res.get("normalized_task") or {}
    st.session_state.task["run_id"] = st.session_state.run_id
    st.session_state.task["current_date"] = today

    st.session_state.queue = res.get("suppliers", [])
    st.session_state.offers = []
    st.session_state.current_supplier = None
    st.session_state.generated_question = ""
    st.session_state.answer_key += 1          
    st.session_state.phase = "supplier_chat"

with st.form("form"):
    task_text = st.text_area("Describe your task:", key="task_input", placeholder="Escreva em PT mesmo :)")
    submitted = st.form_submit_button("Generate quotation")
if submitted and task_text.strip():
    start_flow(task_text.strip())

def ensure_current():
    if st.session_state.current_supplier is None and st.session_state.queue:
        st.session_state.current_supplier = st.session_state.queue.pop(0)
        st.session_state.generated_question = qnode.run(st.session_state.task, st.session_state.current_supplier)
        st.session_state.answer_key += 1       

if st.session_state.phase == "supplier_chat":
    st.subheader("Contato com fornecedores")
    ensure_current()
    sup = st.session_state.current_supplier

    if not sup:
        st.info("Fila de fornecedores esgotada.")
        st.session_state.phase = "budget"
    else:
        st.markdown(f"**Supplier:** {sup.get('name')} — {sup.get('location','-')} (id: {sup.get('id','-')})")
        st.write(f"Pergunta: \"{st.session_state.generated_question}\"")

        answer_widget_key = f"supplier_answer_{st.session_state.answer_key}"
        st.text_input("Resposta do fornecedor:", key=answer_widget_key)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Enviar resposta"):
                answer = (st.session_state.get(answer_widget_key) or "").strip()
                out = anode.run(st.session_state.task, sup, answer)
                if out.get("accepted") and out.get("offer"):
                    st.session_state.offers.append(out["offer"])
                    st.success("Fornecedor aceito.")
                else:
                    st.info("Fornecedor não atende ou não forneceu preço.")
                st.session_state.current_supplier = None
                st.session_state.generated_question = ""
                if len(st.session_state.offers) >= 3 or not st.session_state.queue:
                    st.session_state.phase = "budget"
                st.rerun()

        with c2:
            if st.button("Pular fornecedor"):
                st.session_state.current_supplier = None
                st.session_state.generated_question = ""
                st.rerun()

        with c3:
            if st.button("Encerrar e gerar orçamento"):
                st.session_state.phase = "budget"
                st.rerun()

if st.session_state.phase == "budget":
    result = bnode.run({"offers": st.session_state.offers, "task": st.session_state.task})
    st.markdown(result.get("message", ""))
