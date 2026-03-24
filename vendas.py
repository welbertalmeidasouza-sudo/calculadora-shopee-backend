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
        
        # Tabela 1: Vendas
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
        
        # Tabela 2: Configurações (Datas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
        ''')

        # Tabela 3: Pagamentos em Carteira
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagamentos (
                id_pedido TEXT PRIMARY KEY,
                data_pagamento TEXT,
                valor_recebido REAL
            );
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print("Aviso na criação das tabelas:", e)

init_db()

# ==========================================
# ROTAS DE CONFIGURAÇÕES (DATAS)
# ==========================================

@vendas_bp.route('/configuracoes', methods=['GET'])
def get_configuracoes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT chave, valor FROM configuracoes")
        rows = cursor.fetchall()
        conn.close()
        
        # Prepara um dicionário com as duas datas para enviar ao painel
        config = {"ultima_digitacao": "", "ultimo_pagamento": ""}
        for row in rows:
            if row['chave'] in config:
                config[row['chave']] = row['valor']
                
        return jsonify(config)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@vendas_bp.route('/configuracoes', methods=['POST'])
def salvar_configuracoes():
    try:
        dados = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Salva a data de digitação
        if 'ultima_digitacao' in dados and dados['ultima_digitacao'] is not None:
            cursor.execute('''
                INSERT INTO configuracoes (chave, valor) VALUES ('ultima_digitacao', %s)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
            ''', (dados['ultima_digitacao'],))
            
        # Salva a data de pagamento
        if 'ultimo_pagamento' in dados and dados['ultimo_pagamento'] is not None:
            cursor.execute('''
                INSERT INTO configuracoes (chave, valor) VALUES ('ultimo_pagamento', %s)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
            ''', (dados['ultimo_pagamento'],))
            
        conn.commit()
        conn.close()
        
        return jsonify({"status": "sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ==========================================
# ROTAS DE PAGAMENTOS
# ==========================================

@vendas_bp.route('/pagamentos', methods=['GET'])
def listar_pagamentos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id_pedido, data_pagamento, valor_recebido FROM pagamentos")
        rows = cursor.fetchall()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@vendas_bp.route('/pagamentos/guardar', methods=['POST'])
def guardar_pagamentos():
    try:
        dados = request.json
        lista = dados.get('pagamentos', [])
        conn = get_db_connection()
        cursor = conn.cursor()
        for p in lista:
            cursor.execute('''
                INSERT INTO pagamentos (id_pedido, data_pagamento, valor_recebido)
                VALUES (%s, %s, %s)
                ON CONFLICT (id_pedido) DO UPDATE SET
                    data_pagamento = EXCLUDED.data_pagamento,
                    valor_recebido = EXCLUDED.valor_recebido
            ''', (p['id_pedido'], p['data_pagamento'], p['valor_recebido']))
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Pagamentos salvos com sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ==========================================
# ROTAS DE VENDAS
# ==========================================

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
        cursor.execute("DELETE FROM pagamentos")
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Vendas e Pagamentos apagados com sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
