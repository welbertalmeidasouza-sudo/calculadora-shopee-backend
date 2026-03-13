from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import os

app = Flask(__name__)
CORS(app) # Isso permite que seu HTML acesse a API de fora

DB_NAME = 'shopee_produtos.db'

def init_db():
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

@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    try:
        # Lê o CSV (ajuste o separador se necessário, ex: sep=';')
        df = pd.read_csv(file)
        
        conn = sqlite3.connect(DB_NAME)
        # Salva no SQLite substituindo os dados antigos
        df.to_sql('produtos', conn, if_exists='replace', index=False)
        conn.close()
        
        return jsonify({"mensagem": "Banco de dados atualizado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/produto/<id_produto>', methods=['GET'])
def get_produto(id_produto):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT descricao, custo FROM produtos WHERE id = ?", (id_produto,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({"descricao": row[0], "custo": row[1]})
    return jsonify({"erro": "Produto não encontrado"}), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))