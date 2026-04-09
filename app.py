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

# --- CONFIGURAÇÕES VIA VARIÁVEIS DE AMBIENTE ---
DB_DSN = os.getenv('DB_DSN', 'SeuDSN')
DB_UID = os.getenv('DB_UID', 'SeuUsuario')
DB_PWD = os.getenv('DB_PWD', 'SuaSenha')
CONN_STR = f"DSN={DB_DSN};UID={DB_UID};PWD={DB_PWD};"

# Caminho do arquivo Excel (Centralizado via variável de ambiente)
ARQUIVO_EXCEL = os.getenv('EXCEL_PATH', 'caminho/para/seu/arquivo.xlsm')
# URL da Planilha Google (Protegida)
SHEET_URL = os.getenv('GOOGLE_SHEET_URL', 'https://docs.google.com/spreadsheets/d/ID_DA_PLANILHA/export?format=csv')

def formatar(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%d/%m/%Y')
    return "-" if dt is None or str(dt).strip() == "" else str(dt)

def processar_estatisticas_excel(inicio, fim):
    try:
        if not os.path.exists(ARQUIVO_EXCEL):
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
    except Exception as e:
        print(f"Erro ao processar Excel: {e}")
        return 0, 0

@app.route('/pedido/qrcode/<id_pedido>', methods=['GET'])
def gerar_qrcode(id_pedido):
    # Usando request.host_url para gerar o link dinamicamente conforme o servidor onde rodar
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
        cursor.execute("SELECT * FROM dbo.[BANCODEDADOS]('', '', '')")
        rows = cursor.fetchall()

        pendentes = []
        for row in rows:
            try:
                val_12 = str(row[12]).strip() if len(row) > 12 else ""
                val_15 = str(row[15]).strip() if len(row) > 15 else ""
                protocolo = str(row[13]).strip() if len(row) > 13 else ""
                pedido   = str(row[5]).strip()
                vendedor = str(row[1]).strip()
                nf       = str(row[3]).strip()
                cliente  = str(row[9]).strip() if len(row) > 9 else str(row[2])
                transp = str(row[7]).strip().upper() if (len(row) > 7 and row[7] is not None) else ""
                
                dt_col_final = val_12 if val_12 and val_12.lower() != "none" else val_15
                data_emissao = row[2] 
                              
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

                if 'PEDIDO' in df_sheets.columns:
                    col_ped = 'PEDIDO'
                    col_loc = [c for c in df_sheets.columns if 'LOCALIZ' in c][0]
                    mapa = dict(zip(
                        df_sheets[col_ped].astype(str).str.strip().str.upper(), 
                        df_sheets[col_loc].astype(str).str.strip()
                    ))
                else:
                    mapa = dict(zip(
                        df_sheets.iloc[:, 2].astype(str).str.strip().str.upper(), 
                        df_sheets.iloc[:, 3].astype(str).str.strip()
                    ))

                for p in pendentes:
                    cod_sistema = str(p.get('pedido', '')).strip().upper()
                    loc_encontrada = mapa.get(cod_sistema, "---")
                    loc_str = str(loc_encontrada).strip()
                    p['localizacao'] = "---" if loc_str.lower() in ['nan', 'none', '', 'empty'] else loc_str
            else:
                for p in pendentes: p['localizacao'] = "Erro Conexão"
        except Exception:
            for p in pendentes: p['localizacao'] = "OFFLINE"
        
        return jsonify(pendentes)
    except Exception as e:
        return jsonify({"erro": "Erro na conexão com banco de dados"}), 500
    finally:
        if 'conn' in locals(): conn.close()

@app.route('/<path:filename>')
def custom_static(filename):
    return send_from_directory('.', filename)

@app.route('/')
def index():
    return send_from_directory('.', 'inicio.html')    

@app.route('/pedido/detalhes_qr/<id_pedido>', methods=['GET'])
def detalhes_qr_final(id_pedido):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        query_pv = [BANCODEDADOS]
        cursor.execute(query_pv, (id_pedido,))
        row_p = cursor.fetchone()
        
        cursor.execute("SELECT * FROM dbo.[BANCODEDADOS]('', '', '') WHERE PEDIDO = ?", (id_pedido,))
        row_e = cursor.fetchone()

        if row_p:
            dt_final = "AGUARDANDO"
            protocolo_final = "N/A"
            nf_exibicao = "Pendente"
            emissao_exibicao = "-"
            nome_transportadora = "--"

            if row_e:
                val_12 = str(row_e[12]).strip() if row_e[12] else ""
                val_15 = str(row_e[15]).strip() if len(row_e) > 15 and row_e[15] else ""
                dt_final = val_12 if val_12 and val_12.lower() != "none" else val_15
                protocolo_final = str(row_e[13]).strip() if len(row_e) > 13 else "N/A"
                nf_exibicao = str(row_e[3]).strip()
                emissao_exibicao = row_e[2].strftime('%d/%m/%y') if row_e[2] else "-"

                if len(row_e) > 7:
                    val_7 = str(row_e[7]).strip()
                    if val_7 and val_7.lower() != "none" and val_7 != "":
                        nome_transportadora = val_7

            data = {
                "pedido": row_p[0],
                "cliente": row_p[1],
                "vendedor": row_p[2],
                "tipo_transp": str(row_p[3]).strip() if row_p[3] else "TRANSPORTADORA",
                "nome_transp": nome_transportadora,
                "nf": nf_exibicao,
                "emissao_nf": emissao_exibicao,
                "data_col": dt_final if dt_final else "AGUARDANDO",
                "protocolo": protocolo_final
            }
            return jsonify(data)
        
        return jsonify({"erro": "Pedido não encontrado"}), 404
    except Exception as e:
        return jsonify({"erro": "Erro interno"}), 500
    finally:
        if 'conn' in locals(): conn.close()

def formatar_data_protheus(data_raw):
    if not data_raw or str(data_raw).strip() in ["None", ""]:
        return "-"
    d_str = str(data_raw).strip()
    if len(d_str) == 8 and d_str.isdigit():
        return f"{d_str[6:8]}/{d_str[4:6]}/{d_str[0:4]}"
    try:
        return data_raw.strftime('%d/%m/%Y')
    except:
        return d_str            

@app.route('/pedido/<id_pedido>', methods=['GET'])
def get_pedido(id_pedido):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        query_pv = [BANCODEDADOS]
        cursor.execute(query_pv, (id_pedido,))
        row_p = cursor.fetchone()

        if row_p:
            dt_final = "AGUARDANDO"
            nome_transp_exp = "--"
            nf_num = "Pendente"
            nf_data = "-"

            cursor.execute("SELECT * FROM dbo.[BANCODEDADOS]('', '', '') WHERE PEDIDO = ?", (id_pedido,))
            row_e = cursor.fetchone()

            if row_e:
                val_12 = str(row_e[12]).strip() if row_e[12] else ""
                val_15 = str(row_e[15]).strip() if len(row_e) > 15 and row_e[15] else ""
                raw_col = val_12 if val_12 and val_12.lower() != "none" else val_15
                dt_final = formatar_data_protheus(raw_col)
                nome_transp_exp = str(row_e[7]).strip() if row_e[7] else "--"
                nf_num = str(row_e[3]).strip()
                nf_data = formatar_data_protheus(row_e[2]) 

            data = {
                "empresa": row_p[0],
                "pedido": row_p[1],
                "cliente": row_p[2],
                "emissao_ped": formatar_data_protheus(row_p[3]),
                "vendedor": row_p[4],
                "transp": f"{row_p[5]} | {nome_transp_exp}",
                "data_col": dt_final if dt_final else "AGUARDANDO",
                "nf": nf_num,
                "emissao_nf": nf_data,
                "producao": "-" 
            }
            return jsonify(data)
        
        return jsonify({"erro": "Pedido não encontrado"}), 404
    except Exception as e:
        return jsonify({"erro": "Erro interno"}), 500
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=****)
