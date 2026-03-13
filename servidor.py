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
        # Lê o conteúdo bruto do arquivo
        content = file.read()
        
        # Tenta ler com a codificação do Excel brasileiro (ISO-8859-1) e separador ";"
        try:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='iso-8859-1', engine='python', on_bad_lines='skip')
        except Exception:
            df = pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8', engine='python', on_bad_lines='skip')

        # Mapeamento das colunas originais da sua Pasta1.csv para o nosso padrão
        mapeamento = {
            'PRODUTO_ID': 'id',
            'DESCRICAO': 'descricao',
            'PRECO_CUSTO': 'custo'
        }

        # Verifica se as colunas necessárias existem no arquivo enviado
        for col_origem in mapeamento.keys():
            if col_origem not in df.columns:
                return jsonify({"erro": f"Coluna '{col_origem}' não encontrada na planilha."}), 400

        # Seleciona e renomeia as colunas
        df_final = df[list(mapeamento.keys())].copy()
        df_final.rename(columns=mapeamento, inplace=True)

        # LIMPEZA DE DADOS:
        # 1. Garante que o ID seja string e remove espaços
        df_final['id'] = df_final['id'].astype(str).str.strip()
        
        # 2. Converte o Custo: Remove espaços, troca vírgula por ponto
        df_final['custo'] = df_final['custo'].astype(str).str.replace(',', '.').str.strip()
        
        # 3. Transforma em número (o que não for número vira 'NaN')
        df_final['custo'] = pd.to_numeric(df_final['custo'], errors='coerce')
        
        # 4. Remove linhas onde o ID ou o Custo falharam na conversão
        df_final = df_final.dropna(subset=['id', 'custo'])
        
        # 5. Remove duplicados (caso o mesmo ID apareça duas vezes)
        df_final = df_final.drop_duplicates(subset=['id'])

        # Salva no Banco de Dados SQLite
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
        # Busca o produto pelo ID exato
        cursor.execute("SELECT descricao, custo FROM produtos WHERE id = ?", (str(id_produto).strip(),))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({"descricao": row[0], "custo": row[1]})
        else:
            return jsonify({"erro": "Produto não encontrado no banco de dados."}), 404
            
    except Exception as e:
        return jsonify({"erro": f"Erro na consulta: {str(e)}"}), 500

if __name__ == '__main__':
    init_db()
    # Porta dinâmica para o Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
