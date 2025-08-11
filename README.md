# 🧠 Intelligent Quotation System

Sistema de orçamentos inteligente com **Streamlit**, **LangGraph**, **LangChain (Ollama)** e **MongoDB**.  
Ele recebe uma descrição do pedido (ex.: *“Quero uma camisa GG preta para quinta”* ou *“Minha torneira está pingando, consegue amanhã de manhã?”*), classifica o tipo de serviço, normaliza as informações necessárias, **contata fornecedores**, interpreta as respostas e **gera um orçamento consolidado**. As **ofertas aceitas** e o **orçamento final** são salvos no MongoDB para consulta no **MongoDB Compass**.

---

## ✨ Principais recursos

- UI em **Streamlit** com fluxo guiado.
- **Classificação** automática do pedido: *manual_process* (ex.: encanador) ou *clothing* (camiseta/calça).
- **Normalização** do pedido (datas, janela de tempo, cor/tamanho para roupas, etc.).
- **Pergunta automática ao fornecedor** (determinística para torneira; LLM com fallback para roupas).
- **Parser** da resposta do fornecedor (aceita, preço, compatibilidade com data/turno, observações).
- **Geração do orçamento** em linguagem natural.
- **Persistência no MongoDB**:
  - `offers`: cada oferta **aceita** por fornecedor.
  - `quotes`: o **orçamento final** consolidado.
- **Seeds** com fornecedores de exemplo para torneiras/camisetas/calças.

---

## 🧱 Arquitetura (alto nível)

```
workflow.py (LangGraph)
└─ ClassifierNode
   ├─ ManualNormalizerNode ──> FaucetServiceNode ──> suppliers_faucet
   └─ ClothingNormalizerNode ─> TshirtServiceNode ─> suppliers_tshirt
                             └> PantsServiceNode ──> suppliers_pants

Durante o chat com fornecedor (Streamlit UI):
SupplierQuestionNode  -> gera pergunta
SupplierAnswerParserNode -> avalia resposta (aceite/preço/data) e salva 'offers' se aceito
BudgetGeneratorNode -> monta texto final e salva 'quotes'
```

### Nós principais
- `ClassifierNode`: decide entre **manual_process** e **clothing** (heurística + LLM restrita).
- `ManualNormalizerNode`: extrai `service_type=faucet_repair`, descrição, *desired_date*, *time_window*.
- `ClothingNormalizerNode`: extrai `service_type` (*tshirt_sale* ou *pants_sale*), `color`, `size`, `desired_date`.  
  - **Robusto** contra erros de LLM: usa **regex** de segurança para tamanhos (ex.: **GG**) e cores (ex.: **preta**), e normaliza `preto→preta`, `branco→branca`.
- `*ServiceNode`: carrega fornecedores da coleção Mongo correspondente.
- `SupplierQuestionNode`: pergunta para o fornecedor (determinística para torneira; LLM com fallback para roupas).
- `SupplierAnswerParserNode`: interpreta JSON da LLM, valida preço e data; **salva ofertas aceitas** em `offers`.
- `BudgetGeneratorNode`: gera mensagem final e **salva orçamento** em `quotes`.

---

## 📁 Estrutura do projeto (sugerida)

```
.
├─ streamlit_app.py
├─ workflow.py
├─ llm_client.py
├─ seed_db.py
├─ data/
│  └─ suppliers_seed.json
├─ db/
│  ├─ __init__.py
│  └─ mongo.py
└─ nodes/
   ├─ classifier_node.py
   ├─ manual_normalizer_node.py
   ├─ clothing_normalizer_node.py
   ├─ faucet_service_node.py
   ├─ tshirt_service_node.py
   ├─ pants_service_node.py
   ├─ supplier_question_node.py
   ├─ supplier_answer_parser_node.py
   ├─ supplier_followup_node.py
   └─ service_common.py
```

---

## 🔧 Pré‑requisitos

- **Python** 3.10+
- **MongoDB** (local ou remoto) — recomendado local para testes
- **Ollama** rodando localmente com um modelo de chat (ex.: `llama3`)  
  > Após instalar, rode `ollama run llama3` uma vez para baixar o modelo.

