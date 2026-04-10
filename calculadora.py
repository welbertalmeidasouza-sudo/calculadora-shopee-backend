import os
import io
import math
import psycopg2
import psycopg2.extras
import pandas as pd

from flask import Blueprint, request, jsonify

calculadora_bp = Blueprint('calculadora_bp', __name__)


def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception('DATABASE_URL não configurada')
    return psycopg2.connect(database_url)


def normalizar_numero(valor):
    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        if pd.isna(valor):
            return None
        return float(valor)

    texto = str(valor).strip()
    if not texto:
        return None

    texto = texto.replace('R$', '').replace('r$', '').replace(' ', '')

    # Caso tenha milhar e decimal misturados
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        texto = texto.replace(',', '.')

    try:
        return float(texto)
    except ValueError:
        return None


def normalizar_texto(valor, padrao=''):
    if valor is None:
        return padrao
    if isinstance(valor, float) and pd.isna(valor):
        return padrao
    texto = str(valor).strip()
    return texto if texto else padrao


def obter_coluna(df, opcoes):
    colunas = {str(c).strip().upper(): c for c in df.columns}
    for opcao in opcoes:
        if opcao in colunas:
            return colunas[opcao]
    return None


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


def calcular_cenario(preco, faixa, imposto_p, custo):
    comissao_valor = preco * faixa['comm']
    impostos_valor = preco * imposto_p
    repasse = preco - comissao_valor - faixa['taxa']
    lucro = preco - comissao_valor - faixa['taxa'] - impostos_valor - custo
    margem_real = (lucro / preco * 100) if preco > 0 else 0

    return {
        "preco": round(preco, 2),
        "faixa": faixa['nome'],
        "comissao_valor": round(comissao_valor, 2),
        "comissao_percentual": round(faixa['comm'] * 100, 2),
        "taxa_fixa": round(faixa['taxa'], 2),
        "repasse": round(repasse, 2),
        "impostos_valor": round(impostos_valor, 2),
        "impostos_percentual": round(imposto_p * 100, 2),
        "lucro": round(lucro, 2),
        "margem_real": round(margem_real, 2)
    }


@calculadora_bp.route('/produtos/todos', methods=['GET'])
def get_produtos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT sku, nome, custo FROM produtos ORDER BY sku ASC')
        produtos = cursor.fetchall()
        conn.close()

        resultado = {}
        for p in produtos:
            resultado[p['sku']] = {
                "nome": p['nome'],
                "custo": float(p['custo']) if p['custo'] is not None else 0.0
            }

        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@calculadora_bp.route('/produtos/guardar', methods=['POST'])
