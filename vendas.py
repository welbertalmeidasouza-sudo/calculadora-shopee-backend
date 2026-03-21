from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
import io

# IMPORTANTE: Importamos o Blueprint do ficheiro vendas.py
from vendas import vendas_bp, DB_NAME

app = Flask(__name__)

# Configuração do CORS para permitir que o seu HTML (mesmo local) fale com o Render
CORS(app, resources={r"/*": {"origins": "*"}})

# Registamos as rotas de vendas que estão no outro ficheiro
app.register_blueprint(vendas_bp)

def init_db():
    """Inicializa o Banco de Dados e cria as tabelas se não existirem"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Produtos (Custos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            descricao TEXT,
            custo REAL
        )
    ''')
    
    # Tabela de Vendas (Histórico)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            chave TEXT PRIMARY KEY,
            id_pedido TEXT,
            rastreio TEXT,
            data_ori TEXT,
            sku TEXT,
            nome_produto TEXT,
            status TEXT,
            qtd INTEGER,
            subtotal REAL,
            receita_bruta REAL
        )
    ''')
    
    # Tabela de Saldo (Carteira)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saldo (
            chave TEXT PRIMARY KEY,
            data TEXT,
            tipo TEXT,
            descricao TEXT,
            id_pedido TEXT,
            direcao TEXT,
            valor REAL,
            status TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Inicia o banco de dados assim que o servidor arranca
init_db()

@app.route('/')
def home():
    return "Servidor Shopee Pro - Ativo e Pronto para Vendas e Produtos!"

# --- ROTAS DE PRODUTOS (CUSTOS) ---

@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    try:
        content = file.read()
        try:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='iso-8859-1', engine='python', on_bad_lines='skip')
        except Exception:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8', engine='python', on_bad_lines='skip')

        mapeamento = {
            'PRODUTO_ID': 'id',
            'DESCRICAO': 'descricao',
            'PRECO_CUSTO': 'custo'
        }

        for col_origem in mapeamento.keys():
            if col_origem not in df.columns:
                return jsonify({"erro": f"Coluna '{col_origem}' não encontrada na planilha."}), 400

        df_final = df[list(mapeamento.keys())].copy()
        df_final.rename(columns=mapeamento, inplace=True)

        df_final['id'] = df_final['id'].astype(str).str.strip()
        df_final['custo'] = df_final['custo'].astype(str).str.replace(',', '.').str.strip()
        df_final['custo'] = pd.to_numeric(df_final['custo'], errors='coerce')
        df_final = df_final.dropna(subset=['id', 'custo'])
        df_final = df_final.drop_duplicates(subset=['id'])

        conn = sqlite3.connect(DB_NAME)
        df_final.to_sql('produtos', conn, if_exists='replace', index=False)
        conn.close()
        
        return jsonify({"mensagem": f"Sucesso! {len(df_final)} produtos carregados."})
    
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/produtos/todos', methods=['GET'])
def get_todos_produtos():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, descricao, custo FROM produtos")
        rows = cursor.fetchall()
        conn.close()

        banco = {}
        for row in rows:
            banco[str(row[0])] = {
                "descricao": row[1],
                "custo": row[2]
            }
        return jsonify(banco)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# O servidor rodará na porta definida pelo Render ou na 5000 localmente
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
