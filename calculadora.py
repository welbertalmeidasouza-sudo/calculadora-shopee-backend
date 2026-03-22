import os
import psycopg2
import psycopg2.extras
from flask import Blueprint, request, jsonify

calculadora_bp = Blueprint('calculadora_bp', __name__)

def get_db_connection():
    # Conecta usando a URL que configurou na Render
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

# Função para garantir que a tabela existe ao iniciar
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                sku TEXT PRIMARY KEY,
                nome TEXT,
                custo REAL
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print("Aviso na criação da tabela produtos:", e)

init_db()

@calculadora_bp.route('/produtos/todos', methods=['GET'])
def get_produtos():
    try:
        conn = get_db_connection()
        # Usamos o DictCursor para receber os resultados como dicionário
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT sku, nome, custo FROM produtos')
        produtos = cursor.fetchall()
        conn.close()
        
        resultado = {}
        for p in produtos:
            resultado[p['sku']] = {
                "nome": p['nome'],
                "custo": p['custo']
            }
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@calculadora_bp.route('/produtos/guardar', methods=['POST'])
def guardar_produtos():
    try:
        dados = request.json
        lista_produtos = dados.get('produtos', [])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for p in lista_produtos:
            cursor.execute('''
                INSERT INTO produtos (sku, nome, custo)
                VALUES (%s, %s, %s)
                ON CONFLICT (sku) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    custo = EXCLUDED.custo
            ''', (p['sku'], p['nome'], p['custo']))
            
        conn.commit()
        conn.close()
        
        return jsonify({"mensagem": "Produtos atualizados no PostgreSQL com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
