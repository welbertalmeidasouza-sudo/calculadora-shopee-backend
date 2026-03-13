from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
import io

app = Flask(__name__)
CORS(app)

DB_NAME = 'shopee_produtos.db'

def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            descricao TEXT,
            custo REAL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return "Servidor da Calculadora Shopee Online - Ativo e Pronto!"

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
        
        return jsonify({"mensagem": f"Sucesso! {len(df_final)} produtos carregados corretamente."})
    
    except Exception as e:
        return jsonify({"erro": f"Erro técnico ao processar: {str(e)}"}), 500

@app.route('/produto/<id_produto>', methods=['GET'])
def get_produto(id_produto):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT descricao, custo FROM produtos WHERE id = ?", (str(id_produto).strip(),))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({"descricao": row[0], "custo": row[1]})
        else:
            return jsonify({"erro": "Produto não encontrado no banco de dados."}), 404
            
    except Exception as e:
        return jsonify({"erro": f"Erro na consulta: {str(e)}"}), 500

# ----- NOVA ROTA PARA O RELATÓRIO -----
@app.route('/produtos/todos', methods=['GET'])
def get_todos_produtos():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, descricao, custo FROM produtos")
        rows = cursor.fetchall()
        conn.close()

        # O HTML espera um dicionário/objeto onde a chave é o ID (SKU)
        banco = {}
        for row in rows:
            banco[str(row[0])] = {
                "descricao": row[1],
                "custo": row[2]
            }
        return jsonify(banco)
    except Exception as e:
        return jsonify({"erro": f"Erro ao puxar todos os produtos: {str(e)}"}), 500

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
