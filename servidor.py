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
    cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id TEXT PRIMARY KEY, descricao TEXT, custo REAL)')
    conn.commit()
    conn.close()

@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    file = request.files['file']
    try:
        content = file.read()
        # Tenta ler com a codificação brasileira do Excel (ISO-8859-1)
        try:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='iso-8859-1', engine='python')
        except:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8', engine='python')

        # Traduz os nomes das colunas da sua planilha (Pasta1.csv)
        mapeamento = {'PRODUTO_ID': 'id', 'DESCRICAO': 'descricao', 'PRECO_CUSTO': 'custo'}
        
        df = df[list(mapeamento.keys())].rename(columns=mapeamento)
        
        # Limpa o custo (troca vírgula por ponto) e remove espaços
        df['custo'] = df['custo'].astype(str).str.replace(',', '.').str.strip().astype(float)
        df['id'] = df['id'].astype(str).str.strip()

        conn = sqlite3.connect(DB_NAME)
        df.to_sql('produtos', conn, if_exists='replace', index=False)
        conn.close()
        return jsonify({"mensagem": f"Sucesso! {len(df)} produtos carregados."})
    except Exception as e:
        return jsonify({"erro": f"Erro técnico: {str(e)}"}), 500

@app.route('/produto/<id_produto>', methods=['GET'])
def get_produto(id_produto):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT descricao, custo FROM produtos WHERE id = ?", (str(id_produto),))
    row = cursor.fetchone()
    conn.close()
    if row: return jsonify({"descricao": row[0], "custo": row[1]})
    return jsonify({"erro": "Não encontrado"}), 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
