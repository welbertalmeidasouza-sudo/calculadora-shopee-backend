# ==========================================
# ROTAS DE CONFIGURAÇÕES
# ==========================================

@vendas_bp.route('/configuracoes', methods=['GET'])
def get_configuracoes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT chave, valor FROM configuracoes")
        rows = cursor.fetchall()
        conn.close()
        
        # Prepara um dicionário com as duas datas
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
        
        # Salva a data de digitação se ela foi enviada
        if 'ultima_digitacao' in dados:
            cursor.execute('''
                INSERT INTO configuracoes (chave, valor) VALUES ('ultima_digitacao', %s)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
            ''', (dados['ultima_digitacao'],))
            
        # Salva a data de pagamento se ela foi enviada
        if 'ultimo_pagamento' in dados:
            cursor.execute('''
                INSERT INTO configuracoes (chave, valor) VALUES ('ultimo_pagamento', %s)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor
            ''', (dados['ultimo_pagamento'],))
            
        conn.commit()
        conn.close()
        
        return jsonify({"status": "sucesso"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
