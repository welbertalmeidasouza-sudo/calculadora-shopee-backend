import os
import psycopg2
import psycopg2.extras
import pandas as pd

from flask import Blueprint, request, jsonify

calculadora_bp = Blueprint('calculadora_bp', __name__)

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

# =========================
# INIT DB
# =========================
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
        print("Erro ao criar tabela:", e)

init_db()

# =========================
# BUSCAR PRODUTOS
# =========================
@calculadora_bp.route('/produtos/todos', methods=['GET'])
def get_produtos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT sku, nome, custo FROM produtos')
        produtos = cursor.fetchall()
        conn.close()

        resultado = {}
        for p in produtos:
            resultado[p['sku']] = {
                "nome": p['nome'],
                "custo": float(p['custo'])
            }

        return jsonify(resultado)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# =========================
# SALVAR PRODUTOS
# =========================
@calculadora_bp.route('/produtos/guardar', methods=['POST'])
def guardar_produtos():
    try:
        lista = request.json.get('produtos', [])

        conn = get_db_connection()
        cursor = conn.cursor()

        for p in lista:
            cursor.execute('''
                INSERT INTO produtos (sku, nome, custo)
                VALUES (%s, %s, %s)
                ON CONFLICT (sku) DO UPDATE SET
                nome = EXCLUDED.nome,
                custo = EXCLUDED.custo
            ''', (p['sku'], p['nome'], p['custo']))

        conn.commit()
        conn.close()

        return jsonify({"mensagem": "OK"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# =========================
# UPLOAD CSV / XLSX (NOVO)
# =========================
@calculadora_bp.route('/produtos/upload', methods=['POST'])
def upload_produtos():
    try:
        file = request.files['arquivo']

        # leitura
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return {"erro": "Formato inválido"}, 400

        df.columns = [c.strip().upper() for c in df.columns]

        # valida colunas
        col_sku = next((c for c in df.columns if c in ['SKU', 'PRODUTO_ID', 'CODEBAR']), None)
        col_custo = next((c for c in df.columns if c in ['CUSTO', 'PRECO_CUSTO']), None)
        col_nome = next((c for c in df.columns if c in ['NOME', 'DESCRICAO']), None)

        if not col_sku or not col_custo:
            return {"erro": "Colunas obrigatórias não encontradas"}, 400

        produtos = []
        skus_vistos = set()

        for _, row in df.iterrows():
            try:
                sku = str(row[col_sku]).strip().upper()
                custo = float(row[col_custo])

                if not sku or custo <= 0:
                    continue

                if sku in skus_vistos:
                    continue

                skus_vistos.add(sku)

                nome = str(row[col_nome]) if col_nome else "Sem Nome"

                produtos.append({
                    "sku": sku,
                    "nome": nome,
                    "custo": custo
                })
            except:
                continue

        # salva no banco
        conn = get_db_connection()
        cursor = conn.cursor()

        for p in produtos:
            cursor.execute('''
                INSERT INTO produtos (sku, nome, custo)
                VALUES (%s, %s, %s)
                ON CONFLICT (sku) DO UPDATE SET
                nome = EXCLUDED.nome,
                custo = EXCLUDED.custo
            ''', (p['sku'], p['nome'], p['custo']))

        conn.commit()
        conn.close()

        return {"inseridos": len(produtos)}

    except Exception as e:
        return {"erro": str(e)}, 500

# =========================
# PRECIFICAÇÃO (NOVO)
# =========================
@calculadora_bp.route('/precificar', methods=['POST'])
def precificar():
    try:
        data = request.json

        custo = float(data.get('custo', 0))
        imposto = float(data.get('imposto', 0)) / 100
        margem = float(data.get('margem', 0)) / 100

        faixas = [
            {"nome": "Até 79,99", "max": 79.99, "comm": 0.20, "taxa": 4},
            {"nome": "80 a 99,99", "max": 99.99, "comm": 0.14, "taxa": 16},
            {"nome": "100 a 199,99", "max": 199.99, "comm": 0.14, "taxa": 20},
            {"nome": "200 a 499,99", "max": 499.99, "comm": 0.14, "taxa": 26},
            {"nome": "Acima de 500", "max": float('inf'), "comm": 0.14, "taxa": 26},
        ]

        for i, f in enumerate(faixas):
            divisor = 1 - (f["comm"] + imposto + margem)
            if divisor <= 0:
                continue

            preco = (custo + f["taxa"]) / divisor

            if preco <= f["max"]:
                lucro = preco - (preco * f["comm"]) - f["taxa"] - (preco * imposto) - custo

                return {
                    "preco": round(preco, 2),
                    "lucro": round(lucro, 2),
                    "faixa": f["nome"]
                }

        return {"erro": "não calculado"}

    except Exception as e:
        return {"erro": str(e)}, 500
