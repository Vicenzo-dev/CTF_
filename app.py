from flask import Flask, jsonify, send_from_directory, request, send_file
from flask_cors import CORS
import pyodbc
from datetime import datetime
import pandas as pd
import os
import qrcode
import io 
import requests
from io import StringIO

app = Flask(__name__)
CORS(app)


DB_DSN = os.getenv('DB_DSN')
DB_UID = os.getenv('DB_UID')
DB_PWD = os.getenv('DB_PWD')
CONN_STR = f"DSN={DB_DSN};UID={DB_UID};PWD={DB_PWD};"

ARQUIVO_EXCEL = os.getenv('EXCEL_PATH')
SHEET_URL = os.getenv('GOOGLE_SHEET_URL')

def formatar(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%d/%m/%Y')
    return "-" if dt is None or str(dt).strip() == "" else str(dt)

def processar_estatisticas_excel(inicio, fim):
    try:
        if not ARQUIVO_EXCEL or not os.path.exists(ARQUIVO_EXCEL):
            return 0, 0
        
        df = pd.read_excel(ARQUIVO_EXCEL, sheet_name='REGISTRO DE PEDIDOS', usecols=['LIBERAÇÃO', 'STATUS'])
        df['LIBERAÇÃO'] = pd.to_datetime(df['LIBERAÇÃO'], errors='coerce')
        df = df.dropna(subset=['LIBERAÇÃO'])

        if inicio and fim:
            dt_inicio = pd.to_datetime(inicio)
            dt_fim = pd.to_datetime(fim)
            df = df[(df['LIBERAÇÃO'] >= dt_inicio) & (df['LIBERAÇÃO'] <= dt_fim)]

        no_prazo = int((df['STATUS'] == 'No Prazo').sum())
        atrasado = int((df['STATUS'] == 'Atrasado').sum())
        
        return no_prazo, atrasado
    except Exception:
        return 0, 0

@app.route('/pedido/qrcode/<id_pedido>', methods=['GET'])
def gerar_qrcode(id_pedido):
   
    base_url = f"{request.host_url}pedido_detalhes.html?id={id_pedido}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(base_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@app.route('/pedidos/status_excel', methods=['GET'])
def get_status_excel():
    data_inicio = request.args.get('inicio')
    data_fim = request.args.get('fim')
    no_prazo, atrasado = processar_estatisticas_excel(data_inicio, data_fim)
    
    return jsonify({
        'no_prazo': no_prazo, 
        'atrasado': atrasado
    })

@app.route('/pedidos/pendentes_coleta', methods=['GET'])
def get_pendentes_coleta():
    data_inicio = request.args.get('inicio')
    data_fim = request.args.get('fim')
    tipo_data = request.args.get('tipo_data', 'emissao') 
    
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        # Query sanitizada para o portfólio
        cursor.execute("SELECT * FROM dbo.[VW_EXPEDICAO_GERAL]('', '', '')")
        rows = cursor.fetchall()

        pendentes = []
        for row in rows:
            try:
              
                pedido   = str(row[0]).strip() 
                vendedor = str(row[0]).strip()
                nf       = str(row[0]).strip()
                cliente  = str(row[0]).strip()
                transp   = str(row[0]).strip().upper()
                protocolo = str(row[0]).strip()
                
                dt_col_final = str(row[0]).strip()
                data_emissao = row[0]
                              
                alvo_filtro = ""
                if tipo_data == 'status':
                    if dt_col_final and "/" in dt_col_final:
                        partes = dt_col_final.split('/')
                        alvo_filtro = f"{partes[2]}-{partes[1]}-{partes[0]}"
                else:
                    if isinstance(data_emissao, datetime):
                        alvo_filtro = data_emissao.strftime('%Y-%m-%d')

                if data_inicio and data_fim:
                    if not alvo_filtro or not (data_inicio <= alvo_filtro <= data_fim):
                        continue

                if nf != "" and nf != "None":
                    pendentes.append({
                        "pedido": pedido,
                        "nf": nf,
                        "vendedor": vendedor,
                        "cliente": cliente,
                        "transp": transp,
                        "data_col": dt_col_final,
                        "producao": "FATURADO",
                        "protoc_coleta": protocolo ,
                        "emissao": formatar(data_emissao)
                    })      
            except: 
                continue
        
   
        try:
            res_sheets = requests.get(SHEET_URL, timeout=15)
            if res_sheets.status_code == 200:
                df_sheets = pd.read_csv(StringIO(res_sheets.text), sep=',', engine='python')
                df_sheets.columns = [str(c).strip().upper() for c in df_sheets.columns]

        
                mapa = {}
                if 'PEDIDO' in df_sheets.columns:
                    col_ped = 'PEDIDO'
                    col_loc = [c for c in df_sheets.columns if 'LOCALIZ' in c][0]
                    mapa = dict(zip(df_sheets[col_ped].astype(str).str.strip().str.upper(), 
                                    df_sheets[col_loc].astype(str).str.strip()))

                for p in pendentes:
                    cod_sistema = str(p.get('pedido', '')).strip().upper()
                    loc_encontrada = mapa.get(cod_sistema, "---")
                    p['localizacao'] = "---" if str(loc_encontrada).lower() in ['nan', 'none', ''] else loc_encontrada
        except Exception:
            for p in pendentes: p['localizacao'] = "OFFLINE"
        
        return jsonify(pendentes)
    except Exception:
        return jsonify({"erro": "Erro ao processar dados"}), 500
    finally:
        if 'conn' in locals(): conn.close()


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/')
def index():
    return send_from_directory('static', 'inicio.html')    

@app.route('/pedido/detalhes_qr/<id_pedido>', methods=['GET'])
def detalhes_qr_final(id_pedido):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        

        cursor.execute("SELECT * FROM dbo.[VW_PEDIDOS_DETALHES] WHERE PEDIDO = ?", (id_pedido,))
        row_p = cursor.fetchone()
        
        if row_p:
            data = {
                "pedido": row_p[0],
                "cliente": row_p[0],
                "vendedor": row_p[0],
                "tipo_transp": "TRANSPORTADORA",
                "nome_transp": str(row_p[0]),
                "nf": str(row_p[0]),
                "emissao_nf": "-",
                "data_col": "AGUARDANDO",
                "protocolo": "N/A"
            }
            return jsonify(data)
        
        return jsonify({"erro": "Pedido não encontrado"}), 404
    except Exception:
        return jsonify({"erro": "Erro interno"}), 500
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
