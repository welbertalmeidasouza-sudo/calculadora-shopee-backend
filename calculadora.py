import sqlite3
from flask import Blueprint, request, jsonify

calculadora_bp = Blueprint('calculadora_bp', __name__)
DB_NAME = 'shopee_produtos.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    
    # Garante que a tabela de produtos existe no banco de dados
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            sku TEXT PRIMARY KEY,
            nome TEXT,
            custo REAL
        )
    ''')
    conn.commit()
    
    return conn

# ROTA 1: Consultar todos os produtos (Usada pela calculadora e pelo painel de vendas)
@calculadora_bp.route('/produtos/todos', methods=['GET'])
def get_produtos():
    try:
        conn = get_db_connection()
        produtos = conn.execute('SELECT sku, nome, custo FROM produtos').fetchall()
        conn.close()
        
        # Formata o resultado no dicionário que o Javascript já espera
        resultado = {}
        for p in produtos:
            resultado[p['sku']] = {
                "nome": p['nome'],
                "custo": p['custo']
            }
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ROTA 2: Receber a leitura da planilha e guardar/atualizar no banco
@calculadora_bp.route('/produtos/guardar', methods=['POST'])
def guardar_produtos():
    try:
        dados = request.json
        lista_produtos = dados.get('produtos', [])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for p in lista_produtos:
            cursor.execute('''
                INSERT OR REPLACE INTO produtos (sku, nome, custo)
                VALUES (?, ?, ?)
            ''', (p['sku'], p['nome'], p['custo']))
            
        conn.commit()
        conn.close()
        
        return jsonify({"mensagem": "Produtos atualizados no SQLite com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
