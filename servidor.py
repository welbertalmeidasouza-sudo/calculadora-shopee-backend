from flask import Flask
from flask_cors import CORS
from vendas import vendas_bp
from calculadora import calculadora_bp

app = Flask(__name__)

# Permite que o seu painel HTML converse com o servidor
CORS(app)

# Regista as rotas de vendas e da calculadora
app.register_blueprint(vendas_bp)
app.register_blueprint(calculadora_bp)

@app.route('/')
def home():
    return "Servidor da Calculadora Shopee rodando perfeitamente com PostgreSQL!"

if __name__ == '__main__':
    # O Render usa a porta 10000 por padrão
    app.run(host='0.0.0.0', port=10000)
