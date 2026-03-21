import sqlite3
import os
from flask import Blueprint, request, jsonify

# Criamos o Blueprint para ser chamado no servidor principal
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
        # Busca todas as vendas salvas
        cursor.execute("SELECT id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta FROM vendas")
        rows = cursor.fetchall()
        conn.close()

        vendas = []
        for r in rows:
            vendas.append({
                "id": r['id_pedido'],
                "rastreio": r['rastreio'],
                "dataOri": r['data_ori'],
                "sku": r['sku'],
                "nome": r['nome_produto'],
                "status": r['status'],
                "qtd": r['qtd'],
                "subtotal": r['subtotal'],
                "receitaBruta": r['receita_bruta']
            })
        return jsonify(vendas)
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
            # INSERT OR REPLACE evita duplicados baseados na 'chave'
            cursor.execute('''
                INSERT OR REPLACE INTO vendas 
                (chave, id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                v['chave'], v['id'], v.get('rastreio', '---'), v['dataOri'], 
                v['sku'], v['nome'], v['status'], v['qtd'], 
                v['subtotal'], v['receitaBruta']
            ))
            
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Vendas sincronizadas com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
