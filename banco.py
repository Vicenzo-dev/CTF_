from flask import Flask, jsonify, request
import pyodbc
import os

app = Flask(__name__)

CONN_STR = os.environ.get("DB_CONNECTION_STRING", "DSN=Totvs;UID=usuario_seguro;PWD=senha_segura;")

def validar_banco(cursor, nome_banco):
    query = "SELECT name FROM sys.databases WHERE name = ?"
    cursor.execute(query, nome_banco)
    row = cursor.fetchone()
    return row.name if row else None

def validar_tabela(cursor, nome_tabela):
    query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ? AND TABLE_TYPE = 'BASE TABLE'"
    cursor.execute(query, nome_tabela)
    row = cursor.fetchone()
    return row.TABLE_NAME if row else None


@app.route('/')
def index():
    return "API de Inspeção Online. Acesse /debug/bancos para listar os bancos de dados."


@app.route('/debug/bancos', methods=['GET'])
def listar_todos_os_bancos():
    termo_busca = request.args.get('nome', '')
    conn = None
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        query = "SELECT name FROM sys.databases WHERE database_id > 4 AND name LIKE ? ORDER BY name"
        cursor.execute(query, f"%{termo_busca}%")
        
        bancos = [row.name for row in cursor.fetchall()]
        return jsonify({
            "busca_por": termo_busca if termo_busca else "Todos",
            "quantidade": len(bancos),
            "bancos": bancos
        })
    except Exception as e:
        return jsonify({"erro": "Erro ao processar listagem de bancos."}), 500
    finally:
        if conn: conn.close()


@app.route('/debug/funcoes/<nome_banco>', methods=['GET'])
def listar_funcoes(nome_banco):
    conn = None
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        banco_seguro = validar_banco(cursor, nome_banco)
        if not banco_seguro:
            return jsonify({"erro": "Banco de dados inválido ou não encontrado."}), 400
            
        cursor.execute(f"USE [{banco_seguro}]")
        
        query = """
            SELECT name 
            FROM sys.objects 
            WHERE type IN ('IF', 'TF', 'FN') 
            AND name LIKE 'FN_%'
            ORDER BY name
        """
        cursor.execute(query)
        funcoes = [row.name for row in cursor.fetchall()]
        
        return jsonify({
            "banco": banco_seguro,
            "total_funcoes": len(funcoes),
            "funcoes": funcoes
        })
    except Exception as e:
        return jsonify({"erro": "Erro interno ao processar funções."}), 500
    finally:
        if conn: conn.close()


@app.route('/debug/tabelas/<nome_banco>', methods=['GET'])
def listar_tabelas(nome_banco):
    busca_tabela = request.args.get('busca', '') 
    conn = None
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        banco_seguro = validar_banco(cursor, nome_banco)
        if not banco_seguro:
            return jsonify({"erro": "Banco de dados inválido ou não encontrado."}), 400
            
        cursor.execute(f"USE [{banco_seguro}]")
        
        query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND TABLE_NAME LIKE ?
            ORDER BY TABLE_NAME
        """
        cursor.execute(query, f"%{busca_tabela}%")
        tabelas = [row.TABLE_NAME for row in cursor.fetchall()]
        
        return jsonify({
            "banco": banco_seguro,
            "total_tabelas": len(tabelas),
            "tabelas": tabelas
        })
    except Exception as e:
        return jsonify({"erro": "Erro ao processar listagem de tabelas."}), 500
    finally:
        if conn: conn.close()


@app.route('/debug/dados/<nome_banco>/<nome_tabela>', methods=['GET'])
def ver_dados(nome_banco, nome_tabela):
    conn = None
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        banco_seguro = validar_banco(cursor, nome_banco)
        if not banco_seguro:
            return jsonify({"erro": "Banco de dados inválido ou não encontrado."}), 400
            
        cursor.execute(f"USE [{banco_seguro}]")
        
        tabela_segura = validar_tabela(cursor, nome_tabela)
        if not tabela_segura:
            return jsonify({"erro": "Tabela inválida ou não encontrada no banco especificado."}), 400

        query = f"SELECT TOP 10 * FROM [{tabela_segura}]"
        cursor.execute(query)
        
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        
        resultados = []
        for row in rows:
            resultados.append(dict(zip(columns, row)))
            
        return jsonify({
            "banco": banco_seguro,
            "tabela": tabela_segura,
            "colunas": columns,
            "exemplo_dados": resultados
        })
    except Exception as e:
        return jsonify({"erro": "Erro ao recuperar dados da tabela."}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)