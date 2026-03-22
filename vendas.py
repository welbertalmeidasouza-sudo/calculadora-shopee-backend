import sqlite3
from flask import Blueprint, request, jsonify

vendas_bp = Blueprint('vendas_bp', __name__)
DB_NAME = 'shopee_produtos.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@vendas_bp.route('/vendas', methods=['GET'])
def listar_vendas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta FROM vendas")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
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
                INSERT OR REPLACE INTO vendas 
                (chave, id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
