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
    return "Servidor da Calculadora Shopee Online - Ajustado para Pasta1.csv"

@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
    
    file = request.files['file']
    
    try:
        content = file.read()
        # Tenta ler com o separador ';' que é o da sua planilha
        try:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8')
        except:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='iso-8859-1')

        # Mapeamento das colunas da SUA planilha para o banco de dados
        mapeamento = {
            'PRODUTO_ID': 'id',
            'DESCRICAO': 'descricao',
            'PRECO_CUSTO': 'custo'
        }

        # Verifica se as colunas existem
        for col_origem in mapeamento.keys():
            if col_origem not in df.columns:
                return jsonify({"erro": f"Coluna '{col_origem}' não encontrada na planilha."}), 400

        # Filtra apenas as colunas que precisamos
        df_final = df[list(mapeamento.keys())].copy()
        df_final.rename(columns=mapeamento, inplace=True)

        # Trata o custo: converte "4,78" (string) para 4.78 (número)
        df_final['custo'] = df_final['custo'].astype(str).str.replace(',', '.').astype(float)
        
        # Converte o ID para string para evitar erros de busca
        df_final['id'] = df_final['id'].astype(str)

        # Salva no SQLite
        conn = sqlite3.connect(DB_NAME)
        df_final.to_sql('produtos', conn, if_exists='replace', index=False)
        conn.close()
        
        return jsonify({"mensagem": f"Sucesso! {len(df_final)} produtos da planilha importados."})
    
    except Exception as e:
        return jsonify({"erro": f"Erro ao processar: {str(e)}"}), 500

@app.route('/produto/<id_produto>', methods=['GET'])
def get_produto(id_produto):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
