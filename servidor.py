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
    # Tabela de Produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id TEXT PRIMARY KEY,
            descricao TEXT,
            custo REAL
        )
    ''')
    # Tabela de Vendas
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
        )
    ''')
    # NOVA TABELA: Saldo (Pagamentos Recebidos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saldo (
            chave TEXT PRIMARY KEY,
            data TEXT,
            tipo TEXT,
            descricao TEXT,
            id_pedido TEXT,
            direcao TEXT,
            valor REAL,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return "Servidor Shopee Pro - Ativo"

# --- ROTAS DE PRODUTOS ---
@app.route('/produtos/todos', methods=['GET'])
def get_todos_produtos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao, custo FROM produtos")
    rows = cursor.fetchall()
    conn.close()
    return jsonify({str(r[0]): {"descricao": r[1], "custo": r[2]} for r in rows})

# --- ROTAS DE VENDAS ---
@app.route('/vendas', methods=['GET'])
def get_vendas():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id_pedido, rastreio, data_ori, sku, nome_produto, status, qtd, subtotal, receita_bruta FROM vendas")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "rastreio": r[1], "dataOri": r[2], "sku": r[3], "nome": r[4], "status": r[5], "qtd": r[6], "subtotal": r[7], "receitaBruta": r[8]} for r in rows])

@app.route('/vendas/guardar', methods=['POST'])
def guardar_vendas():
    vendas = request.json.get('vendas', [])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for v in vendas:
        cursor.execute('INSERT OR REPLACE INTO vendas VALUES (?,?,?,?,?,?,?,?,?,?)', (v['chave'], v['id'], v['rastreio'], v['dataOri'], v['sku'], v['nome'], v['status'], v['qtd'], v['subtotal'], v['receitaBruta']))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Vendas integradas"}), 200

# --- NOVAS ROTAS DE SALDO ---
@app.route('/saldo', methods=['GET'])
def get_saldo():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT data, tipo, descricao, id_pedido, direcao, valor, status FROM saldo")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"data": r[0], "tipo": r[1], "descricao": r[2], "id_pedido": r[3], "direcao": r[4], "valor": r[5], "status": r[6]} for r in rows])

@app.route('/saldo/guardar', methods=['POST'])
def guardar_saldo():
    transacoes = request.json.get('transacoes', [])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for t in transacoes:
        cursor.execute('INSERT OR REPLACE INTO saldo VALUES (?,?,?,?,?,?,?,?)', 
                       (t['chave'], t['data'], t['tipo'], t['descricao'], t['id_pedido'], t['direcao'], t['valor'], t['status']))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Transações de saldo integradas"}), 200

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