def guardar_produtos():
    try:
        dados = request.get_json(silent=True) or {}
        lista_produtos = dados.get('produtos', [])

        if not isinstance(lista_produtos, list):
            return jsonify({"erro": "O campo 'produtos' deve ser uma lista"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        inseridos = 0

        for p in lista_produtos:
            sku = normalizar_texto(p.get('sku')).upper()
            nome = normalizar_texto(p.get('nome'), 'Sem Nome')
            custo = normalizar_numero(p.get('custo'))

            if not sku:
                continue
            if custo is None or custo < 0:
                continue

            cursor.execute('''
                INSERT INTO produtos (sku, nome, custo)
                VALUES (%s, %s, %s)
                ON CONFLICT (sku) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    custo = EXCLUDED.custo
            ''', (sku, nome, custo))

            inseridos += 1

        conn.commit()
        conn.close()

        return jsonify({
            "mensagem": "Produtos atualizados no PostgreSQL com sucesso!",
            "inseridos": inseridos
        }), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@calculadora_bp.route('/produtos/upload', methods=['POST'])
def upload_produtos():
    try:
        if 'arquivo' not in request.files:
            return jsonify({"erro": "Nenhum arquivo enviado no campo 'arquivo'"}), 400

        arquivo = request.files['arquivo']

        if not arquivo or not arquivo.filename:
            return jsonify({"erro": "Arquivo inválido"}), 400

        nome_arquivo = arquivo.filename.lower().strip()

        if not (nome_arquivo.endswith('.csv') or nome_arquivo.endswith('.xlsx')):
            return jsonify({"erro": "Formato inválido. Envie um arquivo .csv ou .xlsx"}), 400

        if nome_arquivo.endswith('.csv'):
            conteudo = arquivo.read()
            try:
                df = pd.read_csv(io.BytesIO(conteudo), dtype=str, sep=None, engine='python', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(conteudo), dtype=str, sep=None, engine='python', encoding='latin1')
        else:
            df = pd.read_excel(arquivo, dtype=str)

        if df.empty:
            return jsonify({"erro": "O arquivo está vazio"}), 400

        col_sku = obter_coluna(df, ['PRODUTO_ID', 'SKU', 'CODEBAR'])
        col_custo = obter_coluna(df, ['PRECO_CUSTO', 'CUSTO'])
        col_nome = obter_coluna(df, ['DESCRICAO', 'NOME DO PRODUTO', 'NOME', 'PRODUTO', 'TITULO'])

        if not col_sku:
            return jsonify({
                "erro": "Coluna obrigatória de SKU não encontrada. Use uma destas: PRODUTO_ID, SKU, CODEBAR"
            }), 400

        if not col_custo:
            return jsonify({
                "erro": "Coluna obrigatória de custo não encontrada. Use uma destas: PRECO_CUSTO, CUSTO"
            }), 400

        produtos_validos = []
        skus_vistos = set()
        erros_linhas = 0
        duplicados = 0

        for _, row in df.iterrows():
            sku = normalizar_texto(row.get(col_sku)).upper()
            custo = normalizar_numero(row.get(col_custo))
            nome = normalizar_texto(row.get(col_nome), 'Sem Nome') if col_nome else 'Sem Nome'

            if not sku:
                erros_linhas += 1
                continue

            if custo is None or custo < 0:
                erros_linhas += 1
                continue

            if sku in skus_vistos:
                duplicados += 1
                continue

            skus_vistos.add(sku)

            produtos_validos.append({
                "sku": sku,
                "nome": nome,
                "custo": custo
            })

        if not produtos_validos:
            return jsonify({
                "erro": "Nenhum produto válido encontrado no arquivo"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        for p in produtos_validos:
            cursor.execute('''
                INSERT INTO produtos (sku, nome, custo)
                VALUES (%s, %s, %s)
                ON CONFLICT (sku) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    custo = EXCLUDED.custo
            ''', (p['sku'], p['nome'], p['custo']))

        conn.commit()
        conn.close()

        return jsonify({
            "mensagem": "Upload processado com sucesso",
            "inseridos": len(produtos_validos),
            "duplicados_ignorados": duplicados,
            "linhas_invalidas": erros_linhas
        }), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@calculadora_bp.route('/precificar', methods=['POST'])
def precificar():
    try:
        data = request.get_json(silent=True) or {}

        custo = normalizar_numero(data.get('custo'))
        imposto = normalizar_numero(data.get('imposto'))
        margem = normalizar_numero(data.get('margem'))

        if custo is None or custo <= 0:
            return jsonify({"erro": "O campo 'custo' deve ser maior que zero"}), 400

        if imposto is None:
            imposto = 0.0

        if margem is None:
            margem = 0.0

        imposto_p = imposto / 100.0
        margem_p = margem / 100.0

        faixas = [
            {"nome": "Até R$ 79,99", "max": 79.99, "comm": 0.20, "taxa": 4.00},
            {"nome": "R$ 80 a R$ 99,99", "max": 99.99, "comm": 0.14, "taxa": 16.00},
            {"nome": "R$ 100 a R$ 199,99", "max": 199.99, "comm": 0.14, "taxa": 20.00},
            {"nome": "R$ 200 a R$ 499,99", "max": 499.99, "comm": 0.14, "taxa": 26.00},
            {"nome": "Acima de R$ 500", "max": math.inf, "comm": 0.14, "taxa": 26.00}
        ]

        preco_final_raw = None
        index_atual = None

        for i, faixa in enumerate(faixas):
            divisor = 1 - (faixa['comm'] + imposto_p + margem_p)

            if divisor <= 0:
                continue

            preco_sugerido = (custo + faixa['taxa']) / divisor

            if preco_sugerido <= faixa['max'] or faixa['max'] == math.inf:
                preco_final_raw = preco_sugerido
                index_atual = i
                break

        if preco_final_raw is None or index_atual is None:
            return jsonify({"erro": "Não foi possível calcular com os parâmetros informados"}), 400

        preco_com_99 = math.ceil(preco_final_raw) - 0.01
        if preco_com_99 < preco_final_raw:
            preco_com_99 += 1.00

        if preco_com_99 > faixas[index_atual]['max'] and index_atual < len(faixas) - 1:
            index_atual += 1

        faixa_principal = faixas[index_atual]
        resultado_principal = calcular_cenario(preco_com_99, faixa_principal, imposto_p, custo)

        sugestao = None
        if index_atual > 0:
            faixa_anterior = faixas[index_atual - 1]
            preco_limite = faixa_anterior['max']
            resultado_sugestao = calcular_cenario(preco_limite, faixa_anterior, imposto_p, custo)

            if resultado_sugestao['lucro'] > 0:
                sugestao = resultado_sugestao

        resposta = {
            **resultado_principal,
            "sugestao": sugestao
        }

        return jsonify(resposta), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500
