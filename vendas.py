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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracoes (
                chave TEXT PRIMARY KEY,
                valor TEXT
            );
        ''')

        # NOVA TABELA PARA MÚLTIPLOS PAGAMENTOS (Evita que um sobrescreva o outro)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pagamentos_v2 (
                id_pedido TEXT,
                data_pagamento TEXT,
                valor_recebido REAL,
                UNIQUE(id_pedido, data_pagamento, valor_recebido)
            );
        ''')
        
        # Script salva-vidas: Migra os pagamentos antigos para a tabela nova automaticamente
        try:
            cursor.execute("INSERT INTO pagamentos_v2 (id_pedido, data_pagamento, valor_recebido) SELECT id_pedido, data_pagamento, valor_recebido FROM pagamentos ON CONFLICT DO NOTHING")
            cursor.execute("DROP TABLE pagamentos")
        except Exception:
            pass
        
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
        
        if 'ultima_digitacao' in dados and dados['ultima_digitacao'] is not None:
            cursor.execute('''
                INSERT INTO configuracoes (chave, valor) VALUES ('ultima_digitacao', %s)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
            ''', (dados['ultima_digitacao'],))
            
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
        cursor.execute("SELECT id_pedido, data_pagamento, valor_recebido FROM pagamentos_v2")
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
                INSERT INTO pagamentos_v2 (id_pedido, data_pagamento, valor_recebido)
                VALUES (%s, %s, %s)
                ON CONFLICT (id_pedido, data_pagamento, valor_recebido) DO NOTHING
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
        cursor.execute("DELETE FROM pagamentos_v2")
        conn.commit()
        conn.close()
        return jsonify({"mensagem": "Vendas e Pagamentos apagados com sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