---

## ⚙️ Configuração

1. **Crie o arquivo `.env` na raiz**:

```
# Mongo
MONGO_URI=mongodb://localhost:27017
MONGO_DB=quote_system_db

# Ollama / LangChain
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
```

2. **Instale as dependências** (exemplo):
```bash
pip install -r requirements.txt
```
> Se preferir sem arquivo: `pip install streamlit pymongo python-dotenv langgraph langchain-community langchain-core`

3. **Suba o MongoDB**:
- Via serviço (Windows): abra *Services* e inicie **MongoDB** (ou `net start MongoDB`).
- Via terminal: `mongod --dbpath "C:\caminho\para\data\db"`

4. **Popule fornecedores** (seeds):
```bash
python seed_db.py
```
Cria o DB **`quote_system_db`** e insere docs em:
`suppliers_faucet`, `suppliers_tshirt`, `suppliers_pants`.

5. **(Opcional) Índices úteis**:
```javascript
// mongosh
use quote_system_db
db.offers.createIndex({ run_id: 1, "supplier.id": 1 })
db.quotes.createIndex({ run_id: 1, created_at: -1 })
```

---

## ▶️ Execução

```bash
streamlit run streamlit_app.py
```
Fluxo:
1. Descreva a tarefa em PT-BR (ex.: *“Quero uma camiseta GG preta para quinta”*).
2. O sistema classifica/normaliza e cria uma fila de fornecedores.
3. Para cada fornecedor, a UI mostra a pergunta gerada. Cole a **resposta do fornecedor** (ex.: *“Tenho GG preta, R$ 59,90. Quinta à tarde.”*).
4. Se atender com **preço** e (se houver) **data/turno**, a oferta é aceita e **salva em `offers`**.
5. Ao encerrar (ou atingir 3 ofertas), o sistema gera o **orçamento** e **salva em `quotes`**.

---

## 🔎 Ver no MongoDB Compass

- Conecte em `mongodb://localhost:27017`.
- DB: **`quote_system_db`**
  - **`suppliers_*`**: fornecedores (seeds).
  - **`offers`**: 1 doc por **oferta aceita** (tem `run_id`, `task`, `supplier`, `offer`).
  - **`quotes`**: 1 doc por **orçamento final** (mensagem final e lista `offers`).

Cada execução recebe um `run_id` (UUID) — use para filtrar ofertas e orçamento da mesma sessão.

---

## 🧪 Exemplos

- **Roupas**: “**camiseta GG preta** para **quinta-feira**” → `size='GG'`, `color='preta'` ok.
- **Torneira**: “**torneira pingando** **amanhã de manhã**” → pergunta determinística para o fornecedor.

> **Datas aceitas nas respostas**: `YYYY-MM-DD`, `YYYY/MM/DD`, `dd/mm`, `dd/mm/aaaa`, e termos como *hoje*, *amanhã*, *depois de amanhã* e *dias da semana*.

---

## 🧰 Troubleshooting

- **Tamanho trocado (ex.: GG → M)** → usar `ClothingNormalizerNode` atual (regex de segurança).
- **`ValueError: month must be in 1..12`** → corrigido no `SupplierAnswerParserNode` (validação/heurística de data).
- **LLM/Ollama não responde** → verifique `OLLAMA_HOST` e modelo disponível em `OLLAMA_MODEL`.
- **Sem docs no Compass** → só grava **ofertas aceitas** e o **orçamento** final.

---

## ➕ Novos serviços

1. Criar `*NormalizerNode` para extrair campos do texto do usuário.
2. Criar `*ServiceNode` com consulta ao Mongo via `list_suppliers_by_service`.
3. Ajustar `workflow.py` (roteamento do classifier → normalizer → service).
4. (Opcional) Adaptar `SupplierQuestionNode` com pergunta específica do serviço.

---

## 📜 Licença

Projeto para fins educacionais. Adapte a licença (MIT/Apache/etc.) conforme necessário.
