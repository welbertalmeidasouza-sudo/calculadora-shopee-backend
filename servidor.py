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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Cria a tabela se não existir. 
    # Certifique-se que seu CSV tenha colunas chamadas 'id', 'descricao' e 'custo'
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
    return "Servidor da Calculadora Shopee está online!"

@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    try:
        # Lê o conteúdo do arquivo para a memória para testar codificações
        content = file.read()
        
        # Tenta ler em UTF-8, se falhar, tenta ISO-8859-1 (padrão Excel Brasil)
        try:
            df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding='utf-8')
        except Exception:
            df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', encoding='iso-8859-1')

        # Limpeza básica: remove espaços em branco dos nomes das colunas
        df.columns = [c.strip().lower() for c in df.columns]

        # Verifica se as colunas necessárias existem
        colunas_necessarias = ['id', 'descricao', 'custo']
        if not all(col in df.columns for col in colunas_necessarias):
            return jsonify({"erro": f"O CSV deve conter as colunas: {colunas_necessarias}"}), 400

        # Conecta e salva no SQLite
        conn = sqlite3.connect(DB_NAME)
        # Substitui os dados antigos pelos novos
        df.to_sql('produtos', conn, if_exists='replace', index=False)
        conn.close()
        
        return jsonify({"mensagem": f"Sucesso! {len(df)} produtos cadastrados."})
    
    except Exception as e:
        return jsonify({"erro": f"Falha ao processar arquivo: {str(e)}"}), 500

@app.route('/produto/<id_produto>', methods=['GET'])
def get_produto(id_produto):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Busca pelo ID (convertendo para string para evitar erro de tipo)
        cursor.execute("SELECT descricao, custo FROM produtos WHERE id = ?", (str(id_produto),))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({"descricao": row[0], "custo": row[1]})
        return jsonify({"erro": "Produto não encontrado"}), 404
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    init_db()
    # Configuração necessária para o Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
