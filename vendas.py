import os
import psycopg2
import psycopg2.extras
from flask import Blueprint, request, jsonify

vendas_bp = Blueprint('vendas_bp', __name__)

def get_db_connection():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
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
            );
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print("Aviso na criação da tabela vendas:", e)

init_db()

@vendas_bp.route('/vendas', methods=['GET'])
def listar_vendas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta FROM vendas")
        rows = cursor.fetchall()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@vendas_bp.route('/vendas/guardar', methods=['POST'])
def guardar_vendas():
    try:
        dados = request.json
        lista_vendas = dados.get('vendas', [])
        conn = get_db_connection()
        cursor = conn.cursor()
        for v in lista_vendas:
            cursor.execute('''
                INSERT INTO vendas 
                (chave, id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chave) DO UPDATE SET
                    status = EXCLUDED.status,
                    qtd = EXCLUDED.qtd,
                    subtotal = EXCLUDED.subtotal,
                    receita_bruta = EXCLUDED.receita_bruta,
                    rastreio = EXCLUDED.rastreio
            ''', (v['chave'], v['id'], v.get('rastreio', '---'), v['dataOri'], 
                  v['sku'], v['nome'], v['status'], v['qtd'], v['subtotal'], v['receitaBruta']))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@vendas_bp.route('/vendas/limpar', methods=['DELETE'])
def limpar_vendas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vendas") 
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Vendas apagadas com sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
