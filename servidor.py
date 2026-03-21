from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
import io

# Importa o Blueprint do arquivo vendas.py
from vendas import vendas_bp, DB_NAME

app = Flask(__name__)

# Configuração de CORS expandida para evitar o erro de conexão
CORS(app, resources={r"/*": {"origins": "*"}})

# Registra as rotas do arquivo vendas.py
app.register_blueprint(vendas_bp)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id TEXT PRIMARY KEY, descricao TEXT, custo REAL)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
        chave TEXT PRIMARY KEY, id_pedido TEXT, rastreio TEXT, data_ori TEXT, 
        sku TEXT, nome_produto TEXT, status TEXT, qtd INTEGER, subtotal REAL, receita_bruta REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS saldo (
        chave TEXT PRIMARY KEY, data TEXT, tipo TEXT, descricao TEXT, 
        id_pedido TEXT, direcao TEXT, valor REAL, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return "Servidor Shopee Pro - Online"

@app.route('/produtos/todos', methods=['GET'])
def get_todos_produtos():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, descricao, custo FROM produtos")
        rows = cursor.fetchall()
        conn.close()
        return jsonify({str(r[0]): {"descricao": r[1], "custo": r[2]} for r in rows})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# Rota de upload de custos (mantenha a que você já tinha)
@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files: return jsonify({"erro": "Sem arquivo"}), 400
    file = request.files['file']
    try:
        df = pd.read_csv(io.BytesIO(file.read()), sep=';', encoding='iso-8859-1', engine='python', on_bad_lines='skip')
        conn = sqlite3.connect(DB_NAME)
        # Lógica de salvar produtos...
        df.rename(columns={'PRODUTO_ID': 'id', 'DESCRICAO': 'descricao', 'PRECO_CUSTO': 'custo'}, inplace=True)
        df[['id', 'descricao', 'custo']].to_sql('produtos', conn, if_exists='replace', index=False)
        conn.close()
        return jsonify({"mensagem": "Produtos atualizados"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
