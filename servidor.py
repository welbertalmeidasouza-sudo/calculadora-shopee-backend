from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_NAME = 'shopee_produtos.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabela de Produtos
    cursor.execute('CREATE TABLE IF NOT EXISTS produtos (id TEXT PRIMARY KEY, descricao TEXT, custo REAL)')
    # Tabela de Vendas
    cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
        chave TEXT PRIMARY KEY, id_pedido TEXT, rastreio TEXT, data_ori TEXT, 
        sku TEXT, nome_produto TEXT, status TEXT, qtd INTEGER, subtotal REAL, receita_bruta REAL)''')
    # Tabela de Saldo (Carteira)
    cursor.execute('''CREATE TABLE IF NOT EXISTS saldo (
        chave TEXT PRIMARY KEY, data TEXT, tipo TEXT, descricao TEXT, 
        id_pedido TEXT, direcao TEXT, valor REAL, status TEXT)''')
    conn.commit()
    conn.close()

@app.route('/saldo', methods=['GET'])
def get_saldo():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT data, tipo, descricao, id_pedido, direcao, valor, status FROM saldo")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"data": r[0], "tipo": r[1], "descricao": r[2], "id_pedido": r[3], "direcao": r[4], "valor": r[5], "status": r[6]} for r in rows])
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/saldo/guardar', methods=['POST'])
def guardar_saldo():
    try:
        transacoes = request.json.get('transacoes', [])
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        for t in transacoes:
            cursor.execute('INSERT OR REPLACE INTO saldo VALUES (?,?,?,?,?,?,?,?)', 
                           (t['chave'], t['data'], t['tipo'], t['descricao'], t['id_pedido'], t['direcao'], t['valor'], t['status']))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# Mantenha aqui as suas outras rotas de /upload e /vendas...

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
