import streamlit as st
import pandas as pd
import re
import holidays
import hashlib
import calendar as cal_module
from datetime import datetime, timedelta, date
import os
import json
import time
import pdfplumber
import shutil
import zipfile
import io
import requests
from streamlit_cookies_controller import CookieController

# ==========================================
# DADOS GLOBAIS: TRIBUNAIS E CIDADES (IBGE)
# ==========================================
UFS_BRASIL = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

LISTA_TRIBUNAIS = [
    "Todos", "STF", "STJ", "TST", "TSE", "STM",
    "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
    "TJAC", "TJAL", "TJAP", "TJAM", "TJBA", "TJCE", "TJDF", "TJES", 
    "TJGO", "TJMA", "TJMT", "TJMS", "TJMG", "TJPA", "TJPB", "TJPR", 
    "TJPE", "TJPI", "TJRJ", "TJRN", "TJRS", "TJRO", "TJRR", "TJSC", 
    "TJSP", "TJSE", "TJTO", "Outros"
]

TIPOS_PECA = ["Contestação", "Recurso de Apelação", "Agravo de Instrumento", "Embargos de Declaração", "Contrarrazões", "Impugnação à Execução", "Exceção de Pré-Executividade", "Manifestação / Petição Simples", "Pedido de Prazo", "Outro"]
TIPOS_AUDIENCIA = ["Audiência de Conciliação", "Audiência de Instrução e Julgamento", "Audiência Preliminar", "Audiência de Custódia", "Sessão de Julgamento", "Perícia", "Inspeção Judicial", "Outro"]

def buscar_cidades_por_uf(uf: str) -> list:
    """Busca as cidades no IBGE e guarda no session_state para não travar o sistema."""
    if uf == "Todas": return ["Todas"]
    
    # 1. Cria um "cofre" na memória do sistema (se ainda não existir)
    if "memoria_ibge" not in st.session_state:
        st.session_state["memoria_ibge"] = {}
        
    # 2. Se a gente já buscou as cidades desse Estado antes, pega do cofre e não gasta internet
    if uf in st.session_state["memoria_ibge"]:
        return st.session_state["memoria_ibge"][uf]
        
    # 3. Se for a primeira vez, vai lá no IBGE buscar
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            cidades = [cid["nome"] for cid in resp.json()]
            lista_final = ["Todas"] + cidades
            
            # Guarda a lista no cofre para a próxima vez ser instantâneo!
            st.session_state["memoria_ibge"][uf] = lista_final
            return lista_final
    except Exception as e:
        print(f"Erro ao buscar IBGE: {e}")
        
    # Se a internet cair ou o IBGE sair do ar, devolvemos o básico para o advogado não ficar travado
    return ["Todas", "Capital", "Interior"]

try:
    import google.generativeai as genai
except Exception as e:
    genai = None
    _gemini_import_error = e

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def card_indicador(titulo, valor, icone, cor_destaque="#2563eb"):
    """Cria um card visual de alta qualidade para substituir o st.metric."""
    st.markdown(f"""
    <div style="
        background-color: white;
        padding: 20px;
        border-radius: 16px;
        border-left: 6px solid {cor_destaque};
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    ">
        <div style="color: #64748b; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
            {icone} {titulo}
        </div>
        <div style="color: #1e293b; font-size: 1.8rem; font-weight: 800; margin-top: 5px;">
            {valor}
        </div>
    </div>
    """, unsafe_allow_html=True)
#
    def gerar_arquivo_ics(prazos, audiencias):  # ✅ começa sem indentação
    """
    Gera o conteúdo de um ficheiro .ics (iCalendar) para importar no telemóvel.
    Inclui UIDs persistentes para evitar duplicados e alertas de 24h.
    """
    import hashlib
    from datetime import datetime, timedelta

    def criar_uid(string_base):
        return hashlib.md5(string_base.encode()).hexdigest() + "@jurismind.app"

    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JurisMind//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]

    # --- PROCESSAR PRAZOS ---
    for p in prazos:
        dt = _get_dt(p)
        if dt:
            dt_str = dt.strftime("%Y%m%d")
            uid = criar_uid(f"prazo_{p.get('chave', p.get('processo'))}_{dt_str}")

            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid}")
            ics.append(f"SUMMARY:🚨 PRAZO: {p.get('processo', 'S/N')}")
            ics.append(f"DTSTART;VALUE=DATE:{dt_str}")
            ics.append(f"DESCRIPTION:Tribunal: {p.get('tribunal', 'N/A')}\\nIA: {p.get('resumo_processo','')}")

            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Prazo amanhã")
            ics.append("END:VALARM")
            ics.append("END:VEVENT")

    ics.append("END:VCALENDAR")
    return "\n".join(ics)

    import hashlib
    from datetime import datetime, timedelta

    def criar_uid(string_base):
        # Gera um ID único baseado nos dados para o calendário não duplicar eventos
        return hashlib.md5(string_base.encode()).hexdigest() + "@jurismind.app"

    # Cabeçalho padrão do formato iCalendar
    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JurisMind//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    # --- PROCESSAR PRAZOS ---
    for p in prazos:
        dt = _get_dt(p)
        if dt:
            dt_str = dt.strftime("%Y%m%d")
            uid = criar_uid(f"prazo_{p.get('chave', p.get('processo'))}_{dt_str}")
            
            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid}")
            ics.append(f"SUMMARY:🚨 PRAZO: {p.get('processo', 'S/N')}")
            ics.append(f"DTSTART;VALUE=DATE:{dt_str}")
            ics.append(f"DESCRIPTION:Tribunal: {p.get('tribunal', 'N/A')}\\nIA: {p.get('resumo_processo','')}")
            
            # Alerta de 24 horas
            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Prazo amanhã")
            ics.append("END:VALARM")
            ics.append("END:VEVENT")
            
    # --- PROCESSAR AUDIÊNCIAS ---
    for a in audiencias:
        d_aud = a.get("data")
        if d_aud:
            hora_str = a.get("hora", "09:00").replace(":", "")
            dt_inicio_str = f"{d_aud.strftime('%Y%m%d')}T{hora_str}00"
            uid_aud = criar_uid(f"aud_{a.get('id', 'aud')}_{dt_inicio_str}")
            
            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid_aud}")
            ics.append(f"SUMMARY:⚖️ AUDIÊNCIA: {a.get('tipo', 'Jurídica')}")
            ics.append(f"DTSTART:{dt_inicio_str}")
            
            try:
                dt_obj = datetime.combine(d_aud, datetime.strptime(hora_str, "%H%M").time())
                dt_fim = dt_obj + timedelta(hours=1)
                ics.append(f"DTEND:{dt_fim.strftime('%Y%m%dT%H%M00')}")
            except:
                pass

            ics.append(f"LOCATION:{a.get('local', 'Escritório')}")
            ics.append(f"DESCRIPTION:Processo: {a.get('processo', 'S/N')}\\nObs: {a.get('observacoes','')}")
            
            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Audiência amanhã")
            ics.append("END:VALARM")
            ics.append("END:VEVENT")
            
    ics.append("END:VCALENDAR")
    return "\n".join(ics)

    import hashlib
    from datetime import datetime, timedelta

    def criar_uid(string_base):
        # Gera um ID único baseado nos dados para o calendário não duplicar eventos
        return hashlib.md5(string_base.encode()).hexdigest() + "@jurismind.app"

    # Cabeçalho padrão do formato iCalendar
    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JurisMind//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    # --- PROCESSAR PRAZOS ---
    for p in prazos:
        # Tenta obter a data fatal usando a função auxiliar do sistema
        dt = _get_dt(p)
        
        if dt:
            # Formata a data para o padrão ICS (AAAAMMDD)
            dt_str = dt.strftime("%Y%m%d")
            uid = criar_uid(f"prazo_{p.get('chave', p.get('processo'))}_{dt_str}")
            
            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid}")
            ics.append(f"SUMMARY:🚨 PRAZO: {p.get('processo', 'S/N')}")
            ics.append(f"DTSTART;VALUE=DATE:{dt_str}")
            ics.append(f"DESCRIPTION:Tribunal: {p.get('tribunal', 'N/A')}\\nIA: {p.get('resumo_processo','')}")
            
            # Alerta de 24 horas (PT24H = 24 horas antes)
            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Prazo amanhã")
            ics.append("END:VALARM")
            
            ics.append("END:VEVENT")
            
    # --- PROCESSAR AUDIÊNCIAS ---
    for a in audiencias:
        d_aud = a.get("data")
        if d_aud:
            # Formata hora e data para o padrão ICS (AAAAMMDDT HHMMSS)
            hora_str = a.get("hora", "09:00").replace(":", "")
            dt_inicio_str = f"{d_aud.strftime('%Y%m%d')}T{hora_str}00"
            uid_aud = criar_uid(f"aud_{a.get('id', 'aud')}_{dt_inicio_str}")
            
            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid_aud}")
            ics.append(f"SUMMARY:⚖️ AUDIÊNCIA: {a.get('tipo', 'Jurídica')}")
            ics.append(f"DTSTART:{dt_inicio_str}")
            
            # Define o fim (por padrão 1 hora depois)
            try:
                dt_obj = datetime.combine(d_aud, datetime.strptime(hora_str, "%H%M").time())
                dt_fim = dt_obj + timedelta(hours=1)
                ics.append(f"DTEND:{dt_fim.strftime('%Y%m%dT%H%M00')}")
            except:
                pass

            ics.append(f"LOCATION:{a.get('local', 'Escritório')}")
            ics.append(f"DESCRIPTION:Processo: {a.get('processo', 'S/N')}\\nObs: {a.get('observacoes','')}")
            
            # Alerta de 24 horas
            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Audiência amanhã")
            ics.append("END:VALARM")
            
            ics.append("END:VEVENT")
            
    ics.append("END:VCALENDAR")
    return "\n".join(ics)

    # Este bloco deve ficar logo abaixo do Resumo Executivo (os cartões indicadores)
st.write("")
with st.container(border=True):
    col_info, col_btn = st.columns([2, 1])
    with col_info:
        st.markdown("**📲 Sincronizar com Calendário do Telemóvel**")
        st.caption("Baixe o arquivo para importar seus prazos e audiências no iPhone ou Android com alertas de 24h.")
    
    with col_btn:
        # Filtra apenas o que é relevante para exportar (prazos não cumpridos)
        prazos_para_exportar = [p for p in meus if _get_dt(p) and not p.get("cumprido")]
        audiencias_para_exportar = minhas_audiencias()
        
        # Gera o conteúdo do arquivo
        conteudo_ics = gerar_arquivo_ics(prazos_para_exportar, audiencias_para_exportar)
        
        # Botão de download
        st.download_button(
            label="📥 Baixar Agenda (.ics)",
            data=conteudo_ics,
            file_name=f"agenda_jurismind_{date.today().strftime('%d_%m')}.ics",
            mime="text/calendar",
            type="primary",
            use_container_width=True
        )

    def criar_uid(string_base):
        # Gera um ID único baseado nos dados para o calendário não duplicar eventos
        return hashlib.md5(string_base.encode()).hexdigest() + "@jurismind.app"

    # Cabeçalho padrão do formato iCalendar
    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JurisMind//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    # --- PROCESSAR PRAZOS ---
    for p in prazos:
        # Tenta obter a data fatal usando a função auxiliar do sistema
        dt = _get_dt(p)
        
        if dt:
            # Formata a data para o padrão ICS (AAAAMMDD)
            dt_str = dt.strftime("%Y%m%d")
            uid = criar_uid(f"prazo_{p.get('chave', p.get('processo'))}_{dt_str}")
            
            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid}")
            ics.append(f"SUMMARY:🚨 PRAZO: {p.get('processo', 'S/N')}")
            ics.append(f"DTSTART;VALUE=DATE:{dt_str}")
            ics.append(f"DESCRIPTION:Tribunal: {p.get('tribunal', 'N/A')}\\nIA: {p.get('resumo_processo','')}")
            
            # Alerta de 24 horas (PT24H = 24 horas antes)
            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Prazo amanhã")
            ics.append("END:VALARM")
            
            ics.append("END:VEVENT")
            
    # --- PROCESSAR AUDIÊNCIAS ---
    for a in audiencias:
        d_aud = a.get("data")
        if d_aud:
            # Formata hora e data para o padrão ICS (AAAAMMDDT HHMMSS)
            hora_str = a.get("hora", "09:00").replace(":", "")
            dt_inicio_str = f"{d_aud.strftime('%Y%m%d')}T{hora_str}00"
            uid_aud = criar_uid(f"aud_{a.get('id', 'aud')}_{dt_inicio_str}")
            
            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid_aud}")
            ics.append(f"SUMMARY:⚖️ AUDIÊNCIA: {a.get('tipo', 'Jurídica')}")
            ics.append(f"DTSTART:{dt_inicio_str}")
            
            # Define o fim (por padrão 1 hora depois)
            try:
                dt_obj = datetime.combine(d_aud, datetime.strptime(hora_str, "%H%M").time())
                dt_fim = dt_obj + timedelta(hours=1)
                ics.append(f"DTEND:{dt_fim.strftime('%Y%m%dT%H%M00')}")
            except:
                pass

            ics.append(f"LOCATION:{a.get('local', 'Escritório')}")
            ics.append(f"DESCRIPTION:Processo: {a.get('processo', 'S/N')}\\nObs: {a.get('observacoes','')}")
            
            # Alerta de 24 horas
            ics.append("BEGIN:VALARM")
            ics.append("TRIGGER:-PT24H")
            ics.append("ACTION:DISPLAY")
            ics.append("DESCRIPTION:Lembrete JurisMind: Audiência amanhã")
            ics.append("END:VALARM")
            
            ics.append("END:VEVENT")
            
    ics.append("END:VCALENDAR")
    return "\n".join(ics)

def enviar_email_notificacao(destinatario, assunto, mensagem_html):
    # Configurações para Gmail (necessita de "Senha de App")
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "pjurismind@gmail.com"
    SENDER_PWD = "zkkt plbc tger lgdn"

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(mensagem_html, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PWD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False
    
# =========================
# CONFIG
# =========================

# --- FUNÇÕES AUXILIARES FALTANTES PARA O CALENDÁRIO ---

def _feriados_rj_ano(ano):
    """Retorna os feriados do Rio de Janeiro para o ano selecionado."""
    return holidays.BR(state="RJ", years=ano)

def _todas_suspensoes():
    """Agrupa todas as suspensões de todos os tribunais para exibir no calendário."""
    susp_total = []
    for lista in st.session_state.suspensoes_por_tribunal.values():
        susp_total.extend(lista)
    return susp_total

def _get_dt(p):
    """Extrai e converte a data fatal de um processo para formato de data/hora."""
    dt = p.get("data_fatal")
    if not dt or dt == "DISPENSADO": # <--- ENSINAMOS A IGNORAR DISPENSADOS
        return None
    if isinstance(dt, str):
        try:
            return datetime.fromisoformat(dt)
        except:
            return None
    return dt

def _cliente_por_processo(num_processo: str):
    """Busca um cliente na base de dados pelo número do processo vinculado."""
    if not num_processo or num_processo == "S/N":
        return None
    for c in st.session_state.lista_clientes:
        if num_processo in c.get("processos_vinculados", []):
            return c
    return None

def _cliente_por_id(cliente_id: str):
    """Busca um cliente na base de dados pelo seu ID único."""
    if not cliente_id:
        return None
    for c in st.session_state.lista_clientes:
        if c.get("id") == cliente_id:
            return c
    return None

st.set_page_config(
    page_title="JurisMind Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

def aplicar_estilo_moderno():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif !important; }

    /* Fundo da Aplicação */
    .stApp, .stApp > header { background-color: #f8fafc !important; }

    /* Menu Lateral (Sidebar Navy) e Textos */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    
    /* Botões do Menu Lateral (Fundo Transparente/Escuro) */
    [data-testid="stSidebar"] button {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        justify-content: flex-start !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #334155 !important;
        border-color: #475569 !important;
    }

    /* Botões Principais (AZUL JURISMIND) */
    button[kind="primary"] {
        background-color: #2563eb !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    button[kind="primary"] * { color: white !important; font-weight: 600 !important; }
    button[kind="primary"]:hover {
        background-color: #1d4ed8 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3) !important;
    }

    /* Cartões Brancos com Sombra Suave */
    div[data-testid="stVerticalBlock"] > div:has(div[style*="border"]) {
        background-color: white !important;
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
        padding: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

#

def realizar_backup_completo():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(PASTA_BASE):
            for file in files:
                caminho_completo = os.path.join(root, file)
                caminho_relativo = os.path.relpath(caminho_completo, PASTA_BASE)
                zip_file.write(caminho_completo, caminho_relativo)
    return buffer.getvalue()

def substituir_banco_dados(nome_arquivo, conteudo_bytes):
    caminho_destino = os.path.join(PASTA_BASE, nome_arquivo)
    if os.path.exists(caminho_destino):
        os.replace(caminho_destino, caminho_destino + ".old")
    with open(caminho_destino, "wb") as f:
        f.write(conteudo_bytes)

def obter_caminho(arquivo: str) -> str:
    """Garante que o usuário logado só acesse os arquivos do seu próprio escritório."""
    escritorio = st.session_state.get("escritorio_id", "escritorio_padrao")
    pasta_escritorio = os.path.join(PASTA_BASE, escritorio)
    os.makedirs(pasta_escritorio, exist_ok=True)
    return os.path.join(pasta_escritorio, arquivo)

# =========================
# ARQUIVOS E BANCO DE DADOS
# =========================
PASTA_BASE = "/home/rafaeldgm/database_jurismind"
ARQUIVO_USR = os.path.join(PASTA_BASE, "usuarios.json")
os.makedirs(PASTA_BASE, exist_ok=True)    

# =========================
# HASH & SERIALIZACAO
# =========================
def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def _serializar(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Nao serializavel: {type(obj)}")

    # --- ADICIONE NAS IMPORTAÇÕES (Topo do arquivo) ---
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- ADICIONE APÓS A FUNÇÃO _serializar (Linha 55) ---
def sincronizar_com_google(eventos, tipo="audiencia"):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    # O arquivo que você renomeou no Passo 2
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    
    # Configuração para rodar no servidor remoto do Google Cloud
    creds = flow.run_local_server(
        host='localhost',
        port=8080, 
        authorization_prompt_message='Acesse este link para autorizar: {url}',
        success_message='Concluido! Pode fechar esta aba.',
        open_browser=False 
    )
    
    service = build('calendar', 'v3', credentials=creds)

    for ev in eventos:
        if tipo == "audiencia":
            resumo = f"⚖️ AUDIÊNCIA: {ev.get('tipo', 'Jurídica')}"
            desc = f"Processo: {ev.get('processo')} \nObs: {ev.get('observacoes')}"
            data_evento = ev['data'].isoformat()
            local = ev.get('local', 'Escritório')
        else:
            resumo = f"🚨 PRAZO FATAL: {ev.get('processo')}"
            desc = ev.get('resumo_processo', '')
            data_evento = ev['data_fatal'].date().isoformat() if hasattr(ev['data_fatal'], 'date') else ev['data_fatal']
            local = "Tribunal"

        evento_google = {
            'summary': resumo,
            'location': local,
            'description': desc,
            'start': {'dateTime': f"{data_evento}T09:00:00", 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': f"{data_evento}T10:00:00", 'timeZone': 'America/Sao_Paulo'},
        }
        service.events().insert(calendarId='primary', body=evento_google).execute()

# =========================
# USUARIOS (Com Papéis e Escritórios)
# =========================

def carregar_usuarios() -> list:
    # Se o arquivo não existir, cria o admin padrão
    if not os.path.exists(ARQUIVO_USR):
        padrao = {"usuarios": [{
            "usuario": "admin",
            "senha_hash": _hash("admin123"),
            "nome_completo": "Administrador Master",
            "cpf": "00000000000",
            "email": "admin@jurismind.com.br",
            "oab": "",
            "oab_uf": "RJ",
            "papel": "Master",
            "escritorio_id": "master", 
            "admin": True,
            "ativo": True,
            "requer_reset": False
        }]}
        with open(ARQUIVO_USR, "w", encoding="utf-8") as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao["usuarios"]

    # Tenta ler o arquivo de forma segura
    try:
        with open(ARQUIVO_USR, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except:
        dados = {} # Se o arquivo estiver corrompido, assume que está vazio

    # Garante que 'usuarios' será sempre uma lista
    usuarios = dados.get("usuarios", []) if isinstance(dados, dict) else []
    alterado = False
    
    for u in usuarios:
        # Atualiza senhas antigas para Hash
        if "senha" in u and "senha_hash" not in u:
            u["senha_hash"] = _hash(u["senha"])
            del u["senha"]
            alterado = True
        
        # Garante campos padrão para não dar erro no sistema
        u.setdefault("cpf", "")
        u.setdefault("email", "")
        u.setdefault("requer_reset", False)
        u.setdefault("ativo", True)
        u.setdefault("admin", False)
        u.setdefault("papel", "Sócio")
        u.setdefault("escritorio_id", "matriz")
        
        # Regra de proteção do Master
        if u.get("usuario") == "admin" and u.get("papel") != "Master":
            u["papel"] = "Master"
            u["escritorio_id"] = "master"
            u["admin"] = True
            alterado = True
            
    if alterado:
        salvar_usuarios(usuarios)
        
    return usuarios

def salvar_usuarios(usuarios: list):
    try:
        with open(ARQUIVO_USR, "w", encoding="utf-8") as f:
            json.dump({"usuarios": usuarios}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar usuários: {e}")

def autenticar(usuario: str, senha: str):
    usuarios_lista = carregar_usuarios()
    
    # Proteção: se a lista vier vazia, barra o login
    if not usuarios_lista:
        return None
        
    for u in usuarios_lista:
        if u.get("usuario", "").lower() == usuario.lower() and u.get("senha_hash") == _hash(senha) and u.get("ativo", True):
            return u
            
    return None

# =========================
# BANCOS DE DADOS ISOLADOS
# =========================
def _deserializar_pub(lista: list) -> list:
    for p in lista:
        if p.get("data_fatal") and isinstance(p["data_fatal"], str):
            if p["data_fatal"] == "DISPENSADO":
                continue # <--- PULA SE ESTIVER DISPENSADO
            convertido = False
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):

                try:
                    p["data_fatal"] = datetime.strptime(p["data_fatal"], fmt)
                    convertido = True
                    break
                except: continue
            if not convertido: p["data_fatal"] = None
        elif (isinstance(p.get("data_fatal"), date) and not isinstance(p.get("data_fatal"), datetime)):
            d = p["data_fatal"]
            p["data_fatal"] = datetime(d.year, d.month, d.day)
            
        p.setdefault("resumo_manual", ""); p.setdefault("resumo_processo", ""); p.setdefault("acao_necessaria", "")
        p.setdefault("minuta_gerada", ""); p.setdefault("tipo_peca", ""); p.setdefault("dias_prazo", 0)
        p.setdefault("analisado", False); p.setdefault("usuario_dono", ""); p.setdefault("cliente_id", ""); p.setdefault("cumprido", False)
    return lista

def carregar_publicacoes() -> list:
    if not os.path.exists(obter_caminho("publicacoes.json")):
        return []
    try:
        with open(obter_caminho("publicacoes.json"), "r", encoding="utf-8") as f:
            dados = _deserializar_pub(json.load(f))
            
            # --- AUTO DEDUPLICADOR DE PUBLICAÇÕES ---
            vistos = set()
            dados_limpos = []
            for d in dados:
                # Assinatura única baseada em: Processo + Data + 150 primeiros caracteres do texto
                texto_limpo = re.sub(r'\W+', '', d.get("conteudo", ""))[:150]
                assinatura = f"{d.get('processo')}_{d.get('data_pub')}_{texto_limpo}"
                if assinatura not in vistos:
                    vistos.add(assinatura)
                    dados_limpos.append(d)
                    
            return dados_limpos
    except Exception as e:
        st.warning(f"Erro ao carregar publicações: {e}")
        return []

def salvar_publicacoes():
    with open(obter_caminho("publicacoes.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_publicacoes, f, ensure_ascii=False, indent=2, default=_serializar)

def carregar_suspensoes() -> dict:
    base = {"Todos": [], "TJRJ": [], "Federal": [], "Trabalhista": [], "Outros": []}
    caminho = obter_caminho("suspensoes.json")
    if not os.path.exists(caminho): return base
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for tribunal, lista in dados.items():
                for item in lista:
                    for campo in ["inicio", "fim"]:
                        if isinstance(item.get(campo), str):
                            try: item[campo] = date.fromisoformat(item[campo])
                            except: item[campo] = None
            for k in base:
                if k not in dados: dados[k] = []
            return dados
    except: return base

def salvar_suspensoes():
    with open(obter_caminho("suspensoes.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.suspensoes_por_tribunal, f, ensure_ascii=False, indent=2, default=_serializar)

def carregar_audiencias() -> list:
    caminho = obter_caminho("audiencias.json")
    if not os.path.exists(caminho): return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for a in dados:
                if isinstance(a.get("data"), str):
                    try: a["data"] = date.fromisoformat(a["data"])
                    except: a["data"] = None
                a.setdefault("usuario_dono", "")
                a.setdefault("processo", "")
                a.setdefault("tipo", "")
                a.setdefault("local", "")
                a.setdefault("observacoes", "")
                a.setdefault("hora", "")
            return dados
    except: return []

def salvar_audiencias():
    with open(obter_caminho("audiencias.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_audiencias, f, ensure_ascii=False, indent=2, default=_serializar)

def carregar_clientes() -> list:
    caminho = obter_caminho("clientes.json")
    if not os.path.exists(caminho): return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for c in dados:
                c.setdefault("id", "")
                c.setdefault("nome", "")
                c.setdefault("cpf", "")
                c.setdefault("processos_vinculados", [])
                c.setdefault("usuario_dono", "")
            return dados
    except: return []

def salvar_clientes():
    with open(obter_caminho("clientes.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_clientes, f, ensure_ascii=False, indent=2, default=_serializar)

def carregar_financeiro() -> list:
    caminho = obter_caminho("financeiro.json")
    if not os.path.exists(caminho): return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for r in dados:
                r.setdefault("id", ""); r.setdefault("cliente_id", ""); r.setdefault("valor", 0.0)
                r.setdefault("status", "Pendente"); r.setdefault("usuario_dono", "")
            return dados
    except: return []

def salvar_financeiro():
    with open(obter_caminho("financeiro.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_financeiro, f, ensure_ascii=False, indent=2, default=_serializar)

def carregar_tarefas() -> list:
    caminho = obter_caminho("tarefas.json")
    if not os.path.exists(caminho): return []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
            for t in dados:
                t.setdefault("id", ""); t.setdefault("titulo", ""); t.setdefault("vencimento", "")
                t.setdefault("cumprido", False); t.setdefault("usuario_dono", "")
            return dados
    except: return []

def salvar_tarefas():
    with open(obter_caminho("tarefas.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_tarefas, f, ensure_ascii=False, indent=2, default=_serializar)

# =========================
# HASH
# =========================
def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

# =========================
# SERIALIZACAO
# =========================
def _serializar(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Nao serializavel: {type(obj)}")

# =========================
# CLIENTES
# =========================
def carregar_clientes() -> list:
    if not os.path.exists(obter_caminho("clientes.json")):
        return []
    try:
        with open(obter_caminho("clientes.json"), "r", encoding="utf-8") as f:
            dados = json.load(f)
        for c in dados:
            c.setdefault("id", "")
            c.setdefault("nome", "")
            c.setdefault("cpf", "")
            c.setdefault("rg", "")
            c.setdefault("data_nascimento", "")
            c.setdefault("email", "")
            c.setdefault("telefone", "")
            c.setdefault("telefone2", "")
            c.setdefault("cep", "")
            c.setdefault("logradouro", "")
            c.setdefault("numero", "")
            c.setdefault("complemento", "")
            c.setdefault("bairro", "")
            c.setdefault("cidade", "")
            c.setdefault("estado", "")
            c.setdefault("observacoes", "")
            c.setdefault("processos_vinculados", [])
            c.setdefault("usuario_dono", "")
        return dados
    except:
        return []

def salvar_clientes():
    with open(obter_caminho("clientes.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_clientes, f,
                  ensure_ascii=False, indent=2, default=_serializar)

# =========================
# FINANCEIRO
# =========================
def carregar_financeiro() -> list:
    if not os.path.exists(obter_caminho("financeiro.json")):
        return []
    try:
        with open(obter_caminho("financeiro.json"), "r", encoding="utf-8") as f:
            dados = json.load(f)
        for r in dados:
            r.setdefault("id", "")
            r.setdefault("cliente_id", "")
            r.setdefault("processo", "")
            r.setdefault("tipo", "")
            r.setdefault("descricao", "")
            r.setdefault("valor", 0.0)
            r.setdefault("percentual", 0.0)
            r.setdefault("data_vencimento", "")
            r.setdefault("data_recebimento", "")
            r.setdefault("status", "Pendente")
            r.setdefault("recorrente", False)
            r.setdefault("usuario_dono", "")
        return dados
    except:
        return []

def salvar_financeiro():
    with open(obter_caminho("financeiro.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_financeiro, f,
                  ensure_ascii=False, indent=2, default=_serializar)

# =========================
# AUDIENCIAS
# =========================
def carregar_audiencias() -> list:
    if not os.path.exists(obter_caminho("audiencias.json")):
        return []
    try:
        with open(obter_caminho("audiencias.json"), "r", encoding="utf-8") as f:
            dados = json.load(f)
        for a in dados:
            if isinstance(a.get("data"), str):
                try:
                    a["data"] = date.fromisoformat(a["data"])
                except:
                    a["data"] = None
            a.setdefault("usuario_dono", "")
            a.setdefault("processo", "")
            a.setdefault("tipo", "")
            a.setdefault("local", "")
            a.setdefault("observacoes", "")
            a.setdefault("hora", "")
        return dados
    except:
        return []

def salvar_audiencias():
    with open(obter_caminho("audiencias.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_audiencias, f,
                  ensure_ascii=False, indent=2, default=_serializar)
        
# =========================
# TAREFAS MANUAIS
# =========================
def carregar_tarefas() -> list:
    if not os.path.exists(obter_caminho("tarefas.json")): return []
    try:
        with open(obter_caminho("tarefas.json"), "r", encoding="utf-8") as f:
            dados = json.load(f)
        for t in dados:
            t.setdefault("id", "")
            t.setdefault("titulo", "")
            t.setdefault("descricao", "")
            t.setdefault("vencimento", "")
            t.setdefault("processo", "")
            t.setdefault("cumprido", False)
            t.setdefault("usuario_dono", "")
        return dados
    except: return []

def salvar_tarefas():
    with open(obter_caminho("tarefas.json"), "w", encoding="utf-8") as f:
        json.dump(st.session_state.lista_tarefas, f, ensure_ascii=False, indent=2, default=_serializar)

# =========================
# PUBLICACOES
# =========================
def _deserializar_pub(lista: list) -> list:
    for p in lista:
        if p.get("data_fatal") and isinstance(p["data_fatal"], str):
            convertido = False
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    p["data_fatal"] = datetime.strptime(p["data_fatal"], fmt)
                    convertido = True
                    break
                except:
                    continue
            if not convertido:
                p["data_fatal"] = None
        elif (isinstance(p.get("data_fatal"), date) and
              not isinstance(p.get("data_fatal"), datetime)):
            d = p["data_fatal"]
            p["data_fatal"] = datetime(d.year, d.month, d.day)

        p.setdefault("resumo_manual", "")
        p.setdefault("resumo_processo", "")
        p.setdefault("acao_necessaria", "")
        p.setdefault("minuta_gerada", "")
        p.setdefault("tipo_peca", "")
        p.setdefault("dias_prazo", 0)
        p.setdefault("analisado", False)
        p.setdefault("usuario_dono", "")
        p.setdefault("cliente_id", "")
        p.setdefault("analisado", False)
        p.setdefault("usuario_dono", "")
        p.setdefault("cliente_id", "")
        p.setdefault("cumprido", False)
    return lista

def _deserializar_susp(dicio: dict) -> dict:
    for tribunal, lista in dicio.items():
        for item in lista:
            for campo in ["inicio", "fim"]:
                if isinstance(item.get(campo), str):
                    try:
                        item[campo] = date.fromisoformat(item[campo])
                    except:
                        item[campo] = None
    return dicio

def salvar_publicacoes():
    try:
        with open(obter_caminho("publicacoes.json"), "w", encoding="utf-8") as f:
            json.dump(st.session_state.lista_publicacoes, f,
                      ensure_ascii=False, indent=2, default=_serializar)
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def carregar_publicacoes() -> list:
    if not os.path.exists(obter_caminho("publicacoes.json")):
        return []
    try:
        with open(obter_caminho("publicacoes.json"), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return _deserializar_pub(dados)
    except Exception as e:
        st.warning(f"Erro ao carregar: {e}")
        return []

def salvar_suspensoes():
    try:
        with open(obter_caminho("suspensoes.json"), "w", encoding="utf-8") as f:
            json.dump(st.session_state.suspensoes_por_tribunal, f,
                      ensure_ascii=False, indent=2, default=_serializar)
    except Exception as e:
        st.error(f"Erro ao salvar suspensoes: {e}")

def carregar_suspensoes() -> dict:
    base = {
        "Todos": [], "TJRJ": [], "Federal": [],
        "Trabalhista": [], "Outros": []
    }
    if not os.path.exists(obter_caminho("suspensoes.json")):
        return base
    try:
        with open(obter_caminho("suspensoes.json"), "r", encoding="utf-8") as f:
            dados = json.load(f)
        dados = _deserializar_susp(dados)
        for k in base:
            if k not in dados:
                dados[k] = []
        return dados
    except:
        return base

# =========================
# ESTADO
# =========================
if "usuario_logado"            not in st.session_state:
    st.session_state.usuario_logado = None
if "lista_publicacoes"         not in st.session_state:
    st.session_state.lista_publicacoes = carregar_publicacoes()
if "suspensoes_por_tribunal"   not in st.session_state:
    st.session_state.suspensoes_por_tribunal = carregar_suspensoes()
if "lista_audiencias"          not in st.session_state:
    st.session_state.lista_audiencias = carregar_audiencias()
if "lista_clientes"            not in st.session_state:
    st.session_state.lista_clientes = carregar_clientes()
if "lista_financeiro"          not in st.session_state:
    st.session_state.lista_financeiro = carregar_financeiro()
if "menu_selecionado"          not in st.session_state:
    st.session_state.menu_selecionado = "📥 Entrada de Dados"
if "pagina_processo_aberto"    not in st.session_state:
    st.session_state.pagina_processo_aberto = None
if "pagina_cliente_aberto"     not in st.session_state:
    st.session_state.pagina_cliente_aberto = None
if "ultimo_processamento"      not in st.session_state:
    st.session_state.ultimo_processamento = None
if "admin_usuario_visualizado" not in st.session_state:
    st.session_state.admin_usuario_visualizado = None
if "cal_mes"                   not in st.session_state:
    st.session_state.cal_mes = date.today().month
if "cal_ano"                   not in st.session_state:
    st.session_state.cal_ano = date.today().year
if "lista_financeiro"          not in st.session_state:
    st.session_state.lista_financeiro = carregar_financeiro()
if "lista_tarefas"             not in st.session_state: 
    st.session_state.lista_tarefas = carregar_tarefas()

# =========================
# LOGIN E INICIALIZAÇÃO DE ESTADO
# =========================
controller = CookieController()

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

# Tenta logar automaticamente se existir o cookie salvo no navegador
if st.session_state.usuario_logado is None:
    usuario_salvo = None
    try:
        usuario_salvo = controller.get('jurismind_logado')
    except TypeError:
        # Ignora o erro silenciosamente se o frontend ainda não tiver carregado os cookies
        pass
        
    if usuario_salvo:
        # Procura o usuário no banco de dados para confirmar
        u_encontrado = next((u for u in carregar_usuarios() if u["usuario"] == usuario_salvo), None)
        if u_encontrado:
            st.session_state.usuario_logado = u_encontrado
            st.session_state.escritorio_id = u_encontrado["escritorio_id"]
            
            # Carrega os dados silenciosamente
            st.session_state.lista_publicacoes = carregar_publicacoes()
            st.session_state.lista_audiencias = carregar_audiencias()
            st.session_state.lista_clientes = carregar_clientes()
            st.session_state.lista_financeiro = carregar_financeiro()
            st.session_state.lista_tarefas = carregar_tarefas()
            st.session_state.suspensoes_por_tribunal = carregar_suspensoes()
            st.session_state.ultimo_processamento = None
            if "menu_selecionado" not in st.session_state:
                st.session_state.menu_selecionado = "📥 Entrada de Dados"

# ==========================================
# TELA DE LOGIN VISUAL (Se não tiver cookie)
# ==========================================
if st.session_state.usuario_logado is None:
    st.markdown("""
        <style>
        /* 1. Fundo Escuro da Tela Inteira */
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at top left, #1e293b 0%, #0f172a 100%) !important;
        }
        /* 2. Transformar o Formulário num Cartão Branco (Como na Amostra) */
        [data-testid="stForm"] {
            background-color: white !important;
            padding: 40px !important;
            border-radius: 24px !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
            border: none !important;
        }
        /* 3. Textos dentro do formulário ficam escuros para dar contraste */
        [data-testid="stForm"] * {
            color: #1e293b !important;
        }
        /* 4. Forçar o Botão de Autenticar a ser AZUL JurisMind */
        [data-testid="stForm"] button {
            background-color: #2563eb !important;
            border: none !important;
            border-radius: 8px !important;
            margin-top: 15px !important;
            padding: 10px !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stForm"] button * {
            color: white !important;
            font-weight: bold !important;
            font-size: 16px !important;
        }
        [data-testid="stForm"] button:hover {
            background-color: #1d4ed8 !important;
            transform: translateY(-2px) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    
    with col_login:
        st.write("") 
        st.write("")
        st.markdown("<h1 style='text-align: center; color: white; font-size: 3rem;'>⚖️ JurisMind</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Inteligência e Gestão para Advocacia</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("<h2 style='color: #1e293b; text-align: center; margin-bottom: 20px;'>Login</h2>", unsafe_allow_html=True)
            usuario = st.text_input("Usuário", placeholder="O seu nome de utilizador")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            submit = st.form_submit_button("AUTENTICAR", use_container_width=True)
            
            if submit:
                u = autenticar(usuario.strip(), senha.strip())
                if u:
                    st.session_state.usuario_logado = u
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
    st.stop()

# ==========================================
# VARIÁVEIS GLOBAIS DO USUÁRIO LOGADO
# ==========================================
usr_atual = st.session_state.usuario_logado["usuario"]
nom_atual = st.session_state.usuario_logado.get("nome_completo", usr_atual)
oab_atual = st.session_state.usuario_logado.get("oab", "")
oab_uf_atual = st.session_state.usuario_logado.get("oab_uf", "RJ") # <--- AGORA O SISTEMA SABE A UF
papel_atual = st.session_state.usuario_logado.get("papel", "Sócio")
is_admin = st.session_state.usuario_logado.get("admin", False)

# =========================
# REGRAS DE VISÃO (RBAC) E TRIAGEM OAB
# =========================
def meus_processos() -> list:
    """Sócios e Controladores veem tudo. Associados veem apenas os seus."""
    dono = st.session_state.get("admin_usuario_visualizado") or usr_atual
    if papel_atual in ["Sócio", "Controlador"] or is_admin:
        return st.session_state.lista_publicacoes
    return [p for p in st.session_state.lista_publicacoes if p.get("usuario_dono", "") == dono]

def minhas_audiencias() -> list:
    dono = st.session_state.get("admin_usuario_visualizado") or usr_atual
    if papel_atual in ["Sócio", "Controlador"] or is_admin:
        return st.session_state.lista_audiencias
    return [a for a in st.session_state.lista_audiencias if a.get("usuario_dono", "") == dono]

def meus_clientes() -> list:
    dono = st.session_state.get("admin_usuario_visualizado") or usr_atual
    if papel_atual in ["Sócio", "Controlador"] or is_admin:
        return st.session_state.lista_clientes
    return [c for c in st.session_state.lista_clientes if c.get("usuario_dono", "") == dono]

def meu_financeiro() -> list:
    dono = st.session_state.get("admin_usuario_visualizado") or usr_atual
    if papel_atual in ["Sócio", "Controlador"] or is_admin:
        return st.session_state.lista_financeiro
    return [r for r in st.session_state.lista_financeiro if r.get("usuario_dono", "") == dono]

def descobrir_dono_por_oab(texto_publicacao: str) -> str:
    """
    Escaneia a publicação. Se achar a OAB de um Associado, envia para ele.
    Se não achar, envia para o Sócio do escritório.
    """
    escritorio_atual = st.session_state.escritorio_id
    equipe = [u for u in carregar_usuarios() if u.get("escritorio_id") == escritorio_atual and u.get("ativo", True)]
    texto_upper = texto_publicacao.upper()
    
    # 1. Tenta encontrar a OAB da equipe no texto
    for u in equipe:
        oab = str(u.get("oab", "")).strip().upper()
        if oab and oab in texto_upper:
            return u["usuario"] # Achou a OAB do associado/sócio
            
    # 2. Se não achou nenhuma OAB, delega para um Sócio.
    socios = [u for u in equipe if u.get("papel") == "Sócio"]
    if socios:
        if any(s["usuario"] == usr_atual for s in socios): return usr_atual
        return socios[0]["usuario"]
    return usr_atual

# =========================
# REGRAS DE VISÃO (RBAC) E TRIAGEM
# =========================
def meus_processos() -> list:
    """Sócios e Controladores veem tudo. Associados veem apenas os seus."""
    dono = st.session_state.get("admin_usuario_visualizado") or usr_atual
    if papel_atual in ["Sócio", "Controlador"] or is_admin:
        return st.session_state.lista_publicacoes
    return [p for p in st.session_state.lista_publicacoes if p.get("usuario_dono", "") == dono]

# Aplique a mesma lógica do `if papel_atual in ["Sócio", "Controlador"]:` para minhas_audiencias, meus_clientes e meu_financeiro.

def descobrir_dono_por_oab(texto_publicacao: str) -> str:
    """
    Escaneia a publicação. Se achar a OAB de um Associado, envia para ele.
    Se não achar, envia para o Sócio do escritório.
    """
    escritorio_atual = st.session_state.escritorio_id
    # Filtra toda a equipe daquele escritório
    equipe = [u for u in carregar_usuarios() if u.get("escritorio_id") == escritorio_atual and u.get("ativo", True)]
    
    texto_upper = texto_publicacao.upper()
    
    # 1. Tenta encontrar a OAB da equipe no texto
    for u in equipe:
        oab = str(u.get("oab", "")).strip().upper()
        if oab and oab in texto_upper:
            return u["usuario"] # Achou a OAB do associado/sócio! Delegado.
            
    # 2. Se não achou nenhuma OAB correspondente, delega para um Sócio.
    socios = [u for u in equipe if u.get("papel") == "Sócio"]
    if socios:
        # Se quem está importando é o sócio, fica para ele. Se for o controlador, vai pro primeiro sócio.
        if any(s["usuario"] == usr_atual for s in socios):
            return usr_atual
        return socios[0]["usuario"]
        
    return usr_atual # Último recurso

# =========================
# MESES PT-BR
# =========================
MESES_PTBR = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12
}
MESES_NOME = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

def _mes(s):
    return MESES_PTBR.get(s.lower().strip())

def _dt(d, m, a):
    try:    return date(a, m, d)
    except: return None

# =========================
# PDF TJRJ
# =========================

def extrair_suspensoes_com_ia(texto: str) -> list:
    """Usa a IA para ler a portaria e extrair datas, tribunal, comarca e abrangência."""
    prompt = f"""
    Você é um assistente jurídico. Leia a portaria abaixo e extraia apenas as suspensões de prazos processuais e feriados.
    
    REGRA DE OURO 1: IGNORE datas de assinatura, datas de cabeçalho ou datas de publicação (ex: "Rio de Janeiro, 15 de abril").
    REGRA DE OURO 2: Identifique se a suspensão é "Geral" (pausa a contagem de todos os processos) ou "Apenas início e fim" (afeta apenas prazos que começam ou vencem naquele dia).
    
    Retorne APENAS um JSON (uma lista de dicionários) com estas chaves exatas, sem nenhum texto extra antes ou depois:
    [
      {{
        "inicio": "DD/MM/AAAA",
        "fim": "DD/MM/AAAA",
        "tribunal": "Ex: TJRJ, TRF2, TJSP",
        "comarca": "Ex: Todas, Capital, Niterói",
        "abrangencia": "Geral ou Apenas inicio e fim",
        "descricao": "Motivo curto. Ex: Feriado local"
      }}
    ]
    
    TEXTO DA PORTARIA:
    {texto[:6000]}
    """
    try:
        raw = _chamar_groq(prompt)
        # Procura onde começa o colchete [ e termina com ] para isolar a tabela
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        return json.loads(raw)
    except Exception as e:
        print(f"Erro na IA ao extrair datas: {e}")
        return []

def _merge(lista):
    if not lista: return []
    lista = sorted(lista, key=lambda x: x["inicio"])
    m = [lista[0].copy()]
    for it in lista[1:]:
        if it["inicio"] <= m[-1]["fim"] + timedelta(days=1):
            m[-1]["fim"] = max(m[-1]["fim"], it["fim"])
        else:
            m.append(it.copy())
    return m

# =========================
# PARSER DO PDF DJEN
# =========================
def extrair_dados_djen(texto_pdf: str) -> dict:
    """
    Extrai campos estruturados do PDF do DJEN/TJRJ.
    Retorna dicionario com os dados encontrados.
    """
    dados = {
        "numero_processo": "",
        "classe":          "",
        "tribunal":        "",
        "orgao":           "",
        "tipo_documento":  "",
        "data_pub":        "",
        "advogados":       [],
        "conteudo":        texto_pdf.strip(),
        "certidao":        "",
    }

    # numero do processo
    m = re.search(
        r"N[uú]mero\s+do\s+processo\s*[:\-]?\s*([\d.\-/]+)",
        texto_pdf, re.IGNORECASE
    )
    if m:
        dados["numero_processo"] = m.group(1).strip()

    # classe
    m = re.search(r"Classe\s*[:\-]?\s*(.+?)(?:\n|Tribunal)", texto_pdf, re.IGNORECASE)
    if m:
        dados["classe"] = m.group(1).strip()

    # tribunal
    m = re.search(r"Tribunal\s*[:\-]?\s*(.+?)(?:\n|[OÓ]rg)", texto_pdf, re.IGNORECASE)
    if m:
        dados["tribunal"] = m.group(1).strip()

    # orgao
    m = re.search(r"[OÓ]rg[aã]o\s*[:\-]?\s*(.+?)(?:\n|Tipo)", texto_pdf, re.IGNORECASE)
    if m:
        dados["orgao"] = m.group(1).strip()

    # tipo de documento
    m = re.search(
        r"Tipo\s+de\s+documento\s*[:\-]?\s*(.+?)(?:\n|Disponibilizado)",
        texto_pdf, re.IGNORECASE
    )
    if m:
        dados["tipo_documento"] = m.group(1).strip()

    # data de disponibilizacao
    m = re.search(
        r"Disponibilizado\s+em\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        texto_pdf, re.IGNORECASE
    )
    if m:
        dados["data_pub"] = m.group(1).strip()
    else:
        # tenta formato alternativo
        m = re.search(
            r"Di[aá]rio.*?de\s+(\d{2}/\d{2}/\d{4})",
            texto_pdf, re.IGNORECASE
        )
        if m:
            dados["data_pub"] = m.group(1).strip()

    # advogados — pega todos os nomes OAB
    advs = re.findall(
        r"([A-Z][A-Z\s]+)\s*[-–]\s*OAB\s+[A-Z]+\s*[-–]?\s*(\d+)",
        texto_pdf
    )
    dados["advogados"] = [
        f"{nome.strip()} - OAB {num}" for nome, num in advs
    ]

    # codigo da certidao
    m = re.search(r"C[oó]digo\s+da\s+certid[aã]o\s*[:\-]?\s*(\S+)", texto_pdf, re.IGNORECASE)
    if m:
        dados["certidao"] = m.group(1).strip()

    # classifica tribunal
    trib_sistema = "Outros"
    trib_texto   = dados["tribunal"].upper() + dados["orgao"].upper()
    if "TJRJ" in trib_texto or "RIO DE JANEIRO" in trib_texto:
        trib_sistema = "TJRJ"
    elif "TRF" in trib_texto or "FEDERAL" in trib_texto:
        trib_sistema = "Federal"
    elif "TRT" in trib_texto or "TRABALHO" in trib_texto:
        trib_sistema = "Trabalhista"

    dados["tribunal_sistema"] = trib_sistema

    return dados


def processar_pdf_djen(uploaded_file) -> dict:
    """
    Le o PDF do DJEN e extrai os dados estruturados.
    Retorna os dados extraidos.
    """
    texto = extrair_texto_pdf(uploaded_file)
    return extrair_dados_djen(texto)

# =========================
# PRAZOS E CALCULADORA
# =========================
def _susp_ativa(d: date, ivs: list, comarca_processo: str = "Todas", is_marco: bool = False) -> bool:
    """Verifica se há suspensão ativa, respeitando a comarca e se é suspensão geral ou só de início/fim."""
    for it in ivs:
        ini = (it["inicio"] if isinstance(it["inicio"], date) else date.fromisoformat(it["inicio"]))
        fim = (it["fim"] if isinstance(it["fim"], date) else date.fromisoformat(it["fim"]))
        
        comarca_susp = it.get("comarca", "Todas")
        if comarca_susp != "Todas" and comarca_processo != "Todas":
            if comarca_susp.lower() != comarca_processo.lower():
                continue 
        
        if ini and fim and ini <= d <= fim:
            abrangencia = it.get("abrangencia", "Geral")
            if abrangencia == "Geral":
                return True 
            elif abrangencia == "Apenas inicio e fim" and is_marco:
                return True 
    return False

def calcular_prazo_completo(data_pub_str: str, dias_uteis: int, susp: list = None, comarca_processo: str = "Todas", tipo_contagem: str = "Dias Úteis") -> dict:
    """Calculadora completa: acha a data de publicação, início e o prazo fatal (Úteis ou Corridos)."""
    susp = susp or []
    fer  = holidays.BR(state="RJ")

    try:
        dt_disp = datetime.strptime(data_pub_str, "%d/%m/%Y")
    except:
        dt_disp = datetime.now()

    # Publicação oficial = 1º dia útil após disponibilização
    dt_pub = dt_disp + timedelta(days=1)
    while True:
        d = dt_pub.date()
        if (dt_pub.weekday() < 5 and d not in fer and not _susp_ativa(d, susp, comarca_processo, is_marco=True)):
            break
        dt_pub += timedelta(days=1)

    # Início da contagem = 1º dia útil após publicação
    dt_inicio = dt_pub + timedelta(days=1)
    while True:
        d = dt_inicio.date()
        if (dt_inicio.weekday() < 5 and d not in fer and not _susp_ativa(d, susp, comarca_processo, is_marco=True)):
            break
        dt_inicio += timedelta(days=1)

    # Contagem do Prazo
    dt_fatal  = dt_inicio - timedelta(days=1)
    contagem  = 0
    while contagem < dias_uteis:
        dt_fatal += timedelta(days=1)
        d = dt_fatal.date()
        
        if tipo_contagem == "Dias Úteis":
            if _susp_ativa(d, susp, comarca_processo, is_marco=False): 
                continue
            if dt_fatal.weekday() < 5 and d not in fer:
                contagem += 1
        else:
            # Dias Corridos
            contagem += 1
            
    # VALIDAÇÃO FINAL: Se o prazo acabar no fim de semana ou feriado, prorroga pro 1º dia útil
    while True:
        d = dt_fatal.date()
        if dt_fatal.weekday() >= 5 or d in fer or _susp_ativa(d, susp, comarca_processo, is_marco=True):
            dt_fatal += timedelta(days=1)
        else:
            break

    return {
        "data_disponibilizacao": dt_disp,
        "data_publicacao":       dt_pub,
        "inicio_contagem":       dt_inicio,
        "data_fatal":            dt_fatal,
        "dias_uteis":            dias_uteis,
        "suspensoes_aplicadas":  len(susp),
    }

def calcular_vencimento(data_str: str, dias: int, susp: list = None, comarca_processo: str = "Todas", tipo_contagem: str = "Dias Úteis") -> datetime:
    """Versão simplificada para agendamento rápido nos processos."""
    susp = susp or []
    try:    dt = datetime.strptime(data_str, "%d/%m/%Y")
    except: dt = datetime.now()
    fer = holidays.BR(state="RJ")
    c   = 0
    
    while c < dias:
        dt += timedelta(days=1)
        d   = dt.date()
        
        if tipo_contagem == "Dias Úteis":
            if _susp_ativa(d, susp, comarca_processo, is_marco=False): continue
            if dt.weekday() < 5 and d not in fer:
                c += 1
        else:
            c += 1
            
    while True:
        d = dt.date()
        if dt.weekday() >= 5 or d in fer or _susp_ativa(d, susp, comarca_processo, is_marco=True):
            dt += timedelta(days=1)
        else:
            break
    return dt

# =========================
# INTELIGÊNCIA ARTIFICIAL — GROQ (LLAMA 3)
# =========================
from groq import Groq
import re
import json

GROQ_API_KEY = "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"

def _chamar_groq(prompt: str) -> str:
    try:
        client = Groq(api_key=GROQ_API_KEY)
        resposta = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
        )
        return resposta.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Erro ao acessar Groq: {e}")

def gerar_resumos(texto: str) -> dict:
    prompt = f"""
Você é um assistente jurídico especialista na análise de decisões e contagem de prazos processuais brasileiros.
Sua tarefa é ler a decisão judicial fornecida, identificar a natureza da ação, e propor o prazo correto e a ação correspondente.

Siga rigorosamente esta ordem de análise:
1. Identificação de Prazo Assinalado (Prioridade Máxima):
Leia atentamente a decisão e verifique se o juiz concedeu um prazo expresso e específico (ex: "assinalo o prazo de 5 dias", "intime-se para manifestação em 48 horas"). Se houver, este é o prazo que deve ser proposto, independentemente do prazo geral da lei.
2. Identificação do Ramo do Direito:
Analise o teor da decisão para classificar o processo como: CÍVEL, CRIMINAL ou TRABALHISTA.
3. Aplicação da Regra Legal (Caso o juiz não tenha assinalado prazo diferente):
- Se CÍVEL: Siga estritamente o CPC. Identifique qual é o recurso ou petição cabível para aquela decisão e indique o prazo legal. A contagem deve ser obrigatoriamente em Dias Úteis.
- Se CRIMINAL: Siga estritamente o CPP (ou leis penais extravagantes). Identifique a peça cabível. A contagem deve ser obrigatoriamente em Dias Corridos.
- Se TRABALHISTA: Siga a CLT e, subsidiariamente, o CPC. A contagem deve ser em Dias Úteis (art. 775 da CLT).
4. Dados Complementares (Formato e Tamanho):
- Crie um resumo do processo detalhado (utilize no máximo 15 linhas).
- Na manifestação cabível, além do nome da peça, inclua uma explicação detalhada da ação sugerida (utilize no máximo 15 linhas).
- Extraia uma lista apenas com os nomes do Autor e do Réu.

Retorne APENAS um bloco JSON válido seguindo EXATAMENTE as chaves abaixo, sem formatação markdown ou textos extras:
{{
  "resumo_processo": "Resumo do processo em até 15 linhas",
  "partes": ["Nome 1", "Nome 2"],
  "ramo": "Cível, Criminal ou Trabalhista",
  "prazo_concedido_pelo_juiz": true,
  "quantidade_dias": 5,
  "tipo_contagem": "Dias Úteis ou Dias Corridos",
  "manifestacao_cabivel": "Nome da peça e explicação da ação sugerida em até 15 linhas",
  "fundamento_legal": "Artigo da lei ou menção ao juiz"
}}

TEXTO:
{str(texto)[:8000]}""".strip()

    try:
        raw = _chamar_groq(prompt)
        # Limpa qualquer texto extra que a IA possa enviar antes/depois do JSON
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
            
        dados = json.loads(raw)
        
        # Constrói o texto amigável que vai aparecer na interface
        ramo = dados.get("ramo", "Não identificado")
        peca_e_acao = dados.get("manifestacao_cabivel", "Requer análise manual")
        dias = dados.get("quantidade_dias", 15)
        contagem = dados.get("tipo_contagem", "Dias Úteis")
        fundamento = dados.get("fundamento_legal", "")
        juiz_deu_prazo = "📌 *Prazo fixado pelo Juiz*" if dados.get("prazo_concedido_pelo_juiz") else "⚖️ *Prazo Legal Padrão*"

        acao_montada = f"{juiz_deu_prazo}\n\n**Ação Sugerida:**\n{peca_e_acao}\n\n**Prazo:** {dias} {contagem} ({ramo})\n**Fundamento:** {fundamento}"
        
        return {
            "resumo_processo": dados.get("resumo_processo", "Resumo não gerado."),
            "acao_necessaria": acao_montada,
            "partes": dados.get("partes", []),
            "prazo_identificado": dias,
            "tipo_contagem": contagem # <--- Adicionamos a memória da IA aqui
        }
        
    except Exception as e:
        print(f"Erro no parse da IA: {e}")
        return {
            "resumo_processo": "Houve uma falha na interpretação da IA.",
            "acao_necessaria": "Verificar manualmente o conteúdo da publicação.",
            "partes": [],
            "prazo_identificado": 15
        }
    
# =========================
# PROCESSAMENTO OAB
# =========================
def processar_texto_oab(texto: str) -> list:
    blocos = re.split(r"Publicacao:\s*\d+|Publicação:\s*\d+", texto)
    novos  = []
    for bloco in blocos:
        if "PROCESSO:" not in bloco:
            continue
        pm   = re.search(r"PROCESSO:\s*([\d.\-/]+)", bloco)
        dm   = re.search(
            r"Data de Publicacao:\s*(\d{2}/\d{2}/\d{4})|"
            r"Data de Publicação:\s*(\d{2}/\d{2}/\d{4})", bloco)
        num  = pm.group(1).strip() if pm else "S/N"
        dpub = ((dm.group(1) or dm.group(2)) if dm
                else datetime.now().strftime("%d/%m/%Y"))
        ch   = f"{num}_{dpub}_{usr_atual}"

        trib = "Outros"
        if "TJRJ"  in bloco: trib = "TJRJ"
        elif "TRF" in bloco: trib = "Federal"
        elif "TRT" in bloco or "Trabalho" in bloco: trib = "Trabalhista"

        if not any(p["chave"] == ch for p in st.session_state.lista_publicacoes):
            cli_match = _cliente_por_processo(num)
            novos.append({
                "chave":       ch,
                "processo":    num,
                "data_pub":    dpub,
                "tribunal":    trib,
                "conteudo":    bloco.strip(),
                "analisado":   False,
                "resumo_processo": "",
                "resumo_manual":   "",
                "acao_necessaria": "",
                "minuta_gerada":   "",
                "tipo_peca":       "",
                "data_fatal":      None,
                "dias_prazo":      0,
                "usuario_dono":    usr_atual,
                "cliente_id":      cli_match["id"] if cli_match else "",
                "fonte":           "texto",
            })
    return novos

# =========================
# INTEGRAÇÃO COM DJEN (API COMUNICA)
# =========================
def consultar_api_djen(oab=None, processo=None, data_ini=None, data_fim=None):
    """Consulta a API Pública do DJEN com tolerância maior de tempo."""
    url = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
    params = {}
    
    if oab:
        # Remove espaços e traços, mas MATÉM as letras da UF (ex: RJ123456)
        params["numeroOab"] = re.sub(r'[^A-Za-z0-9]', '', str(oab)).upper()
    if processo:
        params["numeroProcesso"] = re.sub(r'\D', '', str(processo))
    if data_ini:
        params["dataDisponibilizacaoInicio"] = data_ini.strftime("%Y-%m-%d")
    if data_fim:
        params["dataDisponibilizacaoFim"] = data_fim.strftime("%Y-%m-%d")

    headers = {"Accept": "application/json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=90)
        
        if resp.status_code == 200:
            return resp.json().get("items", [])
        else:
            st.error(f"⚠️ O Governo recusou a busca! Código: {resp.status_code} | Motivo: {resp.text}")
            return []
            
    except Exception as e:
        st.error(f"Falha de comunicação ou lentidão no servidor do DJEN: {e}")
        return []

def integrar_resultados_djen(itens_djen, usuario_dono):
    """Filtra, formata e salva os dados da API com extração profunda de Partes e Processo."""
    novos_adicionados = []
    for item in itens_djen:
        # 1. Extração Blindada do Número do Processo
        num_proc_raw = item.get("numeroProcesso") or item.get("numero_processo") or ""
        if not num_proc_raw and item.get("numerosProcessos"): # Caso a API mande uma lista
            num_proc_raw = item.get("numerosProcessos")[0]
            
        num_proc = str(num_proc_raw).strip()
        
        # Formatação Padrão CNJ
        apenas_numeros = re.sub(r'\D', '', num_proc)
        if len(apenas_numeros) == 20:
            num_proc = f"{apenas_numeros[:7]}-{apenas_numeros[7:9]}.{apenas_numeros[9:13]}.{apenas_numeros[13]}.{apenas_numeros[14:16]}.{apenas_numeros[16:]}"
        elif not num_proc:
            num_proc = "S/N"
            
        # 2. Resgate do texto para caçar informações caso a API falhe
        texto_pub = item.get("texto") or item.get("conteudo") or ""
        
        # Se mesmo assim vier S/N, a IA "caça" o processo dentro do texto do despacho
        if num_proc == "S/N":
            m = re.search(r'([\d]{7}-[\d]{2}\.[\d]{4}\.[\d]\.[\d]{2}\.[\d]{4})', texto_pub)
            if m:
                num_proc = m.group(1)

        # 3. Extração dos Nomes das Partes (Destinatários)
        partes_lista = []
        destinatarios = item.get("destinatarios") or item.get("destinatario_advogados") or []
        for d in destinatarios:
            nome_parte = d.get("nome") or d.get("nomeDestinatario") or ""
            if nome_parte:
                # Limpa e formata como Título (Iniciais Maiúsculas)
                partes_lista.append(nome_parte.strip().title())

        # 4. Extração de Data
        data_disp_raw = item.get("dataDisponibilizacao") or item.get("data_disponibilizacao") or ""
        try:
            data_disp_dt = datetime.strptime(data_disp_raw[:10], "%Y-%m-%d").date()
            data_disp_str = data_disp_dt.strftime("%d/%m/%Y")
        except:
            data_disp_str = date.today().strftime("%d/%m/%Y")
            
        # 5. Chave de Segurança Blindada (Evita duplicatas futuras)
        id_djen_bruto = str(item.get("id") or item.get("id_comunicacao") or "")
        # Se a API do governo falhar e não mandar o ID, criamos um Hash Matemático exato do texto
        if not id_djen_bruto:
            texto_limpo = re.sub(r'\W+', '', texto_pub)[:150]
            id_djen_bruto = hashlib.md5(f"{num_proc}{data_disp_str}{texto_limpo}".encode('utf-8')).hexdigest()
            
        ch = f"{num_proc}_{data_disp_str}_{usuario_dono}_{id_djen_bruto}"
        
        if any(p["chave"] == ch for p in st.session_state.lista_publicacoes):
            continue
            
        # 6. Metadados e Construção do Bloco de Texto
        tribunal = item.get("siglaTribunal") or item.get("sigla_tribunal") or "Outros"
        orgao = item.get("nomeOrgao") or item.get("nome_orgao") or ""
        tipo = item.get("tipoComunicacao") or item.get("tipo_comunicacao") or "Comunicação"
        
        partes_str = " | ".join(partes_lista) if partes_lista else "Não informadas pela API"
        
        conteudo_fmt = (
            f"PROCESSO: {num_proc}\n"
            f"PARTES: {partes_str}\n"
            f"Tribunal: {tribunal} - {orgao}\n"
            f"Tipo de Ato: {tipo}\n"
            f"Data Disponibilização: {data_disp_str}\n\n"
            f"{texto_pub}"
        )
        
        cli_match = _cliente_por_processo(num_proc)
        
        novo = {
            "chave": ch,
            "processo": num_proc,
            "data_pub": data_disp_str,
            "tribunal": "Federal" if "TRF" in tribunal else ("Trabalhista" if "TRT" in tribunal else "TJRJ"),
            "conteudo": conteudo_fmt,
            "partes": partes_lista, 
            "analisado": False,
            "resumo_processo": "",
            "resumo_manual": "",
            "acao_necessaria": "",
            "minuta_gerada": "",
            "tipo_peca": "",
            "data_fatal": None,
            "dias_prazo": 0,
            "usuario_dono": usuario_dono,
            "cliente_id": cli_match["id"] if cli_match else "",
            "fonte": "api_djen",
            "id_djen": id_djen_bruto # <--- A CORREÇÃO FOI FEITA AQUI
        }
        
        st.session_state.lista_publicacoes.append(novo)
        novos_adicionados.append(novo)
        
    if novos_adicionados:
        salvar_publicacoes()
    return novos_adicionados

def gatilho_busca_automatica_fds():
    """Roda a busca automaticamente de madrugada no fim de semana."""
    hoje = date.today()
    # Verifica se é Sábado (5) ou Domingo (6)
    if hoje.weekday() in [5, 6]:
        arquivo_controle = obter_caminho("ultima_busca_djen.txt")
        ja_rodou = False
        if os.path.exists(arquivo_controle):
            with open(arquivo_controle, "r") as f:
                if f.read().strip() == hoje.isoformat():
                    ja_rodou = True
                    
        if not ja_rodou and oab_atual:
            data_ini = hoje - timedelta(days=7)
            # Executa a busca invisível
            itens = consultar_api_djen(oab=oab_atual, processo=None, data_ini=data_ini, data_fim=hoje)
            if itens:
                integrar_resultados_djen(itens, usr_atual)
            # Salva que já rodou hoje
            with open(arquivo_controle, "w") as f:
                f.write(hoje.isoformat())

# =========================
# CALENDARIO VISUAL
# =========================
def render_calendario(mes: int, ano: int):
    fer_rj   = _feriados_rj_ano(ano)
    susp_all = _todas_suspensoes()

    prazos_mes = {}
    for p in meus_processos():
        dt = _get_dt(p)
        if dt and dt.month == mes and dt.year == ano:
            d = dt.date()
            prazos_mes.setdefault(d, []).append(p["processo"])

    aud_mes = {}
    for a in minhas_audiencias():
        d_aud = a.get("data")
        if isinstance(d_aud, str):
            try:    d_aud = date.fromisoformat(d_aud)
            except: continue
        if d_aud and d_aud.month == mes and d_aud.year == ano:
            aud_mes.setdefault(d_aud, []).append(a.get("tipo", ""))

    suspensos = set()
    for it in susp_all:
        ini = (it["inicio"] if isinstance(it["inicio"], date)
               else date.fromisoformat(it["inicio"]))
        fim = (it["fim"] if isinstance(it["fim"], date)
               else date.fromisoformat(it["fim"]))
        if ini and fim:
            d = ini
            while d <= fim:
                if d.month == mes and d.year == ano:
                    suspensos.add(d)
                d += timedelta(days=1)

    primeiro_dia = date(ano, mes, 1)
    num_dias     = cal_module.monthrange(ano, mes)[1]
    inicio_sem   = primeiro_dia.weekday()

    st.markdown("""
    <style>
    .cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:16px;}
    .cal-header{background:#1e3a5f;color:white;text-align:center;
                padding:8px 4px;border-radius:4px;font-weight:bold;font-size:12px;}
    .cal-day{background:white;border:1px solid #e0e0e0;border-radius:6px;
             padding:6px;min-height:85px;font-size:11px;}
    .cal-day-num{font-weight:bold;font-size:14px;margin-bottom:3px;}
    .cal-empty{background:#f8f9fa;border:1px solid #f0f0f0;
               border-radius:6px;min-height:85px;}
    .cal-feriado{background:#fff3cd;border-color:#ffc107;}
    .cal-suspenso{background:#f8d7da;border-color:#dc3545;}
    .cal-hoje{border:2px solid #0d6efd !important;}
    .badge-prazo{background:#dc3545;color:white;border-radius:3px;
                 padding:1px 4px;margin:1px 0;display:block;font-size:9px;
                 overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    .badge-aud{background:#198754;color:white;border-radius:3px;
               padding:1px 4px;margin:1px 0;display:block;font-size:9px;}
    .badge-fer{background:#fd7e14;color:white;border-radius:3px;
               padding:1px 4px;margin:1px 0;display:block;font-size:9px;
               overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    .badge-susp{background:#6c757d;color:white;border-radius:3px;
                padding:1px 4px;margin:1px 0;display:block;font-size:9px;}
    </style>
    """, unsafe_allow_html=True)

    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
    html = '<div class="cal-grid">'
    for ds in dias_semana:
        html += f'<div class="cal-header">{ds}</div>'
    for _ in range(inicio_sem):
        html += '<div class="cal-empty"></div>'

    hoje     = date.today()
    fer_dict = holidays.BR(state="RJ", years=ano)

    for dia_num in range(1, num_dias + 1):
        d       = date(ano, mes, dia_num)
        is_fer  = d in fer_rj
        is_susp = d in suspensos
        is_hoje = d == hoje
        is_fim  = d.weekday() >= 5

        classes = "cal-day"
        if is_susp:  classes += " cal-suspenso"
        elif is_fer: classes += " cal-feriado"
        if is_hoje:  classes += " cal-hoje"

        cor_num = "#6c757d" if is_fim else "#1e3a5f"
        html += f'<div class="{classes}">'
        html += (f'<div class="cal-day-num" '
                 f'style="color:{cor_num}">{dia_num}</div>')

        if is_fer:
            nome_fer = fer_dict.get(d, "Feriado")
            html += f'<span class="badge-fer">{str(nome_fer)[:16]}</span>'
        if is_susp and not is_fer:
            html += '<span class="badge-susp">Suspenso</span>'
        for proc in prazos_mes.get(d, []):
            # Procura o processo inteiro na sua base de dados
            proc_obj = next((p for p in meus_processos() if p["processo"] == proc), None)
            
            if proc_obj:
                # Se achou, cria um Link de internet (a href) disfarçado de botão
                html += f'<a href="/?proc={proc_obj["chave"]}" target="_self" style="text-decoration:none;"><span class="badge-prazo" style="cursor:pointer;">⚖️ Prazo: {proc[:12]}</span></a>'
            else:
                # Se der algum erro e não achar, mostra o balão normal sem link
                html += f'<span class="badge-prazo">Prazo: {proc[:12]}</span>'
        for tipo in aud_mes.get(d, []):
            html += f'<span class="badge-aud">Aud: {tipo[:12]}</span>'
        html += '</div>'

    ultimo_dia = date(ano, mes, num_dias)
    restante   = 6 - ultimo_dia.weekday()
    for _ in range(restante):
        html += '<div class="cal-empty"></div>'
    html += '</div>'

    html += """
    <div style="display:flex;gap:10px;flex-wrap:wrap;
                margin-top:6px;font-size:11px;">
    <span style="background:#dc3545;color:white;
                 padding:2px 8px;border-radius:3px;">Prazo fatal</span>
    <span style="background:#198754;color:white;
                 padding:2px 8px;border-radius:3px;">Audiencia</span>
    <span style="background:#fd7e14;color:white;
                 padding:2px 8px;border-radius:3px;">Feriado</span>
    <span style="background:#6c757d;color:white;
                 padding:2px 8px;border-radius:3px;">Suspenso</span>
    <span style="background:#fff3cd;color:#333;padding:2px 8px;
                 border-radius:3px;border:1px solid #ffc107;">
                 Fundo amarelo = Feriado</span>
    <span style="background:#f8d7da;color:#333;padding:2px 8px;
                 border-radius:3px;border:1px solid #dc3545;">
                 Fundo vermelho = Suspenso</span>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

# --- Ativa a busca silenciosa do DJEN aos fins de semana ---
gatilho_busca_automatica_fds()

# =========================
# SIDEBAR
# =========================
st.sidebar.title("JurisMind Pro")
st.sidebar.markdown(f"**{nom_atual}**")
if oab_atual: st.sidebar.caption(f"OAB/{oab_uf_atual} {oab_atual}")
if is_admin:  st.sidebar.caption("Administrador")
st.sidebar.markdown("---")

meus = meus_processos()
qtd_meus = len(meus)
qtd_cli = len(meus_clientes())
qtd_prazo = len([p for p in meus if isinstance(p.get("data_fatal"), (date, datetime)) and not p.get("cumprido")])
qtd_aud = len(minhas_audiencias())

# Bloqueia os botões rápidos para o Master para não quebrar a navegação dele
if papel_atual != "Master":
    st.sidebar.markdown("**Painel Rápido (Clique para abrir):**")
    
    if st.sidebar.button(f"📂 Meus processos: {qtd_meus}", use_container_width=True, key="btn_sb_proc"):
        st.session_state.pagina_processo_aberto = None
        st.session_state.pagina_cliente_aberto = None
        st.session_state.menu_selecionado = "📥 Entrada de Dados"
        st.rerun()

    if st.sidebar.button(f"👥 Clientes: {qtd_cli}", use_container_width=True, key="btn_sb_cli"):
        st.session_state.pagina_processo_aberto = None
        st.session_state.pagina_cliente_aberto = None
        st.session_state.menu_selecionado = "👥 Clientes"
        st.rerun()

    if st.sidebar.button(f"🚨 Com prazo: {qtd_prazo}", use_container_width=True, key="btn_sb_prz"):
        st.session_state.pagina_processo_aberto = None
        st.session_state.pagina_cliente_aberto = None
        st.session_state.menu_selecionado = "📥 Entrada de Dados"
        st.rerun()

    if st.sidebar.button(f"⚖️ Audiencias: {qtd_aud}", use_container_width=True, key="btn_sb_aud"):
        st.session_state.pagina_processo_aberto = None
        st.session_state.pagina_cliente_aberto = None
        st.session_state.menu_selecionado = "⚖️ Audiencias"
        st.rerun()

st.sidebar.markdown("---")

# ==========================================
# CALCULADORA RÁPIDA (MENU LATERAL)
# ==========================================
with st.sidebar.expander("🧮 Calculadora Rápida", expanded=False):
    st.caption("Cálculo ágil de prazos")
    
    # 1. Datas e Dias
    calc_data_lat = st.date_input("Disponibilização:", value=date.today(), key="calc_data_lat")
    calc_dias_lat = st.number_input("Dias:", min_value=1, value=15, key="calc_dias_lat")
    
    # 2. Configurações Inteligentes (Cível vs Criminal / Jurisdição)
    calc_modo_lat = st.selectbox("Contagem:", ["Dias Úteis", "Dias Corridos"], key="calc_modo_lat")
    calc_trib_lat = st.selectbox("Tribunal:", LISTA_TRIBUNAIS, key="calc_trib_lat")
    
    # 3. Integração com IBGE
    calc_uf_lat = st.selectbox("UF da Comarca:", ["Todas"] + UFS_BRASIL, key="calc_uf_lat")
    lista_cidades_lat = buscar_cidades_por_uf(calc_uf_lat)
    calc_comarca_lat = st.selectbox("Comarca:", lista_cidades_lat, key="calc_comarca_lat")

    # 4. Botão e Lógica de Cálculo
    if st.button("Calcular Prazo", use_container_width=True, key="calc_btn_lat", type="primary"):
        # Pega as suspensões do tribunal escolhido + as gerais (Todos)
        susp_esp_lat = st.session_state.suspensoes_por_tribunal.get(calc_trib_lat, [])
        susp_tod_lat = st.session_state.suspensoes_por_tribunal.get("Todos", [])
        susp_lat = susp_esp_lat + susp_tod_lat

        # Chama a nossa função mestra
        res_lat = calcular_prazo_completo(
            calc_data_lat.strftime("%d/%m/%Y"), 
            calc_dias_lat, 
            susp_lat, 
            calc_comarca_lat, 
            calc_modo_lat
        )
        
        # Exibe o resultado bonitão no próprio menu lateral
        st.divider()
        st.markdown(f"**Início da Contagem:** {res_lat['inicio_contagem'].strftime('%d/%m/%Y')}")
        st.error(f"**Vencimento Final:** {res_lat['data_fatal'].strftime('%d/%m/%Y')}")
        if res_lat['suspensoes_aplicadas'] > 0:
            st.caption(f"⚠️ {res_lat['suspensoes_aplicadas']} suspensão(ões) aplicada(s) neste cálculo.")

if (st.session_state.pagina_processo_aberto or st.session_state.pagina_cliente_aberto):
    st.sidebar.info("Visualizando registro")
    # Adicionado ID fixo (key) ao botão de voltar
    if st.sidebar.button("Voltar ao Menu", key="btn_sb_voltar_menu"):
        st.session_state.pagina_processo_aberto = None
        st.session_state.pagina_cliente_aberto  = None
        st.rerun()
else:
    if papel_atual == "Master":
        opcoes_menu = ["👑 Painel Master"]
    else:
        opcoes_menu = [
            "📥 Entrada de Dados",
            "⏳ Tarefas em Aberto",      
            "✅ Tarefas Concluídas",
            "👥 Clientes",
            "🗓️ Calendario",
            "📊 Relatórios",
            "⚖️ Audiências",
            "📄 Suspensões de Prazo (PDF)",
            "🏛️ TJRJ", "🏛️ Federal", "🏛️ Trabalhista", "🏛️ Outros",
            "🧮 Calculadora de Prazos",
            "🔑 Alterar Senha",
        ]
        if papel_atual in ["Sócio", "Controlador"]: opcoes_menu.insert(4, "💰 Financeiro") 
        if papel_atual == "Sócio": opcoes_menu.append("⚙️ Administracao")

    st.sidebar.radio("Navegar por:", opcoes_menu, key="menu_selecionado")

st.sidebar.markdown("---")

if st.session_state.admin_usuario_visualizado and is_admin:
    st.sidebar.warning(f"Vendo: **{st.session_state.admin_usuario_visualizado}**")
    # Adicionado ID fixo (key) ao botão
    if st.sidebar.button("Voltar p/ meus dados", key="btn_sb_voltar_dados"):
        st.session_state.admin_usuario_visualizado = None
        st.rerun()

# A PRINCIPAL CORREÇÃO: ID fixo no botão Sair para evitar o Clique Fantasma
if st.sidebar.button("Sair do sistema", key="btn_sb_sair"):
    controller.remove('jurismind_logado') # DELETA O COOKIE DO NAVEGADOR
    
    st.session_state.usuario_logado = None
    st.session_state.pagina_processo_aberto = None
    st.session_state.pagina_cliente_aberto = None
    st.session_state.admin_usuario_visualizado = None
    time.sleep(0.5) # Dá meio segundo pro cookie ser apagado antes de recarregar
    st.rerun()

menu = st.session_state.menu_selecionado

# =========================
# PAGINA DO PROCESSO
# =========================
def pagina_processo(chave: str):
    pubs = [p for p in st.session_state.lista_publicacoes
            if p["chave"] == chave]
    if not pubs:
        st.error("Processo nao encontrado.")
        return

    pub = pubs[0]
    mesmo_proc = sorted(
        [p for p in meus_processos()
         if p["processo"] == pub["processo"]],
        key=lambda x: x.get("data_pub", "")
    )
    susp = (
        st.session_state.suspensoes_por_tribunal.get(pub["tribunal"], []) +
        st.session_state.suspensoes_por_tribunal.get("Todos", [])
    )
    cliente = (_cliente_por_id(pub.get("cliente_id", "")) or
               _cliente_por_processo(pub["processo"]))

    c1, c2 = st.columns([4, 1])
    with c1:
        st.title(f"Processo: {pub['processo']}")
        st.caption(
            f"Tribunal: **{pub['tribunal']}** | "
            f"Ultima pub.: {pub['data_pub']} | "
            f"{len(mesmo_proc)} publicacao(oes)"
        )
        if cliente:
            if st.button(f"Cliente: {cliente['nome']}",
                         key="btn_cli_proc"):
                st.session_state.pagina_cliente_aberto  = cliente["id"]
                st.session_state.pagina_processo_aberto = None
                st.rerun()
        else:
            st.caption("Cliente: nao vinculado")
    with c2:
        st.write("")
        st.write("")
        if st.button("Voltar", use_container_width=True):
            st.session_state.pagina_processo_aberto = None
            st.rerun()

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    dt_f = _get_dt(pub)
    m1.metric("Prazo Fatal",
              dt_f.strftime("%d/%m/%Y") if dt_f else "Nao agendado")
    m2.metric("Dias Uteis",  pub.get("dias_prazo", 0))
    m3.metric("IA",          "Analisado" if pub.get("analisado") else "Pendente")
    m4.metric("Minuta",      "Gerada" if pub.get("minuta_gerada") else "Nao gerada")
    st.divider()

    st.divider()
    dt_f = _get_dt(pub)
    
    # Prepara os textos
    str_prazo = dt_f.strftime("%d/%m/%Y") if dt_f else "Não agendado"
    str_ia = "Analisado" if pub.get("analisado") else "Pendente"
    str_minuta = "Gerada" if pub.get("minuta_gerada") else "Não gerada"
    
    # Cria as colunas com os nossos Cartões Premium!
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    
    with c_m1:
        cor_prazo = "#dc3545" if dt_f and dt_f.date() <= date.today() else ("#10b981" if dt_f else "#64748b")
        card_indicador("Prazo Fatal", str_prazo, "📅", cor_destaque=cor_prazo)
    with c_m2:
        card_indicador("Dias Úteis", str(pub.get("dias_prazo", 0)), "⏱️", cor_destaque="#2563eb")
    with c_m3:
        cor_ia = "#10b981" if pub.get("analisado") else "#f59e0b"
        card_indicador("Inteligência Art.", str_ia, "🤖", cor_destaque=cor_ia)
    with c_m4:
        cor_minuta = "#10b981" if pub.get("minuta_gerada") else "#64748b"
        card_indicador("Minuta", str_minuta, "📄", cor_destaque=cor_minuta)
    
    st.write("") # Espaço para respirar o design

    t_painel, t3, t4 = st.tabs([
        "🏠 Painel de Controle",
        "📄 Gerar Peça",
        "📜 Histórico"
    ])

    # ── ABA UNIFICADA (LADO A LADO) ──────────────────────────────────────────
    with t_painel:
        # Criamos duas colunas: a esquerda para texto e a direita para ferramentas
        col_pub, col_ia = st.columns([1.5, 1])

        with col_pub:
            st.subheader("📑 Publicações do Processo")
            for i, p in enumerate(mesmo_proc):
                with st.expander(
                    f"Publicação {i+1} — {p['data_pub']}",
                    expanded=(i == len(mesmo_proc) - 1)
                ):
                    st.markdown(f"""
                    <div style="background:#f1f3f6;padding:15px;border-radius:5px;border:1px solid #d1d5db;color:#1f2937;font-family:'Courier New',monospace;white-space:pre-wrap;max-height:350px;overflow-y:auto;">{p['conteudo']}</div>
                    """, unsafe_allow_html=True)
            
            st.divider()
            
            # Seção de Vínculo de Cliente
            st.subheader("👥 Vincular Cliente")
            partes_ia = pub.get("partes", [])
            
            # 1. Botões Inteligentes da IA
            if partes_ia and not pub.get("cliente_id"):
                st.info("A IA identificou estas partes. Clique para vincular:")
                cols_partes = st.columns(len(partes_ia))
                for i_p, nome_p in enumerate(partes_ia):
                    with cols_partes[i_p]:
                        if st.button(f"É meu cliente: {nome_p}", key=f"ia_cli_btn_{i_p}_{pub['chave']}"):
                            nome_limpo = nome_p.strip().title()
                            # Procura se o cliente já existe
                            cli_existente = next((c for c in meus_clientes() if c["nome"].lower() == nome_limpo.lower()), None)
                            
                            if cli_existente:
                                pub["cliente_id"] = cli_existente["id"]
                                if pub["processo"] not in cli_existente.setdefault("processos_vinculados", []):
                                    cli_existente["processos_vinculados"].append(pub["processo"])
                            else:
                                # Cria um cliente novo rápido
                                novo_cli = {
                                    "id": f"cli_{usr_atual}_{int(time.time())}",
                                    "nome": nome_limpo,
                                    "cpf": "", "rg": "", "email": "", "telefone": "",
                                    "processos_vinculados": [pub["processo"]],
                                    "usuario_dono": usr_atual
                                }
                                st.session_state.lista_clientes.append(novo_cli)
                                pub["cliente_id"] = novo_cli["id"]
                            
                            salvar_clientes()
                            salvar_publicacoes()
                            st.success(f"{nome_limpo} foi vinculado com sucesso!")
                            st.rerun()

            # 2. Seleção Manual pela Caixa de Texto (Selectbox)
            nomes_cli = ["(nenhum)"] + [f"{c['nome']} - CPF: {c['cpf']}" for c in meus_clientes()]
            idx_atual = 0
            if cliente:
                for i2, cx in enumerate(meus_clientes()):
                    if cx["id"] == pub.get("cliente_id", ""):
                        idx_atual = i2 + 1
                        break
                        
            sel_cli = st.selectbox("Selecione manualmente:", nomes_cli, index=idx_atual, key=f"sel_cli_unif_{pub['chave']}")
            
            if st.button("💾 Salvar Vínculo", key=f"sv_cli_unif_{pub['chave']}"):
                if sel_cli == "(nenhum)":
                    pub["cliente_id"] = ""
                else:
                    nome_sel = sel_cli.split(" - CPF:")[0].strip()
                    for cx in meus_clientes():
                        if cx["nome"] == nome_sel:
                            pub["cliente_id"] = cx["id"]
                            # Além de salvar no processo, salva o processo na ficha do cliente!
                            if pub["processo"] not in cx.setdefault("processos_vinculados", []):
                                cx["processos_vinculados"].append(pub["processo"])
                            salvar_clientes()
                            break
                
                salvar_publicacoes()
                st.success("Vínculo atualizado com sucesso!")
                time.sleep(0.5)
                st.rerun()

        with col_ia:
            # === SEÇÃO DE IA ===
            st.subheader("🤖 Análise Inteligente")
            if not pub.get("analisado"):
                st.info("Ainda não analisado.")
                if st.button("🚀 Iniciar Análise IA", key=f"btn_ia_start_final_{pub['chave']}", type="primary", use_container_width=True):
                    with st.spinner("Analisando..."):
                        try:
                            res = gerar_resumos(mesmo_proc[-1]["conteudo"])
                            pub["resumo_processo"] = res["resumo_processo"]
                            pub["acao_necessaria"] = res["acao_necessaria"]
                            pub["dias_prazo"] = res.get("prazo_identificado", 15)
                            pub["analisado"] = True
                            salvar_publicacoes()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
            else:
                st.markdown("**Resumo:**")
                st.info(pub.get("resumo_processo", "Sem resumo."))
                st.markdown("**Ação Sugerida:**")
                st.warning(pub.get("acao_necessaria", "Nenhuma ação."))
                if st.button("🔄 Refazer Análise", key=f"btn_ia_redo_final_{pub['chave']}"):
                    pub["analisado"] = False
                    salvar_publicacoes()
                    st.rerun()

            st.divider()

           # === SEÇÃO DE PRAZO ===
            st.subheader("📅 Agendamento")
            
            # Pega as sugestões da IA
            prazo_base = max(1, int(pub.get("dias_prazo", 15)))
            tipo_base = pub.get("tipo_contagem", "Dias Úteis")
            
            # O ALERTA INTELIGENTE PARA PROCESSOS CRIMINAIS
            if tipo_base == "Dias Corridos":
                st.error("🚨 **Atenção:** A IA identificou este processo como Criminal/Penal. A contagem sugerida é em **Dias Corridos**. Por favor, confirme abaixo.")
            
            with st.container(border=True):
                c_prazo1, c_prazo2 = st.columns(2)
                with c_prazo1:
                    p_dias = st.number_input("Quantidade de dias:", min_value=1, value=prazo_base, key=f"num_dias_final_{pub['chave']}")
                with c_prazo2:
                    p_tipo = st.radio("Modo de Contagem:", ["Dias Úteis", "Dias Corridos"], index=0 if tipo_base == "Dias Úteis" else 1, key=f"tipo_cont_final_{pub['chave']}")
                
                # Colunas para botões
                c_b1, c_b2 = st.columns(2)
                
                if c_b1.button("📌 Agendar Prazo", key=f"btn_age_unif_final_{pub['chave']}", type="primary", use_container_width=True):
                    pub["dias_prazo"] = int(p_dias)
                    pub["tipo_contagem"] = p_tipo # Salva a escolha do humano
                    
                    # Chama a função nova de cálculo que aceita dias corridos e comarcas
                    pub["data_fatal"] = calcular_vencimento(pub["data_pub"], pub["dias_prazo"], susp, "Todas", pub["tipo_contagem"])
                    
                    pub["cumprido"] = False
                    salvar_publicacoes()
                    st.rerun()

                if c_b2.button("⏭️ Dispensar", key=f"btn_disp_final_{pub['chave']}", use_container_width=True):
                    pub["data_fatal"] = "DISPENSADO"
                    pub["cumprido"] = True
                    pub["dias_prazo"] = 0
                    salvar_publicacoes()
                    st.success("Dispensado!")
                    time.sleep(0.5)
                    st.session_state.pagina_processo_aberto = None
                    st.rerun()
                
                st.divider()
                dt_fat = _get_dt(pub)
                if dt_fat:
                    st.metric(f"Vencimento Fatal ({pub.get('tipo_contagem', 'Dias Úteis')})", dt_fat.strftime("%d/%m/%Y"))
                    cump_check = st.checkbox("✅ Prazo Cumprido", value=pub.get("cumprido", False), key=f"chk_cump_final_{pub['chave']}")
                    if cump_check != pub.get("cumprido"):
                        pub["cumprido"] = cump_check
                        salvar_publicacoes()
                        st.rerun()
                elif pub.get("data_fatal") == "DISPENSADO":
                    st.info("⚡ Agendamento Dispensado")

            st.divider()
            st.subheader("📝 Anotações Rápidas")
            # CHAVE ÚNICA PARA AS NOTAS
            anot = st.text_area("Notas:", value=pub.get("resumo_manual", ""), height=100, key=f"area_anot_final_{pub['chave']}")
            if st.button("Salvar Notas", key=f"btn_salvar_anot_final_{pub['chave']}", use_container_width=True):
                pub["resumo_manual"] = anot
                salvar_publicacoes()
                st.success("Salvo!")
   

    # ── ABA 3 ──────────────────────────────────────────────
    with t3:
        st.subheader("Gerar Minuta de Peca Juridica")
        tp   = st.selectbox("Tipo:", TIPOS_PECA, key=f"tp_{pub['chave']}")
        inst = st.text_area(
            "Instrucoes adicionais (opcional):", height=100,
            key=f"it_{pub['chave']}",
            placeholder="Ex: Cliente alega pagamento realizado. Pedir tutela urgente..."
        )
        res_ia = pub.get("resumo_manual") or pub.get("resumo_processo") or ""

        if st.button(f"Gerar {tp}", key=f"gm_{pub['chave']}", type="primary"):
            with st.spinner(f"Gemini redigindo {tp}..."):
                try:
                    mt = gerar_minuta(
                        mesmo_proc[-1]["conteudo"], tp, inst, res_ia
                    )
                    pub["minuta_gerada"] = mt
                    pub["tipo_peca"]     = tp
                    salvar_publicacoes()
                    st.success("Minuta gerada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

        if pub.get("minuta_gerada"):
            st.markdown("---")
            st.subheader(f"{pub.get('tipo_peca', 'Peca Juridica')}")
            st.markdown(f"""
            <div style="background:#fffef0;padding:20px;
            border-radius:5px;border:1px solid #d4af37;
            color:#1f2937;font-family:Georgia,serif;
            white-space:pre-wrap;max-height:500px;
            overflow-y:auto;line-height:1.7;">
{pub['minuta_gerada']}</div>""", unsafe_allow_html=True)

            cd, cr = st.columns(2)
            cd.download_button(
                "Baixar .txt",
                pub["minuta_gerada"].encode("utf-8"),
                f"minuta_{pub['processo']}_{tp.replace(' ', '_')}.txt",
                "text/plain",
                key=f"dl_{pub['chave']}"
            )
            with cr:
                if st.button("Regenerar", key=f"rg_{pub['chave']}"):
                    pub["minuta_gerada"] = ""
                    salvar_publicacoes()
                    st.rerun()

    # ── ABA 4 ──────────────────────────────────────────────
    with t4:
        st.subheader(f"Historico — {pub['processo']}")
        df = pd.DataFrame([{
            "Data Pub.":   p["data_pub"],
            "Tribunal":    p["tribunal"],
            "Prazo Fatal": (_get_dt(p).strftime("%d/%m/%Y")
                            if _get_dt(p) else "—"),
            "IA":     "Sim" if p.get("analisado")     else "Nao",
            "Minuta": "Sim" if p.get("minuta_gerada") else "Nao",
        } for p in mesmo_proc])
        st.dataframe(df, use_container_width=True, hide_index=True)

# =========================
# PAGINA DO CLIENTE
# =========================
def pagina_cliente(cliente_id: str):
    clientes = [c for c in st.session_state.lista_clientes
                if c["id"] == cliente_id]
    if not clientes:
        st.error("Cliente nao encontrado.")
        return
    cli = clientes[0]

    c1, c2 = st.columns([4, 1])
    with c1:
        st.title(f"Cliente: {cli['nome']}")
        st.caption(f"CPF: {cli.get('cpf', '')} | Tel: {cli.get('telefone', '')}")
    with c2:
        st.write("")
        st.write("")
        if st.button("Voltar", use_container_width=True):
            st.session_state.pagina_cliente_aberto = None
            st.rerun()

    st.divider()

    procs_cli = [
        p for p in meus_processos()
        if (p.get("cliente_id") == cli["id"] or
            p.get("processo") in cli.get("processos_vinculados", []))
    ]
    fin_cli        = [r for r in meu_financeiro()
                      if r.get("cliente_id") == cli["id"]]
    total_esperado = sum(r.get("valor", 0) for r in fin_cli)
    total_recebido = sum(r.get("valor", 0) for r in fin_cli
                         if r.get("status") == "Recebido")

    m1, m2, m3 = st.columns(3)
    m1.metric("Processos",        len(procs_cli))
    m2.metric("Total honorarios", f"R$ {total_esperado:,.2f}")
    m3.metric("Total recebido",   f"R$ {total_recebido:,.2f}")

    st.divider()

    t1, t2, t3, t4 = st.tabs([
        "Dados Pessoais", "Processos", "Financeiro", "Editar"
    ])

    # ── DADOS PESSOAIS ─────────────────────────────────────
    with t1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Nome:** {cli.get('nome', '')}")
            st.markdown(f"**CPF:** {cli.get('cpf', '')}")
            st.markdown(f"**RG:** {cli.get('rg', '')}")
            st.markdown(f"**Nascimento:** {cli.get('data_nascimento', '')}")
            st.markdown(f"**E-mail:** {cli.get('email', '')}")
            st.markdown(f"**Telefone:** {cli.get('telefone', '')}")
            st.markdown(f"**Telefone 2:** {cli.get('telefone2', '')}")
        with col2:
            st.markdown(f"**CEP:** {cli.get('cep', '')}")
            st.markdown(
                f"**Logradouro:** {cli.get('logradouro', '')} "
                f"{cli.get('numero', '')}"
            )
            st.markdown(f"**Complemento:** {cli.get('complemento', '')}")
            st.markdown(f"**Bairro:** {cli.get('bairro', '')}")
            st.markdown(
                f"**Cidade/UF:** {cli.get('cidade', '')} / "
                f"{cli.get('estado', '')}"
            )
        if cli.get("observacoes"):
            st.info(f"Observacoes: {cli['observacoes']}")

    # ── PROCESSOS ──────────────────────────────────────────
    with t2:
        st.subheader("Processos Vinculados")
        if not procs_cli:
            st.info("Nenhum processo vinculado.")
        else:
            for p in sorted(procs_cli,
                            key=lambda x: x.get("data_pub", ""),
                            reverse=True):
                with st.container(border=True):
                    cc1, cc2, cc3 = st.columns([3, 2, 1])
                    dt     = _get_dt(p)
                    icone  = ("Gerada" if p.get("minuta_gerada") else
                              "Analisado" if p.get("analisado") else "Pendente")
                    with cc1:
                        st.markdown(f"**{p['processo']}** ({icone})")
                        st.caption(
                            f"Tribunal: {p['tribunal']} | "
                            f"Pub: {p['data_pub']}"
                        )
                    with cc2:
                        st.markdown(
                            f"**Prazo:** {dt.strftime('%d/%m/%Y')}"
                            if dt else "**Prazo:** nao agendado"
                        )
                    with cc3:
                        if st.button("Abrir", key=f"cli_p_{p['chave']}",
                                     use_container_width=True):
                            st.session_state.pagina_processo_aberto = p["chave"]
                            st.session_state.pagina_cliente_aberto  = None
                            st.rerun()

    # ── FINANCEIRO ─────────────────────────────────────────
    with t3:
        st.subheader("Honorarios e Recebiveis")

        with st.expander("Cadastrar novo lancamento", expanded=False):
            with st.container(border=True):
                fc1, fc2 = st.columns(2)
                with fc1:
                    f_proc = st.text_input(
                        "Processo:", key="f_proc",
                        value=(cli.get("processos_vinculados", [""])[0]
                               if cli.get("processos_vinculados") else "")
                    )
                    f_tipo = st.selectbox("Tipo de honorario:", [
                        "Preco certo (fixo)",
                        "Mensalidade recorrente",
                        "Percentual do exito",
                        "Adiantamento de custas",
                        "Outro"
                    ], key="f_tipo")
                    f_desc = st.text_input("Descricao:", key="f_desc")
                with fc2:
                    f_valor = st.number_input(
                        "Valor (R$):", min_value=0.0, step=100.0, key="f_val"
                    )
                    f_perc = st.number_input(
                        "Percentual (% sobre exito):",
                        min_value=0.0, max_value=100.0,
                        step=0.5, key="f_perc"
                    )
                    f_venc  = st.date_input(
                        "Vencimento:", key="f_venc", value=date.today()
                    )
                    f_recor = st.checkbox(
                        "Lancamento recorrente (mensal)?", key="f_recor"
                    )

                if st.button("Salvar lancamento", key="f_salvar",
                             type="primary"):
                    novo_lan = {
                        "id": (f"{cli['id']}_"
                               f"{date.today().isoformat()}_"
                               f"{len(st.session_state.lista_financeiro)}"),
                        "cliente_id":       cli["id"],
                        "processo":         f_proc.strip(),
                        "tipo":             f_tipo,
                        "descricao":        f_desc.strip(),
                        "valor":            float(f_valor),
                        "percentual":       float(f_perc),
                        "data_vencimento":  f_venc.isoformat(),
                        "data_recebimento": "",
                        "status":           "Pendente",
                        "recorrente":       f_recor,
                        "usuario_dono":     usr_atual,
                    }
                    st.session_state.lista_financeiro.append(novo_lan)
                    salvar_financeiro()
                    st.success("Lancamento salvo!")
                    st.rerun()

        if not fin_cli:
            st.info("Nenhum lancamento financeiro.")
        else:
            for r in sorted(fin_cli,
                            key=lambda x: x.get("data_vencimento", ""),
                            reverse=True):
                recebido = r.get("status") == "Recebido"
                with st.container(border=True):
                    lc1, lc2, lc3, lc4 = st.columns([3, 2, 2, 1])
                    with lc1:
                        cor = "Recebido" if recebido else "Pendente"
                        st.markdown(f"**{r.get('tipo', '')}** — {cor}")
                        st.caption(
                            f"{r.get('descricao', '')} | "
                            f"Proc: {r.get('processo', '')}"
                        )
                    with lc2:
                        st.metric("Valor", f"R$ {r.get('valor', 0):,.2f}")
                        if r.get("percentual"):
                            st.caption(f"Percentual: {r.get('percentual', 0)}%")
                    with lc3:
                        st.caption(f"Venc: {r.get('data_vencimento', '')}")
                        st.caption(f"Receb: {r.get('data_recebimento', '—')}")
                        if r.get("recorrente"):
                            st.caption("Recorrente")
                    with lc4:
                        if not recebido:
                            if st.button("Receber",
                                         key=f"rec_{r['id']}",
                                         use_container_width=True):
                                r["status"]           = "Recebido"
                                r["data_recebimento"] = date.today().isoformat()
                                salvar_financeiro()
                                st.rerun()
                        if st.button("Excluir",
                                     key=f"del_f_{r['id']}",
                                     use_container_width=True):
                            st.session_state.lista_financeiro = [
                                x for x in st.session_state.lista_financeiro
                                if x["id"] != r["id"]
                            ]
                            salvar_financeiro()
                            st.rerun()

    # ── EDITAR ─────────────────────────────────────────────
    with t4:
        st.subheader("Editar Dados do Cliente")
        with st.container(border=True):
            e1, e2 = st.columns(2)
            with e1:
                e_nome  = st.text_input("Nome completo:",
                                        value=cli.get("nome", ""), key="e_nome")
                e_cpf   = st.text_input("CPF:",
                                        value=cli.get("cpf", ""), key="e_cpf")
                e_rg    = st.text_input("RG:",
                                        value=cli.get("rg", ""), key="e_rg")
                e_nasc  = st.text_input("Nascimento (dd/mm/aaaa):",
                                        value=cli.get("data_nascimento", ""),
                                        key="e_nasc")
                e_email = st.text_input("E-mail:",
                                        value=cli.get("email", ""), key="e_email")
                e_tel   = st.text_input("Telefone:",
                                        value=cli.get("telefone", ""), key="e_tel")
                e_tel2  = st.text_input("Telefone 2:",
                                        value=cli.get("telefone2", ""), key="e_tel2")
            with e2:
                e_cep    = st.text_input("CEP:",
                                         value=cli.get("cep", ""), key="e_cep")
                e_log    = st.text_input("Logradouro:",
                                         value=cli.get("logradouro", ""), key="e_log")
                e_num    = st.text_input("Numero:",
                                         value=cli.get("numero", ""), key="e_num")
                e_comp   = st.text_input("Complemento:",
                                         value=cli.get("complemento", ""), key="e_comp")
                e_bairro = st.text_input("Bairro:",
                                         value=cli.get("bairro", ""), key="e_bairro")
                e_cid    = st.text_input("Cidade:",
                                         value=cli.get("cidade", ""), key="e_cid")
                estado_atual = cli.get("estado", "RJ").upper()
                idx_est = ESTADOS_BR.index(estado_atual) if estado_atual in ESTADOS_BR else 18
                e_est = st.selectbox("Estado (UF):", ESTADOS_BR, index=idx_est, key="e_est")
            e_obs = st.text_area("Observacoes:",
                                  value=cli.get("observacoes", ""),
                                  key="e_obs", height=80)

            if st.button("Salvar alteracoes", key="e_salvar", type="primary"):
                cli.update({
                    "nome":            e_nome.strip() or cli.get("nome", ""),
                    "cpf":             e_cpf.strip(),
                    "rg":              e_rg.strip(),
                    "data_nascimento": e_nasc.strip(),
                    "email":           e_email.strip(),
                    "telefone":        e_tel.strip(),
                    "telefone2":       e_tel2.strip(),
                    "cep":             e_cep.strip(),
                    "logradouro":      e_log.strip(),
                    "numero":          e_num.strip(),
                    "complemento":     e_comp.strip(),
                    "bairro":          e_bairro.strip(),
                    "cidade":          e_cid.strip(),
                    "estado":          e_est.strip(),
                    "observacoes":     e_obs.strip(),
                })
                salvar_clientes()
                st.success("Dados atualizados!")
                st.rerun()

# =========================
# ROTEADOR
# =========================
if st.session_state.pagina_processo_aberto:
    pagina_processo(st.session_state.pagina_processo_aberto)
    st.stop()

if st.session_state.pagina_cliente_aberto:
    pagina_cliente(st.session_state.pagina_cliente_aberto)
    st.stop()

# =========================
# CLIENTES (MENU)
# =========================
if menu == "👥 Clientes":
    st.header("Gestao de Clientes")

    tab_lista, tab_cad, tab_busca = st.tabs([
        "Meus Clientes", "Novo Cliente", "Pesquisar"
    ])

    with tab_cad:
        st.subheader("Cadastrar Novo Cliente")
        with st.container(border=True):
            n1, n2 = st.columns(2)
            with n1:
                nc_nome  = st.text_input("Nome completo *:", key="nc_nome")
                nc_cpf   = st.text_input("CPF *:", key="nc_cpf",
                                         placeholder="000.000.000-00")
                nc_rg    = st.text_input("RG:", key="nc_rg")
                nc_nasc  = st.text_input("Data de nascimento:",
                                         key="nc_nasc", placeholder="dd/mm/aaaa")
                nc_email = st.text_input("E-mail:", key="nc_email")
                nc_tel   = st.text_input("Telefone *:", key="nc_tel",
                                         placeholder="(21) 99999-9999")
                nc_tel2  = st.text_input("Telefone 2:", key="nc_tel2")
            with n2:
                nc_cep    = st.text_input("CEP:", key="nc_cep")
                nc_log    = st.text_input("Logradouro:", key="nc_log")
                nc_num    = st.text_input("Numero:", key="nc_num")
                nc_comp   = st.text_input("Complemento:", key="nc_comp")
                nc_bairro = st.text_input("Bairro:", key="nc_bairro")
                nc_cid    = st.text_input("Cidade:", key="nc_cid")
                nc_est    = st.selectbox("Estado (UF):", ESTADOS_BR, index=18, key="nc_est")
            nc_obs  = st.text_area("Observacoes:", key="nc_obs", height=80)
            nc_proc = st.text_input(
                "Processos ja existentes (separados por virgula):",
                key="nc_proc",
                placeholder="Ex: 0001234-12.2023.8.19.0001"
            )

            if st.button("Cadastrar Cliente", type="primary", key="btn_nc"):
                erros = []
                if not nc_nome.strip(): erros.append("Nome obrigatorio.")
                if not nc_cpf.strip():  erros.append("CPF obrigatorio.")
                if not nc_tel.strip():  erros.append("Telefone obrigatorio.")
                cpf_limpo = nc_cpf.strip().replace(".", "").replace("-", "")
                if any(
                    c.get("cpf", "").replace(".", "").replace("-", "") == cpf_limpo
                    for c in meus_clientes()
                ):
                    erros.append("CPF ja cadastrado.")

                if erros:
                    for e in erros: st.error(e)
                else:
                    procs_list = [
                        x.strip() for x in nc_proc.split(",") if x.strip()
                    ]
                    novo_cli = {
                        "id": (f"cli_{usr_atual}_"
                               f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"),
                        "nome":                nc_nome.strip(),
                        "cpf":                 nc_cpf.strip(),
                        "rg":                  nc_rg.strip(),
                        "data_nascimento":     nc_nasc.strip(),
                        "email":               nc_email.strip(),
                        "telefone":            nc_tel.strip(),
                        "telefone2":           nc_tel2.strip(),
                        "cep":                 nc_cep.strip(),
                        "logradouro":          nc_log.strip(),
                        "numero":              nc_num.strip(),
                        "complemento":         nc_comp.strip(),
                        "bairro":              nc_bairro.strip(),
                        "cidade":              nc_cid.strip(),
                        "estado":              nc_est.strip(),
                        "observacoes":         nc_obs.strip(),
                        "processos_vinculados": procs_list,
                        "usuario_dono":        usr_atual,
                    }
                    st.session_state.lista_clientes.append(novo_cli)
                    # vincula publicacoes existentes
                    for num_p in procs_list:
                        for pub in st.session_state.lista_publicacoes:
                            if (pub.get("processo") == num_p and
                                    not pub.get("cliente_id")):
                                pub["cliente_id"] = novo_cli["id"]
                    salvar_clientes()
                    salvar_publicacoes()
                    st.success(f"Cliente **{nc_nome}** cadastrado!")
                    st.rerun()

    with tab_lista:
        clientes_ord = sorted(meus_clientes(), key=lambda x: x.get("nome", ""))
        st.subheader(f"Clientes cadastrados ({len(clientes_ord)})")
        if not clientes_ord:
            st.info("Nenhum cliente cadastrado ainda.")
        else:
            for c in clientes_ord:
                procs_c = [
                    p for p in meus_processos()
                    if (p.get("cliente_id") == c["id"] or
                        p.get("processo") in c.get("processos_vinculados", []))
                ]
                with st.container(border=True):
                    cc1, cc2, cc3 = st.columns([3, 2, 1])
                    with cc1:
                        st.markdown(f"**{c['nome']}**")
                        st.caption(
                            f"CPF: {c.get('cpf', '')} | "
                            f"Tel: {c.get('telefone', '')}"
                        )
                        if c.get("email"):
                            st.caption(f"Email: {c['email']}")
                    with cc2:
                        st.metric("Processos", len(procs_c))
                        fin_c = [r for r in meu_financeiro()
                                 if r.get("cliente_id") == c["id"]]
                        rec   = sum(r.get("valor", 0) for r in fin_c
                                    if r.get("status") == "Recebido")
                        st.caption(f"Recebido: R$ {rec:,.2f}")
                    with cc3:
                        if st.button("Abrir",
                                     key=f"abrir_cli_{c['id']}",
                                     use_container_width=True):
                            st.session_state.pagina_cliente_aberto = c["id"]
                            st.rerun()

    with tab_busca:
        st.subheader("Pesquisar Cliente")
        termo_cli = st.text_input(
            "Pesquise por nome, CPF ou telefone:",
            placeholder="Ex: Rafael, 021.999 ou 99999-9999",
            key="busca_cli"
        )
        if termo_cli.strip():
            t       = termo_cli.lower()
            enc_cli = [
                c for c in meus_clientes()
                if (t in c.get("nome", "").lower() or
                    t in c.get("cpf", "").lower() or
                    t in c.get("telefone", "").lower() or
                    t in c.get("telefone2", "").lower() or
                    t in c.get("email", "").lower())
            ]
            if not enc_cli:
                st.warning(f"Nenhum cliente encontrado para: **{termo_cli}**")
            else:
                st.success(f"{len(enc_cli)} cliente(s) encontrado(s).")
                for c in enc_cli:
                    with st.container(border=True):
                        sc1, sc2, sc3 = st.columns([3, 2, 1])
                        with sc1:
                            st.markdown(f"**{c['nome']}**")
                            st.caption(
                                f"CPF: {c.get('cpf', '')} | "
                                f"Tel: {c.get('telefone', '')}"
                            )
                        with sc2:
                            procs_c = [p for p in meus_processos()
                                       if p.get("cliente_id") == c["id"]]
                            st.metric("Processos", len(procs_c))
                        with sc3:
                            if st.button("Abrir",
                                         key=f"srch_cli_{c['id']}",
                                         use_container_width=True):
                                st.session_state.pagina_cliente_aberto = c["id"]
                                st.rerun()

# =========================
# FINANCEIRO (MENU)
# =========================
elif menu == "💰 Financeiro":
    st.header("Painel Financeiro")
    for p in st.session_state.lista_publicacoes:
        p["data_fatal"] = _get_dt(p)

    fin_todos  = meu_financeiro()
    total_esp  = sum(r.get("valor", 0) for r in fin_todos)
    total_rec  = sum(r.get("valor", 0) for r in fin_todos
                     if r.get("status") == "Recebido")
    total_pen  = total_esp - total_rec

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total lancamentos", len(fin_todos))
    m2.metric("Total esperado",    f"R$ {total_esp:,.2f}")
    m3.metric("Total recebido",    f"R$ {total_rec:,.2f}")
    m4.metric("Total pendente",    f"R$ {total_pen:,.2f}")

    st.divider()

    tab_pen, tab_rec, tab_all = st.tabs([
        "Pendentes", "Recebidos", "Todos"
    ])

    for tab, filtro in [
        (tab_pen, "Pendente"),
        (tab_rec, "Recebido"),
        (tab_all, "Todos")
    ]:
        with tab:
            lista_f = (fin_todos if filtro == "Todos"
                       else [r for r in fin_todos if r.get("status") == filtro])
            if not lista_f:
                st.info("Nenhum lancamento.")
            else:
                df_f = pd.DataFrame([{
                    "Cliente": next(
                        (c["nome"] for c in meus_clientes()
                         if c["id"] == r.get("cliente_id", "")), "—"
                    ),
                    "Processo":  r.get("processo", ""),
                    "Tipo":      r.get("tipo", ""),
                    "Descricao": r.get("descricao", ""),
                    "Valor":     f"R$ {r.get('valor', 0):,.2f}",
                    "Vencimento":r.get("data_vencimento", ""),
                    "Status":    r.get("status", ""),
                    "Recorrente":"Sim" if r.get("recorrente") else "Nao",
                } for r in sorted(
                    lista_f,
                    key=lambda x: x.get("data_vencimento", "")
                )])
                st.dataframe(df_f, use_container_width=True, hide_index=True)

                if filtro == "Pendente":
                    st.divider()
                    for r in lista_f:
                        with st.container(border=True):
                            rc1, rc2, rc3 = st.columns([3, 2, 1])
                            cli_nome = next(
                                (c["nome"] for c in meus_clientes()
                                 if c["id"] == r.get("cliente_id", "")), "—"
                            )
                            with rc1:
                                st.markdown(
                                    f"**{cli_nome}** — {r.get('tipo', '')}"
                                )
                                st.caption(
                                    f"{r.get('descricao', '')} | "
                                    f"Proc: {r.get('processo', '')}"
                                )
                            with rc2:
                                st.metric("Valor",
                                          f"R$ {r.get('valor', 0):,.2f}")
                                st.caption(
                                    f"Venc: {r.get('data_vencimento', '')}"
                                )
                            with rc3:
                                if st.button("Receber",
                                             key=f"fin_rec_{r['id']}",
                                             use_container_width=True):
                                    r["status"]           = "Recebido"
                                    r["data_recebimento"] = date.today().isoformat()
                                    salvar_financeiro()
                                    st.rerun()

# =========================
# CALENDARIO
# =========================
elif menu == "🗓️ Calendario":
    st.header("Calendario de Prazos e Audiencias")
    for p in st.session_state.lista_publicacoes:
        p["data_fatal"] = _get_dt(p)

    hoje    = date.today()
    col_m, col_a, col_nav = st.columns([2, 2, 1])

    with col_m:
        mes_sel = st.selectbox(
            "Mes:", list(range(1, 13)),
            index=st.session_state.cal_mes - 1,
            format_func=lambda x: MESES_NOME[x - 1],
            key="cal_mes_sel"
        )
    with col_a:
        ano_sel = st.selectbox(
            "Ano:", list(range(hoje.year - 1, hoje.year + 3)),
            index=1, key="cal_ano_sel"
        )
    with col_nav:
        st.write("")
        if st.button("Anterior"):
            d = date(ano_sel, mes_sel, 1) - timedelta(days=1)
            st.session_state.cal_mes = d.month
            st.session_state.cal_ano = d.year
            st.rerun()
        if st.button("Proximo"):
            d = date(ano_sel, mes_sel, 28) + timedelta(days=4)
            st.session_state.cal_mes = d.month
            st.session_state.cal_ano = d.year
            st.rerun()

    st.markdown(f"### {MESES_NOME[mes_sel - 1]} / {ano_sel}")
    render_calendario(mes_sel, ano_sel)

    st.divider()
    st.subheader("Eventos do mes")
    tab_p, tab_a = st.tabs(["Prazos", "Audiencias"])

    with tab_p:
        prazos_m = sorted(
            [p for p in meus_processos()
             if _get_dt(p) and
             _get_dt(p).month == mes_sel and
             _get_dt(p).year  == ano_sel],
            key=lambda x: _get_dt(x)
        )
        if not prazos_m:
            st.info("Nenhum prazo neste mes.")
        else:
            for p in prazos_m:
                dt = _get_dt(p)
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.error(
                            f"**{dt.strftime('%d/%m/%Y')}** — {p['processo']}"
                        )
                        cli = _cliente_por_id(p.get("cliente_id", ""))
                        if cli: st.caption(f"Cliente: {cli['nome']}")
                        st.caption(
                            f"Tribunal: {p['tribunal']} | "
                            f"{p.get('dias_prazo', 0)} dias uteis"
                        )
                    with c2:
                        if st.button("Abrir",
                                     key=f"cal_p_{p['chave']}",
                                     use_container_width=True):
                            st.session_state.pagina_processo_aberto = p["chave"]
                            st.rerun()

    with tab_a:
        auds_m = sorted(
            [a for a in minhas_audiencias()
             if isinstance(a.get("data"), date) and
             a["data"].month == mes_sel and
             a["data"].year  == ano_sel],
            key=lambda x: x["data"]
        )
        if not auds_m:
            st.info("Nenhuma audiencia neste mes.")
        else:
            for a in auds_m:
                with st.container(border=True):
                    st.success(
                        f"**{a['data'].strftime('%d/%m/%Y')}** "
                        f"{'as '+a['hora'] if a.get('hora') else ''} — "
                        f"**{a.get('tipo', '')}**"
                    )
                    st.caption(
                        f"Processo: {a.get('processo', '')} | "
                        f"Local: {a.get('local', '')}"
                    )
                    if a.get("observacoes"):
                        st.info(a["observacoes"])

# =========================
# AUDIENCIAS
# =========================
elif menu == "⚖️ Audiencias":
    st.header("Cadastro de Audiencias")
    tab_cad, tab_lista = st.tabs(["Nova Audiencia", "Minhas Audiencias"])

    with tab_cad:
        st.subheader("Cadastrar Nova Audiencia")
        with st.container(border=True):
            ca1, ca2 = st.columns(2)
            with ca1:
                a_proc = st.text_input(
                    "Numero do processo:", key="a_proc",
                    placeholder="Ex: 0001234-12.2023"
                )
                a_tipo = st.selectbox(
                    "Tipo de audiencia:", TIPOS_AUDIENCIA, key="a_tipo"
                )
                a_data = st.date_input(
                    "Data:", key="a_data", value=date.today()
                )
            with ca2:
                a_hora  = st.text_input(
                    "Horario:", key="a_hora", placeholder="Ex: 14:00"
                )
                a_local = st.text_input(
                    "Local / Vara:", key="a_local",
                    placeholder="Ex: 3a Vara Civel - TJRJ"
                )
                a_trib  = st.selectbox(
                    "Tribunal:",
                    ["TJRJ", "Federal", "Trabalhista", "Outros"],
                    key="a_trib"
                )
            a_obs = st.text_area(
                "Observacoes:", height=100, key="a_obs",
                placeholder="Ex: Levar documentos, testemunhas..."
            )

            if st.button("Cadastrar Audiencia", type="primary",
                         key="btn_aud"):
                if not a_proc.strip():
                    st.error("Informe o numero do processo.")
                else:
                    nova = {
                        "id":          f"{a_proc}_{a_data.isoformat()}_{usr_atual}",
                        "processo":    a_proc.strip(),
                        "tipo":        a_tipo,
                        "data":        a_data,
                        "hora":        a_hora.strip(),
                        "local":       a_local.strip(),
                        "tribunal":    a_trib,
                        "observacoes": a_obs.strip(),
                        "usuario_dono":usr_atual,
                    }
                    if not any(a["id"] == nova["id"]
                               for a in st.session_state.lista_audiencias):
                        st.session_state.lista_audiencias.append(nova)
                        salvar_audiencias()
                        st.success(
                            f"Audiencia cadastrada para "
                            f"{a_data.strftime('%d/%m/%Y')}!"
                        )
                        st.rerun()
                    else:
                        st.warning(
                            "Audiencia ja cadastrada para este processo nesta data."
                        )

    with tab_lista:
        st.subheader("Audiencias Cadastradas")
        auds = sorted(
            minhas_audiencias(),
            key=lambda x: (x.get("data", date.min)
                           if isinstance(x.get("data"), date) else date.min)
        )
        if not auds:
            st.info("Nenhuma audiencia cadastrada.")
        else:
            f1, f2 = st.columns(2)
            ft = f1.selectbox(
                "Tribunal:",
                ["Todos", "TJRJ", "Federal", "Trabalhista", "Outros"],
                key="fa_t"
            )
            fp = f2.selectbox(
                "Periodo:", ["Todas", "Futuras", "Passadas"], key="fa_p"
            )
            lista_a = auds
            if ft != "Todos":
                lista_a = [a for a in lista_a if a.get("tribunal") == ft]
            if fp == "Futuras":
                lista_a = [a for a in lista_a
                           if isinstance(a.get("data"), date) and
                           a["data"] >= date.today()]
            if fp == "Passadas":
                lista_a = [a for a in lista_a
                           if isinstance(a.get("data"), date) and
                           a["data"] < date.today()]

            for a in lista_a:
                d_aud   = a.get("data")
                passada = isinstance(d_aud, date) and d_aud < date.today()
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    with c1:
                        icone    = "Realizada" if passada else "Agendada"
                        data_str = (d_aud.strftime("%d/%m/%Y")
                                    if isinstance(d_aud, date) else "—")
                        st.markdown(f"**{a.get('tipo', '')}** ({icone})")
                        st.caption(
                            f"Proc: {a.get('processo', '')} | "
                            f"{data_str} "
                            f"{'as '+a['hora'] if a.get('hora') else ''}"
                        )
                    with c2:
                        st.caption(f"Local: {a.get('local', '')}")
                        st.caption(f"Tribunal: {a.get('tribunal', '')}")
                    with c3:
                        if st.button("Excluir",
                                     key=f"del_aud_{a['id']}",
                                     use_container_width=True):
                            st.session_state.lista_audiencias = [
                                x for x in st.session_state.lista_audiencias
                                if x["id"] != a["id"]
                            ]
                            salvar_audiencias()
                            st.rerun()
                    if a.get("observacoes"):
                        st.info(f"Obs: {a['observacoes']}")

# =========================
# RELATORIOS
# =========================
elif menu == "📊 Relatórios":
    st.header("Relatórios de Prazos e Audiências")
    for p in st.session_state.lista_publicacoes:
        p["data_fatal"] = _get_dt(p)

    tab_sem, tab_mes, tab_ano, tab_exp, tab_wpp = st.tabs(["Por Semana", "Por Mês", "Por Ano", "Exportar", "📲 WhatsApp"])

    with tab_sem:
        st.subheader("Prazos da Semana")
        data_ref  = st.date_input(
            "Selecione qualquer dia da semana:",
            value=date.today(), key="rp_sem"
        )
        seg = data_ref - timedelta(days=data_ref.weekday())
        sex = seg + timedelta(days=4)
        st.caption(
            f"Semana: **{seg.strftime('%d/%m/%Y')}** a "
            f"**{sex.strftime('%d/%m/%Y')}**"
        )
        prazos_sem = sorted(
            [p for p in meus_processos()
             if _get_dt(p) and
             seg <= _get_dt(p).date() <= (seg + timedelta(days=6))],
            key=lambda x: _get_dt(x)
        )
        auds_sem = sorted(
            [a for a in minhas_audiencias()
             if isinstance(a.get("data"), date) and
             seg <= a["data"] <= (seg + timedelta(days=6))],
            key=lambda x: x["data"]
        )
        if not prazos_sem and not auds_sem:
            st.info("Nenhum evento nesta semana.")
        else:
            if prazos_sem:
                st.markdown("#### Prazos")
                st.dataframe(pd.DataFrame([{
                    "Data":       _get_dt(p).strftime("%d/%m/%Y"),
                    "Processo":   p["processo"],
                    "Tribunal":   p["tribunal"],
                    "Dias uteis": p.get("dias_prazo", 0),
                    "Analisado":  "Sim" if p.get("analisado") else "Nao",
                } for p in prazos_sem]),
                use_container_width=True, hide_index=True)

            if auds_sem:
                st.markdown("#### Audiencias")
                st.dataframe(pd.DataFrame([{
                    "Data":     (a["data"].strftime("%d/%m/%Y")
                                 if isinstance(a["data"], date) else "—"),
                    "Horario":  a.get("hora", ""),
                    "Tipo":     a.get("tipo", ""),
                    "Processo": a.get("processo", ""),
                    "Local":    a.get("local", ""),
                } for a in auds_sem]),
                use_container_width=True, hide_index=True)

    with tab_mes:
        st.subheader("Prazos do Mes")
        cm, ca = st.columns(2)
        mes_r = cm.selectbox(
            "Mes:", list(range(1, 13)),
            index=date.today().month - 1,
            format_func=lambda x: MESES_NOME[x - 1], key="rp_mes"
        )
        ano_r = ca.selectbox(
            "Ano:",
            list(range(date.today().year - 1, date.today().year + 3)),
            index=1, key="rp_ano"
        )
        prazos_m = sorted(
            [p for p in meus_processos()
             if _get_dt(p) and
             _get_dt(p).month == mes_r and
             _get_dt(p).year  == ano_r],
            key=lambda x: _get_dt(x)
        )
        auds_m = sorted(
            [a for a in minhas_audiencias()
             if isinstance(a.get("data"), date) and
             a["data"].month == mes_r and
             a["data"].year  == ano_r],
            key=lambda x: x["data"]
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Total prazos",     len(prazos_m))
        c2.metric("Total audiencias", len(auds_m))
        c3.metric("Total eventos",    len(prazos_m) + len(auds_m))

        if prazos_m:
            st.markdown("#### Prazos por semana")
            for sem_ini in [1, 8, 15, 22, 29]:
                sem_fim = sem_ini + 6
                sem_p   = [p for p in prazos_m
                           if sem_ini <= _get_dt(p).day <= sem_fim]
                if sem_p:
                    nd = cal_module.monthrange(ano_r, mes_r)[1]
                    with st.expander(
                        f"Semana {sem_ini}-{min(sem_fim, nd)} "
                        f"({len(sem_p)} prazo(s))",
                        expanded=True
                    ):
                        for p in sem_p:
                            with st.container(border=True):
                                cc1, cc2 = st.columns([4, 1])
                                with cc1:
                                    st.error(
                                        f"**{_get_dt(p).strftime('%d/%m/%Y')}**"
                                        f" — {p['processo']}"
                                    )
                                    if p.get("acao_necessaria"):
                                        st.warning(p["acao_necessaria"])
                                with cc2:
                                    if st.button(
                                        "Abrir",
                                        key=f"rel_m_{p['chave']}",
                                        use_container_width=True
                                    ):
                                        st.session_state.pagina_processo_aberto = p["chave"]
                                        st.rerun()

        if auds_m:
            st.markdown("#### Audiencias")
            st.dataframe(pd.DataFrame([{
                "Data":    (a["data"].strftime("%d/%m/%Y")
                            if isinstance(a["data"], date) else "—"),
                "Horario": a.get("hora", ""),
                "Tipo":    a.get("tipo", ""),
                "Processo":a.get("processo", ""),
                "Local":   a.get("local", ""),
            } for a in auds_m]),
            use_container_width=True, hide_index=True)

    with tab_ano:
        st.subheader("Visao Anual")
        ano_a = st.selectbox(
            "Ano:",
            list(range(date.today().year - 1, date.today().year + 3)),
            index=1, key="rp_ano2"
        )
        prazos_a = sorted(
            [p for p in meus_processos()
             if _get_dt(p) and _get_dt(p).year == ano_a],
            key=lambda x: _get_dt(x)
        )
        auds_a = sorted(
            [a for a in minhas_audiencias()
             if isinstance(a.get("data"), date) and a["data"].year == ano_a],
            key=lambda x: x["data"]
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total prazos",       len(prazos_a))
        c2.metric("Total audiencias",   len(auds_a))
        c3.metric("Processos unicos",
                  len(set(p["processo"] for p in prazos_a)))
        c4.metric("Meses com eventos",
                  len(set(_get_dt(p).month for p in prazos_a))
                  if prazos_a else 0)

        dados_mes = []
        for m_i in range(1, 13):
            pp = [p for p in prazos_a if _get_dt(p).month == m_i]
            aa = [a for a in auds_a
                  if isinstance(a.get("data"), date) and
                  a["data"].month == m_i]
            dados_mes.append({
                "Mes":        MESES_NOME[m_i - 1],
                "Prazos":     len(pp),
                "Audiencias": len(aa),
                "Total":      len(pp) + len(aa),
            })
        df_ano = pd.DataFrame(dados_mes)
        st.dataframe(df_ano, use_container_width=True, hide_index=True)
        st.bar_chart(df_ano.set_index("Mes")[["Prazos", "Audiencias"]])

    with tab_exp:
        st.subheader("Exportar Relatório")
        ex1, ex2 = st.columns(2)
        mes_e = ex1.selectbox(
            "Mês:", list(range(1, 13)),
            index=date.today().month - 1,
            format_func=lambda x: MESES_NOME[x - 1], key="exp_m"
        )
        ano_e = ex2.selectbox(
            "Ano:",
            list(range(date.today().year - 1, date.today().year + 3)),
            index=1, key="exp_a"
        )
        prazos_e = sorted(
            [p for p in meus_processos()
             if _get_dt(p) and
             _get_dt(p).month == mes_e and
             _get_dt(p).year  == ano_e],
            key=lambda x: _get_dt(x)
        )
        auds_e = sorted(
            [a for a in minhas_audiencias()
             if isinstance(a.get("data"), date) and
             a["data"].month == mes_e and
             a["data"].year  == ano_e],
            key=lambda x: x["data"]
        )
        linhas = [
            "RELATORIO DE PRAZOS E AUDIENCIAS",
            f"Advogado: {nom_atual} | OAB/{oab_uf_atual} {oab_atual}",
            f"Periodo: {MESES_NOME[mes_e-1]}/{ano_e}",
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "=" * 60, "",
            f"PRAZOS ({len(prazos_e)})", "-" * 40,
        ]
        for p in prazos_e:
            dt = _get_dt(p)
            linhas += [
                f"Data: {dt.strftime('%d/%m/%Y') if dt else '—'}",
                f"Processo: {p['processo']}",
                f"Tribunal: {p['tribunal']}",
                f"Acao: {p.get('acao_necessaria', '—')}",
                "",
            ]
        linhas += ["", f"AUDIENCIAS ({len(auds_e)})", "-" * 40]
        for a in auds_e:
            d = a.get("data")
            linhas += [
                f"Data: {d.strftime('%d/%m/%Y') if isinstance(d, date) else '—'}"
                f" {'as '+a['hora'] if a.get('hora') else ''}",
                f"Tipo: {a.get('tipo', '')}",
                f"Processo: {a.get('processo', '')}",
                f"Local: {a.get('local', '')}",
                f"Obs: {a.get('observacoes', '')}",
                "",
            ]
        st.download_button(
            "Baixar relatorio .txt",
            data="\n".join(linhas).encode("utf-8"),
            file_name=f"relatorio_{MESES_NOME[mes_e-1]}_{ano_e}.txt",
            mime="text/plain"
        )
# ── ABA WHATSAPP (RELATÓRIO CONTROLADOR + CLIENTE + AGENDA GOOGLE) ──
        with tab_wpp:
            st.subheader("📲 Gestão de Mensagens WhatsApp")
            m_aba1, m_aba2 = st.tabs(["📋 Relatório do Controlador", "👤 Comunicar Cliente"])

            # --- SUB-ABA 1: RELATÓRIO PARA O GRUPO DO ESCRITÓRIO ---
            with m_aba1:
                st.caption("Gere o resumo diário ou semanal para o grupo interno do escritório.")
                tipo_rel = st.radio("Período:", ["Resumo do Dia (Hoje)", "Próxima Semana"], horizontal=True, key="rad_wpp_int")
                
                dias_semana_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

                if st.button("Gerar Mensagem para o Grupo", type="primary", use_container_width=True):
                    hoje = date.today()
                    msg = ""
                    if tipo_rel == "Resumo do Dia (Hoje)":
                        data_ini = data_fim = hoje
                        msg = f"🚨 *AUDIÊNCIA E PRAZOS DO DIA {hoje.strftime('%d/%m/%Y')}*\n\n"
                    else:
                        data_ini = hoje + timedelta(days=(7 - hoje.weekday()))
                        data_fim = data_ini + timedelta(days=6)
                        msg = f"🗓️ *PRAZOS E AUDIÊNCIAS DA PRÓXIMA SEMANA ({data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')})*\n\n"

                    for a in sorted([x for x in minhas_audiencias() if data_ini <= x['data'] <= data_fim], key=lambda x: (x['data'], x['hora'])):
                        cli_obj = next((c for c in meus_clientes() if a['processo'] in c.get('processos_vinculados', [])), None)
                        msg += f"PROCESSO: {a['processo']} - {a['tipo'].upper()}\n"
                        msg += f"{dias_semana_pt[a['data'].weekday()]}, {a['data'].day} de {MESES_NOME[a['data'].month - 1].lower()} ⋅ {a['hora']}\n"
                        msg += f"PARTES: {cli_obj['nome'].upper() if cli_obj else 'Não informado'}\n\n"

                    for p in sorted([x for x in meus_processos() if x.get("data_fatal") and data_ini <= (x["data_fatal"].date() if isinstance(x["data_fatal"], datetime) else x["data_fatal"]) <= data_fim], key=lambda x: x['data_fatal']):
                        cli_obj = (_cliente_por_id(p.get("cliente_id", "")) or next((c for c in meus_clientes() if p['processo'] in c.get('processos_vinculados', [])), None))
                        msg += f"PROCESSO: {p['processo']}\nPARTES: {cli_obj['nome'].upper() if cli_obj else 'Não informado'}\n"
                        msg += f"DECISÃO: {p.get('resumo_processo') or p.get('conteudo', '')[:150]}...\n\n"
                    
                    st.text_area("Copie para o Grupo:", value=msg, height=300, key="txt_wpp_int")

            # --- SUB-ABA 2: COMUNICAR O CLIENTE (INDIVIDUAL) ---
            with m_aba2:
                st.caption("Gere uma mensagem personalizada para enviar diretamente ao cliente sobre uma atualização ou audiência.")
                
                opcoes_eventos = []
                mapa_eventos = {}
                
                for aud in sorted([x for x in minhas_audiencias() if x['data'] >= date.today()], key=lambda x: x['data']):
                    label = f"⚖️ AUDIÊNCIA: {aud['data'].strftime('%d/%m')} - Proc: {aud['processo']}"
                    opcoes_eventos.append(label)
                    mapa_eventos[label] = {"tipo": "audiencia", "dados": aud}
                
                for p in sorted(meus_processos(), key=lambda x: x['data_pub'], reverse=True)[:10]:
                    label = f"📄 DECISÃO: {p['data_pub']} - Proc: {p['processo']}"
                    opcoes_eventos.append(label)
                    mapa_eventos[label] = {"tipo": "decisao", "dados": p}

                evento_sel = st.selectbox("Selecione o evento para informar o cliente:", ["(Selecione um item)"] + opcoes_eventos)

                if evento_sel != "(Selecione um item)":
                    ev = mapa_eventos[evento_sel]
                    proc_id = ev['dados']['processo']
                    cli_obj = next((c for c in meus_clientes() if proc_id in c.get('processos_vinculados', [])), None)
                    nome_cliente = cli_obj['nome'].split()[0].title() if cli_obj else "Prezado(a) Cliente"

                    if ev['tipo'] == "audiencia":
                        dados_aud = ev['dados']
                        local = dados_aud.get('local', '').upper()
                        obs = dados_aud.get('observacoes', '')
                        links = re.findall(r'(https?://\S+)', obs + " " + local)
                        is_online = len(links) > 0 or "ONLINE" in local or "VIRTUAL" in local or "VIDEO" in local
                        
                        msg_cli = f"Olá, *{nome_cliente}*! Tudo bem?\n\n"
                        msg_cli += f"Gostaríamos de informar que foi agendada uma audiência para o seu processo: *{dados_aud['processo']}*.\n\n"
                        msg_cli += f"🗓️ *DATA:* {dados_aud['data'].strftime('%d/%m/%Y')}\n"
                        msg_cli += f"🕒 *HORÁRIO:* {dados_aud['hora']}\n"
                        
                        if is_online:
                            link_final = links[0] if links else "Será enviado em breve"
                            msg_cli += f"💻 *FORMATO:* Virtual (Online)\n"
                            msg_cli += f"🔗 *LINK DE ACESSO:* {link_final}\n\n"
                            msg_cli += "📝 *DICAS:* Procure um local silencioso, com boa internet e teste seu microfone com antecedência. Estaremos acompanhando você durante todo o ato."
                        else:
                            msg_cli += f"📍 *LOCAL:* {dados_aud.get('local', 'Verificar com o escritório')}\n\n"
                            msg_cli += "📝 *DICAS:* Favor chegar com 20 minutos de antecedência portando seu documento de identidade original com foto."
                    
                    else:
                        dados_dec = ev['dados']
                        resumo = dados_dec.get('resumo_processo') or "O juiz publicou um novo despacho/decisão em seu processo."
                        
                        msg_cli = f"Olá, *{nome_cliente}*! Esperamos que esteja bem.\n\n"
                        msg_cli += f"Passando para te dar uma atualização sobre o seu processo (*{dados_dec['processo']}*).\n\n"
                        msg_cli += f"📢 *NOVIDADE:* {resumo}\n\n"
                        msg_cli += "✅ *PRÓXIMOS PASSOS:* Nossa equipe jurídica já analisou esta publicação e estamos tomando todas as providências necessárias. Não há necessidade de qualquer ação de sua parte no momento. Qualquer dúvida, estamos à disposição!"

                    st.text_area("Mensagem Personalizada para o Cliente:", value=msg_cli, height=350, key="txt_cli_wpp")
                    st.info("💡 **Ação:** Copie o texto acima e cole na conversa privada do cliente.")

            # INTEGRAÇÃO GOOGLE CALENDAR
            st.markdown("---")
            st.subheader("📅 Sincronização de Agenda")
            if st.button("🔄 Enviar Prazos e Audiências para meu Celular (Google)", use_container_width=True):
                with st.spinner("Aguardando autorização no terminal..."):
                    try:
                        auds = minhas_audiencias()
                        prazos = [p for p in meus_processos() if p.get("data_fatal")]
                        sincronizar_com_google(auds, tipo="audiencia")
                        sincronizar_com_google(prazos, tipo="prazo")
                        st.success("✅ Sucesso! Verifique sua agenda do Google em instantes.")
                    except Exception as e:
                        st.error(f"Erro ao sincronizar: {e}")

# =========================
# SUSPENSÕES DE PRAZO (PDF)
# =========================
elif menu == "📄 Suspensoes de Prazo (PDF)" or menu == "📄 Suspensões de Prazo (PDF)":
    st.header("📄 Suspensões de Prazo — Leitura por IA")
    st.caption("Faça o upload da portaria. A IA extrairá os dados e você poderá revisá-los na tabela antes de salvar.")
    
    # --- FUNÇÕES LOCAIS DE SEGURANÇA (Garante que nunca dá NameError) ---
    import pdfplumber
    def _extrair_texto_seguro(uploaded_file) -> str:
        texto = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t: texto += t + "\n"
        return texto

    def _merge_seguro(lista):
        if not lista: return []
        from datetime import timedelta
        lista = sorted(lista, key=lambda x: x["inicio"])
        m = [lista[0].copy()]
        for it in lista[1:]:
            if it["inicio"] <= m[-1]["fim"] + timedelta(days=1): 
                m[-1]["fim"] = max(m[-1]["fim"], it["fim"])
            else: 
                m.append(it.copy())
        return m
    # ------------------------------------------------------------------

    trib_alvo = st.selectbox(
        "Em qual categoria este documento deve ser salvo?",
        ["Todos", "TJRJ", "Federal", "Trabalhista", "Outros"],
        key="susp_trib_alvo"
    )
    
    up = st.file_uploader("Selecione o PDF da Portaria/Aviso:", type=["pdf"], key="susp_pdf_up")
    
    if up:
        if st.button("🤖 Analisar PDF com IA", type="primary", use_container_width=True):
            with st.spinner("A IA está lendo o documento e extraindo as datas..."):
                try:
                    # Usa a função local garantida
                    txt = _extrair_texto_seguro(up)
                    # Chama a função inteligente da Groq (que já está no seu sistema)
                    regs = extrair_suspensoes_com_ia(txt)
                    st.session_state['rascunho_suspensoes'] = regs
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    # Exibe a tabela de rascunho se a IA já terminou
    if 'rascunho_suspensoes' in st.session_state and st.session_state['rascunho_suspensoes']:
        st.success("✅ Análise concluída! Revise as informações abaixo.")
        st.warning("DICA: Se a IA puxou alguma data errada, selecione a linha clicando no número à esquerda e aperte 'Delete' no seu teclado.")
        
        df_r = pd.DataFrame(st.session_state['rascunho_suspensoes'])
        
        # Garante que as colunas existam
        colunas_esperadas = ["inicio", "fim", "tribunal", "comarca", "abrangencia", "descricao"]
        for col in colunas_esperadas:
            if col not in df_r.columns:
                df_r[col] = ""
                
        # A planilha mágica editável do Streamlit
        df_editado = st.data_editor(
            df_r[colunas_esperadas],
            num_rows="dynamic",
            use_container_width=True,
            key="ed_susp"
        )
        
        if st.button("💾 Confirmar e Salvar Suspensões", type="primary"):
            def formatar_data(s):
                s = str(s).strip().replace(".", "/")
                try:    return datetime.strptime(s, "%d/%m/%Y").date()
                except: 
                    try: return datetime.strptime(s, "%Y-%m-%d").date()
                    except: return None

            novas_suspensoes = []
            for _, row in df_editado.iterrows():
                ini = formatar_data(row.get("inicio", ""))
                fim = formatar_data(row.get("fim", ""))
                
                if ini and fim:
                    if fim < ini: ini, fim = fim, ini
                    novas_suspensoes.append({
                        "inicio": ini,
                        "fim": fim,
                        "comarca": str(row.get("comarca", "Todas")),
                        "abrangencia": str(row.get("abrangencia", "Geral")),
                        "descricao": str(row.get("descricao", ""))
                    })

            # Agrupa as datas sobrepostas e salva no banco usando a função segura
            msc = _merge_seguro(novas_suspensoes)
            if trib_alvo not in st.session_state.suspensoes_por_tribunal:
                st.session_state.suspensoes_por_tribunal[trib_alvo] = []
                
            st.session_state.suspensoes_por_tribunal[trib_alvo].extend(msc)
            salvar_suspensoes()
            
            st.success(f"{len(msc)} período(s) salvo(s) com sucesso!")
            del st.session_state['rascunho_suspensoes'] # Limpa a tela
            time.sleep(1)
            st.rerun()

    st.divider()
    
    # Mostra as suspensões que já estão salvas no banco
    st.subheader("Suspensões Salvas no Banco de Dados")
    for t in ["Todos", "TJRJ", "Federal", "Trabalhista", "Outros"]:
        its = st.session_state.suspensoes_por_tribunal.get(t, [])
        if its:
            with st.expander(f"**{t}** — {len(its)} intervalo(s)", expanded=(t == "Todos")):
                df_s = pd.DataFrame([{
                    "Início": (i["inicio"].strftime("%d/%m/%Y") if isinstance(i["inicio"], date) else i["inicio"]),
                    "Fim":    (i["fim"].strftime("%d/%m/%Y") if isinstance(i["fim"], date) else i["fim"]),
                    "Comarca": i.get("comarca", "Todas"),
                    "Abrangência": i.get("abrangencia", "Geral"),
                    "Descrição": i.get("descricao", "")
                } for i in its])
                
                st.dataframe(df_s, use_container_width=True, hide_index=True)
                
                if st.button(f"🗑️ Limpar todas do {t}", key=f"lmp_{t}"):
                    st.session_state.suspensoes_por_tribunal[t] = []
                    salvar_suspensoes()
                    st.rerun()
        else:
            st.write(f"**{t}**: Nenhuma suspensão cadastrada.")

# =========================
# ENTRADA DE DADOS / PÁGINA INICIAL
# =========================
elif menu == "📥 Entrada de Dados":
    # ── Inicialização do Controle de Páginas (Paginação) ──
    if 'pag_pendentes' not in st.session_state: st.session_state.pag_pendentes = 0
    if 'pag_prazos' not in st.session_state: st.session_state.pag_prazos = 0

    st.header("🏠 Visão Geral e Importação")
    meus = meus_processos()

    # ── 1. RESUMO EXECUTIVO (DASHBOARD PREMIUM) ──────────────────
    qtd_meus = len(meus)
    qtd_cli = len(meus_clientes())
    qtd_prazo = len([p for p in meus if p.get("data_fatal") and not p.get("cumprido")])
    qtd_aud = len(minhas_audiencias())

    st.markdown("### 📊 Resumo Executivo")
    st.write("") 

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        card_indicador("Processos Ativos", qtd_meus, "📂", "#2563eb")
    with col2:
        card_indicador("Clientes na Base", qtd_cli, "👥", "#10b981")
    with col3:
        card_indicador("Prazos Pendentes", qtd_prazo, "🚨", "#ef4444")
    with col4:
        card_indicador("Próximas Audiências", qtd_aud, "⚖️", "#f59e0b")

    st.write("")
    st.divider()

    # ── 2. PESQUISA GLOBAL ───────────────────────────────────────
    st.subheader("🔍 Pesquisa Global")
    st.caption("Busque por número do processo, CPF do cliente, nome, OAB ou termos da publicação.")
    
    cb, cf = st.columns([3, 1])
    with cb:
        busca = st.text_input("Digite o termo de busca:", placeholder="Ex: 0001234-12.2023, João Silva...", key="busca")
    with cf:
        ftrib = st.selectbox("Tribunal:", ["Todos", "TJRJ", "Federal", "Trabalhista", "Outros"], key="ftrib")

    if busca.strip():
        termo = busca.lower()
        enc = []
        for p in meus:
            cli = _cliente_por_id(p.get("cliente_id", ""))
            cli_str = f"{cli.get('nome','')} {cli.get('cpf','')} {cli.get('rg','')}" if cli else ""
            
            if (termo in p.get("processo", "").lower() or
                termo in p.get("conteudo", "").lower() or
                termo in p.get("resumo_manual", "").lower() or
                termo in p.get("resumo_processo", "").lower() or
                termo in cli_str.lower()):
                
                if ftrib == "Todos" or p.get("tribunal") == ftrib:
                    enc.append(p)
                    
        if not enc:
            st.warning(f"Nenhum processo encontrado para: **{busca}**")
        else:
            st.success(f"{len(enc)} processo(s) encontrado(s).")
            for r in enc[:10]: # Mostra no máximo 10 na pesquisa para não poluir
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    cli = _cliente_por_id(r.get("cliente_id", ""))
                    with c1:
                        st.markdown(f"**{r['processo']}**")
                        if cli:
                            st.caption(f"Cliente: {cli['nome']} | {r['tribunal']}")
                        else:
                            st.caption(f"Tribunal: {r['tribunal']} | Pub: {r['data_pub']}")
                    with c2:
                        dt = _get_dt(r)
                        st.markdown(f"**Prazo:** {dt.strftime('%d/%m/%Y')}" if dt else "**Prazo:** não agendado")
                    with c3:
                        if st.button("Abrir Processo", key=f"bs_{r['chave']}", use_container_width=True):
                            st.session_state.pagina_processo_aberto = r["chave"]
                            st.rerun()
        st.divider()

    # ── 3. IMPORTAÇÃO (ABAIXO DA PESQUISA) ────────────────────
    st.subheader("⬇️ Importar Novas Publicações")
    tab_api, tab_txt = st.tabs(["🌐 API DJEN", "📋 Colar Texto"])
    
    with tab_api:
        st.caption("Puxe as publicações diretamente da base de dados do judiciário.")
        
        c_oab_num, c_oab_uf = st.columns([3, 1])
        api_oab = c_oab_num.text_input("Sua OAB (somente números):", value=re.sub(r'\D', '', oab_atual) if oab_atual else "", key="api_oab")
        api_oab_uf = c_oab_uf.selectbox("UF:", ESTADOS_BR, index=ESTADOS_BR.index(oab_uf_atual) if oab_uf_atual in ESTADOS_BR else 18, key="api_oab_uf")
        
        # Calendário duplo com limite de período
        c_dt1, c_dt2 = st.columns(2)
        api_dt_ini = c_dt1.date_input("Data Inicial:", value=date.today() - timedelta(days=7), key="api_dt_ini")
        api_dt_fim = c_dt2.date_input("Data Final:", value=date.today(), key="api_dt_fim")
        
        if st.button("🔄 Buscar no DJEN", type="primary", use_container_width=True):
            if not api_oab:
                st.error("Por favor, preencha o número da OAB.")
            elif api_dt_ini > api_dt_fim:
                st.error("❌ A Data Inicial não pode ser posterior à Data Final.")
            elif (api_dt_fim - api_dt_ini).days > 31:
                st.error("⚠️ Limite excedido! Para preservar a estabilidade do servidor, o período máximo de busca é de 31 dias.")
            else:
                with st.spinner(f"Buscando publicações entre {api_dt_ini.strftime('%d/%m/%Y')} e {api_dt_fim.strftime('%d/%m/%Y')}..."):
                    itens = consultar_api_djen(oab=f"{api_oab_uf}{api_oab}", data_ini=api_dt_ini, data_fim=api_dt_fim)
                    if itens:
                        integrar_resultados_djen(itens, usr_atual)
                        st.success("✅ Busca finalizada com sucesso! Novos registros foram processados.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning("Nenhuma publicação encontrada para esta OAB neste período.")

    with tab_txt:
        st.caption("Cole o conteúdo do e-mail do Recorte Digital ou qualquer texto com publicações.")
        txt_in = st.text_area("Cole o conteúdo:", height=150, key="txt_in_imp")
        if st.button("Processar e Filtrar", type="primary", key="btn_txt_imp"):
            if txt_in.strip():
                with st.spinner("Processando..."):
                    novos = processar_texto_oab(txt_in)
                    st.session_state.lista_publicacoes.extend(novos)
                    salvar_publicacoes()
                    st.success(f"{len(novos)} publicações importadas com sucesso!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Cole algum texto antes de processar.")

    st.divider()

    # ── 4. PROCESSOS PENDENTES DE TRATAMENTO (PAGINADO) ──────────
    st.subheader("📥 Processos Pendentes de Tratamento")
    st.caption("Publicações que ainda não possuem um prazo fatal agendado.")
    
    pendentes = [p for p in meus if not p.get("data_fatal")]
    
    if not pendentes:
        st.info("Tudo limpo! Nenhum processo pendente de análise. 🎉")
    else:
        itens_por_pagina = 15
        total_pag_pend = max(1, (len(pendentes) - 1) // itens_por_pagina + 1)
        
        if st.session_state.pag_pendentes >= total_pag_pend:
            st.session_state.pag_pendentes = max(0, total_pag_pend - 1)
            
        idx_ini_pend = st.session_state.pag_pendentes * itens_por_pagina
        idx_fim_pend = idx_ini_pend + itens_por_pagina
        pendentes_pagina = pendentes[idx_ini_pend:idx_fim_pend]
        
        for p in pendentes_pagina:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                icone = "Analisado" if p.get("analisado") else "Pendente"
                cli = _cliente_por_id(p.get("cliente_id", ""))
                
                with c1:
                    st.markdown(f"**{p['processo']}** ({icone})")
                    if cli:
                        st.caption(f"Cliente: {cli['nome']} | {p['tribunal']}")
                    else:
                        st.caption(f"Tribunal: {p['tribunal']} | Pub: {p['data_pub']}")
                with c2:
                    st.markdown("**Prazo:** não agendado")
                with c3:
                    if st.button("Tratar", key=f"pn_pend_{p['chave']}", use_container_width=True):
                        st.session_state.pagina_processo_aberto = p["chave"]
                        st.rerun()
        
        # Paginação
        if total_pag_pend > 1:
            st.write("")
            cp1, cp2, cp3 = st.columns([1, 2, 1])
            if cp1.button("⬅️ Anterior", key="prev_pend", use_container_width=True, disabled=(st.session_state.pag_pendentes == 0)):
                st.session_state.pag_pendentes -= 1
                st.rerun()
            cp2.markdown(f"<div style='text-align:center; padding-top: 5px; color:#64748b;'>Página <b>{st.session_state.pag_pendentes + 1}</b> de {total_pag_pend} <br><small>Total: {len(pendentes)} processos</small></div>", unsafe_allow_html=True)
            if cp3.button("Próxima ➡️", key="next_pend", use_container_width=True, disabled=(st.session_state.pag_pendentes == total_pag_pend - 1)):
                st.session_state.pag_pendentes += 1
                st.rerun()

    st.divider()

    # ── 5. PRAZOS EM ABERTO (PAGINADO) ─────────────
    st.subheader("🚨 Próximos Prazos em Aberto")
    prazos_abertos = [p for p in meus if p.get("data_fatal") and not p.get("cumprido", False)]
    prazos_abertos.sort(key=lambda x: _get_dt(x))
    
    if not prazos_abertos:
        st.info("Nenhum prazo em aberto no momento! 🎉")
    else:
        itens_por_pagina = 15
        total_pag_prazos = max(1, (len(prazos_abertos) - 1) // itens_por_pagina + 1)
        
        if st.session_state.pag_prazos >= total_pag_prazos:
            st.session_state.pag_prazos = max(0, total_pag_prazos - 1)
            
        idx_ini_prazos = st.session_state.pag_prazos * itens_por_pagina
        idx_fim_prazos = idx_ini_prazos + itens_por_pagina
        prazos_pagina = prazos_abertos[idx_ini_prazos:idx_fim_prazos]
        
        for p in prazos_pagina:
            dt = _get_dt(p)
            hoje = date.today()
            dt_date = dt.date() if isinstance(dt, datetime) else dt
            dias_restantes = (dt_date - hoje).days
            
            cor_data = "#dc3545" if dias_restantes < 0 else ("#fd7e14" if dias_restantes <= 3 else "#198754")
            status_txt = f"Atrasado {abs(dias_restantes)} dias" if dias_restantes < 0 else ("Vence HOJE" if dias_restantes == 0 else f"Em {dias_restantes} dias")

            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 2, 1])
                cli = _cliente_por_id(p.get("cliente_id", ""))
                with c1:
                    st.markdown(f"**{p['processo']}** ({p['tribunal']})")
                    if cli:
                        st.caption(f"👤 Cliente: {cli['nome']}")
                    resumo_exib = p.get("resumo_processo") or p.get("conteudo", "")[:100] + "..."
                    st.caption(f"_{resumo_exib}_")
                with c2:
                    st.markdown(f"**Vence em:** <span style='color:{cor_data}'>{dt.strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
                    st.caption(status_txt)
                with c3:
                    if st.button("Abrir", key=f"abrir_prz_ini_{p['chave']}", use_container_width=True):
                        st.session_state.pagina_processo_aberto = p["chave"]
                        st.rerun()
                        
        # Paginação
        if total_pag_prazos > 1:
            st.write("")
            cp1, cp2, cp3 = st.columns([1, 2, 1])
            if cp1.button("⬅️ Anterior", key="prev_prazos", use_container_width=True, disabled=(st.session_state.pag_prazos == 0)):
                st.session_state.pag_prazos -= 1
                st.rerun()
            cp2.markdown(f"<div style='text-align:center; padding-top: 5px; color:#64748b;'>Página <b>{st.session_state.pag_prazos + 1}</b> de {total_pag_prazos} <br><small>Total: {len(prazos_abertos)} prazos</small></div>", unsafe_allow_html=True)
            if cp3.button("Próxima ➡️", key="next_prazos", use_container_width=True, disabled=(st.session_state.pag_prazos == total_pag_prazos - 1)):
                st.session_state.pag_prazos += 1
                st.rerun()
        
# =========================
# CALCULADORA DE PRAZOS (PAGINA)
# =========================

elif menu == "🧮 Calculadora de Prazos":
    st.header("🧮 Calculadora de Prazos Processuais")
    st.caption(
        "Calcula prazos conforme as regras do DJEN/CPC: "
        "publicação = 1º dia útil após disponibilização; "
        "contagem inicia no 1º dia útil após a publicação."
    )

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            calc_data_disp = st.date_input("Data de disponibilização:", value=date.today(), key="calc_data_pag")
            calc_dias_pag = st.number_input("Quantidade de dias:", min_value=1, max_value=90, value=15, key="calc_dias_pag")
        
        with col2:
            calc_modo_pag = st.selectbox("Modo de Contagem:", ["Dias Úteis", "Dias Corridos"], key="calc_modo_pag")
            # Agora usa a nossa lista completa de tribunais!
            calc_trib_pag = st.selectbox("Tribunal (para suspensões):", LISTA_TRIBUNAIS, key="calc_trib_pag")
            
            # Divide a comarca em UF e Cidade
            c_uf, c_cid = st.columns([1, 3]) # UF fica pequenininho, Cidade fica grande
            with c_uf:
                calc_uf_pag = st.selectbox("UF:", ["Todas"] + UFS_BRASIL, key="calc_uf_pag")
            with c_cid:
                # O IBGE devolve as cidades do estado que o usuário escolheu ao lado
                lista_cidades_pag = buscar_cidades_por_uf(calc_uf_pag)
                calc_comarca_pag = st.selectbox("Comarca:", lista_cidades_pag, key="calc_comarca_pag")

        # Botão de cálculo atualizado
        if st.button("Calcular Prazo Agora", type="primary", key="calc_btn_pag", use_container_width=True):
            susp_esp_pag = st.session_state.suspensoes_por_tribunal.get(calc_trib_pag, [])
            susp_tod_pag = st.session_state.suspensoes_por_tribunal.get("Todos", [])
            susp_pag     = susp_esp_pag + susp_tod_pag

            # Chamada da função com os novos parâmetros: Comarca e Modo de Contagem
            resultado_pag = calcular_prazo_completo(
                calc_data_disp.strftime("%d/%m/%Y"), 
                calc_dias_pag, 
                susp_pag, 
                calc_comarca_pag, 
                calc_modo_pag
            )
            st.session_state["calc_resultado_pag"] = resultado_pag

    if st.session_state.get("calc_resultado_pag"):
        r = st.session_state["calc_resultado_pag"]
        st.divider()
        st.subheader("Resultado do Calculo")

        c1, c2, c3, c4 = st.columns(4)
        c1.info(
            f"**Disponibilizacao**\n\n"
            f"{r['data_disponibilizacao'].strftime('%d/%m/%Y')}"
        )
        c2.info(
            f"**Publicacao oficial**\n\n"
            f"{r['data_publicacao'].strftime('%d/%m/%Y')}"
        )
        c3.info(
            f"**Inicio da contagem**\n\n"
            f"{r['inicio_contagem'].strftime('%d/%m/%Y')}"
        )
        c4.success(
            f"**PRAZO FATAL**\n\n"
            f"{r['data_fatal'].strftime('%d/%m/%Y')}"
        )

        st.divider()

        # linha do tempo visual
        st.subheader("Linha do Tempo")
        eventos = [
            ("Disponibilizacao",  r["data_disponibilizacao"], "#6c757d"),
            ("Publicacao oficial",r["data_publicacao"],       "#0d6efd"),
            ("Inicio contagem",   r["inicio_contagem"],       "#fd7e14"),
            ("PRAZO FATAL",       r["data_fatal"],            "#dc3545"),
        ]
        html_timeline = '<div style="display:flex;gap:0;align-items:flex-start;margin:20px 0;">'
        for i, (nome, dt, cor) in enumerate(eventos):
            html_timeline += f"""
            <div style="flex:1;text-align:center;position:relative;">
                <div style="width:40px;height:40px;border-radius:50%;
                            background:{cor};color:white;font-weight:bold;
                            display:flex;align-items:center;justify-content:center;
                            margin:0 auto;font-size:14px;">{i+1}</div>
                <div style="font-size:11px;margin-top:6px;font-weight:bold;
                            color:{cor};">{nome}</div>
                <div style="font-size:12px;color:#333;">
                    {dt.strftime('%d/%m/%Y')}
                </div>
                <div style="font-size:11px;color:#888;">
                    {dt.strftime('%A').capitalize()}
                </div>
            </div>
            """
            if i < len(eventos) - 1:
                html_timeline += (
                    '<div style="flex:0.3;display:flex;'
                    'align-items:center;justify-content:center;'
                    'color:#ccc;font-size:20px;margin-top:10px;">→</div>'
                )
        html_timeline += '</div>'
        st.markdown(html_timeline, unsafe_allow_html=True)

        if r["suspensoes_aplicadas"] > 0:
            st.warning(
                f"{r['suspensoes_aplicadas']} periodo(s) de suspensao "
                f"foram considerados no calculo."
            )
        else:
            st.info(
                "Nenhuma suspensao aplicada. "
                "Importe o calendario em Suspensoes de Prazo (PDF) "
                "para calculos mais precisos."
            )

        # exportar resultado
        txt_resultado = (
            f"CALCULO DE PRAZO PROCESSUAL\n"
            f"{'='*40}\n"
            f"Data disponibilizacao: "
            f"{r['data_disponibilizacao'].strftime('%d/%m/%Y')}\n"
            f"Data publicacao:       "
            f"{r['data_publicacao'].strftime('%d/%m/%Y')}\n"
            f"Inicio da contagem:    "
            f"{r['inicio_contagem'].strftime('%d/%m/%Y')}\n"
            f"Dias uteis:            {r['dias_uteis']}\n"
            f"Suspensoes aplicadas:  {r['suspensoes_aplicadas']}\n"
            f"PRAZO FATAL:           "
            f"{r['data_fatal'].strftime('%d/%m/%Y')}\n"
            f"{'='*40}\n"
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        )
        st.download_button(
            "Baixar resultado .txt",
            data=txt_resultado.encode("utf-8"),
            file_name=(
                f"prazo_{r['data_fatal'].strftime('%d%m%Y')}.txt"
            ),
            mime="text/plain"
        )

    # historico de calculos recentes (nao salvos)
    st.divider()
    st.subheader("Calculos Rapidos em Lote")
    st.caption(
        "Calcule varios prazos de uma vez. "
        "Informe a data e os dias para cada processo."
    )

    if "lote_calculos" not in st.session_state:
        st.session_state.lote_calculos = []

    with st.container(border=True):
        lc1, lc2, lc3, lc4 = st.columns([2, 2, 1, 1])
        with lc1:
            lote_num  = st.text_input("Processo:", key="lote_num",
                                       placeholder="Numero opcional")
        with lc2:
            lote_data = st.date_input("Disponibilizacao:", key="lote_data",
                                       value=date.today())
        with lc3:
            lote_dias = st.number_input("Dias:", min_value=1, max_value=90,
                                         value=15, key="lote_dias")
        with lc4:
            st.write("")
            if st.button("+ Adicionar", key="lote_add",
                         use_container_width=True):
                susp_lote = (
                    st.session_state.suspensoes_por_tribunal.get("Todos", [])
                )
                r_lote = calcular_prazo_completo(
                    lote_data.strftime("%d/%m/%Y"),
                    lote_dias, susp_lote
                )
                st.session_state.lote_calculos.append({
                    "processo":   lote_num or "—",
                    "disp":       r_lote["data_disponibilizacao"].strftime("%d/%m/%Y"),
                    "publicacao": r_lote["data_publicacao"].strftime("%d/%m/%Y"),
                    "inicio":     r_lote["inicio_contagem"].strftime("%d/%m/%Y"),
                    "fatal":      r_lote["data_fatal"].strftime("%d/%m/%Y"),
                    "dias":       lote_dias,
                })
                st.rerun()

    if st.session_state.lote_calculos:
        df_lote = pd.DataFrame(st.session_state.lote_calculos)
        df_lote.columns = [
            "Processo", "Disponibilizacao", "Publicacao",
            "Inicio Contagem", "PRAZO FATAL", "Dias"
        ]
        st.dataframe(df_lote, use_container_width=True, hide_index=True)

        col_exp, col_lmp = st.columns(2)
        with col_exp:
            st.download_button(
                "Exportar lote .txt",
                data=df_lote.to_string(index=False).encode("utf-8"),
                file_name="prazos_lote.txt",
                mime="text/plain"
            )
        with col_lmp:
            if st.button("Limpar lote", key="lote_limpar"):
                st.session_state.lote_calculos = []
                st.rerun()

# =========================
# GESTÃO DE TAREFAS E PRAZOS
# =========================
elif menu in ["⏳ Tarefas em Aberto", "✅ Tarefas Concluídas"]:
    is_concluida = (menu == "✅ Tarefas Concluídas")
    st.header(menu)

    # Formulário de nova tarefa avulsa (só aparece na tela de Em Aberto)
    if not is_concluida:
        with st.expander("➕ Cadastrar Tarefa (Não Processual)", expanded=False):
            with st.form("form_nova_tarefa"):
                t_tit = st.text_input("Título da Tarefa *", placeholder="Ex: Ligar para cliente, Buscar documento...")
                t_desc = st.text_area("Descrição (opcional)")
                c1, c2 = st.columns(2)
                t_venc = c1.date_input("Vencimento", value=date.today())
                t_proc = c2.text_input("Vincular a Processo (opcional)")
                
                if st.form_submit_button("Salvar Tarefa", type="primary"):
                    if t_tit.strip():
                        nova_t = {
                            "id": f"tar_{int(time.time())}",
                            "titulo": t_tit.strip(),
                            "descricao": t_desc.strip(),
                            "vencimento": t_venc.isoformat(),
                            "processo": t_proc.strip(),
                            "cumprido": False,
                            "usuario_dono": usr_atual
                        }
                        st.session_state.lista_tarefas.append(nova_t)
                        salvar_tarefas()
                        st.success("Tarefa salva com sucesso!")
                        st.rerun()
                    else:
                        st.error("O título da tarefa é obrigatório.")

    st.divider()

    # Compilar prazos e tarefas
    itens_exibicao = []
    
    # 1. Prazos processuais (Inclui agendados e dispensados)
    # 1. Prazos processuais (Inclui agendados e dispensados)
    for p in meus_processos():
        dt = _get_dt(p)
        status_dispensa = (p.get("data_fatal") == "DISPENSADO")
        
        # Filtra por Aberto ou Concluído. Dispensados são sempre considerados Concluídos.
        if (dt or status_dispensa) and bool(p.get("cumprido", False)) == is_concluida:
            resumo_texto = p.get("resumo_processo") or p.get("conteudo", "")[:120] + "..."
            
            if status_dispensa:
                titulo_card = f"⏭️ DISPENSADO: {p['processo']}"
                data_exibicao = "Sem prazo"
            else:
                titulo_card = f"⚖️ Prazo: {p['processo']} ({p['tribunal']})"
                data_exibicao = dt.date() if isinstance(dt, datetime) else dt

            itens_exibicao.append({
                "tipo": "prazo",
                "data": data_exibicao,
                "id": p["chave"],
                "titulo": titulo_card,
                "desc": resumo_texto,
                "obj": p
            })
            
    # 2. Tarefas manuais
    for t in st.session_state.lista_tarefas:
        if t.get("usuario_dono") == usr_atual and bool(t.get("cumprido", False)) == is_concluida:
            dt = date.fromisoformat(t["vencimento"]) if t.get("vencimento") else date.max
            itens_exibicao.append({
                "tipo": "tarefa",
                "data": dt,
                "id": t["id"],
                "titulo": f"📌 Tarefa: {t['titulo']}",
                "desc": t.get("descricao", ""),
                "obj": t
            })
            
    # Ordenar tudo cronologicamente
    itens_exibicao.sort(key=lambda x: x["data"] if isinstance(x["data"], date) else date.max)
    
    if not itens_exibicao:
        st.info("Nenhuma atividade nesta categoria.")
    else:
        for item in itens_exibicao:
            with st.container(border=True):
                col_info, col_data, col_acao = st.columns([5, 2, 2])
                
                with col_info:
                    st.markdown(f"**{item['titulo']}**")
                    st.caption(f"_{item['desc']}_")
                    
                with col_data:
                    dt_str = item["data"].strftime("%d/%m/%Y") if isinstance(item["data"], date) else "Sem data"
                    cor_data = "#198754" if is_concluida else ("#dc3545" if item["data"] < date.today() else "#0d6efd")
                    st.markdown(f"<span style='color:{cor_data}; font-weight:bold; font-size: 16px;'>{dt_str}</span>", unsafe_allow_html=True)
                    if not is_concluida and item["data"] < date.today():
                        st.caption("⚠️ Atrasado")
                        
                with col_acao:
                    if item["tipo"] == "prazo":
                        if st.button("Abrir", key=f"abrir_t_{item['id']}", use_container_width=True):
                            st.session_state.pagina_processo_aberto = item["id"]
                            st.rerun()
                    
                    btn_label = "Desmarcar" if is_concluida else "✔ Concluir"
                    tipo_btn = "secondary" if is_concluida else "primary"
                    
                    if st.button(btn_label, type=tipo_btn, key=f"btn_cump_{item['tipo']}_{item['id']}", use_container_width=True):
                        # Alterna o status
                        item["obj"]["cumprido"] = not is_concluida
                        if item["tipo"] == "prazo":
                            salvar_publicacoes()
                        else:
                            salvar_tarefas()
                        st.rerun()
                        
                    # NOVO BOTÃO DE EXCLUIR TAREFA/PRAZO
                    if st.button("🗑️ Excluir", type="secondary", key=f"del_item_{item['tipo']}_{item['id']}", use_container_width=True):
                        if item["tipo"] == "tarefa":
                            # Apaga a tarefa manual do banco de dados
                            st.session_state.lista_tarefas = [t for t in st.session_state.lista_tarefas if t["id"] != item["id"]]
                            salvar_tarefas()
                        elif item["tipo"] == "prazo":
                            # Remove apenas o agendamento para preservar a publicação no histórico do processo
                            item["obj"]["data_fatal"] = None
                            item["obj"]["dias_prazo"] = 0
                            salvar_publicacoes()
                        st.rerun()


# =========================
# TRIBUNAIS
# =========================
elif menu in ["🏛️ TJRJ", "🏛️ Federal", "🏛️ Trabalhista", "🏛️ Outros"]:
    trib_alvo = menu.replace("🏛️ ", "")
    st.header(f"Publicacoes: {trib_alvo}")
    itens = [p for p in meus_processos() if p["tribunal"] == trib_alvo]
    if not itens:
        st.info("Nenhuma publicacao para este tribunal.")
    else:
        itens.sort(key=lambda x: x.get("data_pub", ""), reverse=True)
        for p in itens:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                icone = ("Minuta" if p.get("minuta_gerada") else
                         "Analisado" if p.get("analisado") else "Pendente")
                dt  = _get_dt(p)
                cli = _cliente_por_id(p.get("cliente_id", ""))
                with c1:
                    st.markdown(f"**{p['processo']}** ({icone})")
                    if cli:
                        if st.button(
                            f"Cliente: {cli['nome']}",
                            key=f"cli_btn_{p['chave']}"
                        ):
                            st.session_state.pagina_cliente_aberto = cli["id"]
                            st.rerun()
                    st.caption(f"Pub: {p['data_pub']}")
                with c2:
                    st.markdown(
                        f"**Prazo:** {dt.strftime('%d/%m/%Y')}"
                        if dt else "**Prazo:** nao agendado"
                    )
                with c3:
                    if st.button("Abrir",
                                 key=f"tr_{p['chave']}",
                                 use_container_width=True):
                        st.session_state.pagina_processo_aberto = p["chave"]
                        st.rerun()
                if p.get("resumo_manual"):
                    st.info(p["resumo_manual"][:120])
                elif p.get("resumo_processo"):
                    st.info(p["resumo_processo"][:120])

# =======================================================
# MÓDULOS DE ADMINISTRAÇÃO (MASTER E SÓCIO)
# =======================================================

# 1. PAINEL GLOBAL (MÓDULO MASTER) - Visível apenas para o Master
elif menu == "👑 Painel Master" and papel_atual == "Master":
    st.header("👑 Painel Master - Gestão de Escritórios")
    usuarios = carregar_usuarios()
    
    # Agrupa nomes de escritórios existentes para o seletor
    esc_existentes = sorted(list(set([u.get("escritorio_id") for u in usuarios if u.get("escritorio_id") != "master"])))
    
    tab_cad, tab_gestao = st.tabs(["➕ Novo Cadastro", "⚙️ Gerenciar Escritórios"])
    
    with tab_cad:
        tipo_vinculo = st.radio("Destino do Usuário:", ["Novo Escritório", "Escritório Existente"], horizontal=True)
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                if tipo_vinculo == "Novo Escritório":
                    n_esc = st.text_input("ID do NOVO Escritório (Ex: matriz, filial_buzios):", key="m_nesc")
                    # Se está criando um escritório novo, o primeiro usuário tem que ser o Sócio-Dono
                    papel_padrao = "Sócio"
                    st.info("O primeiro usuário será cadastrado automaticamente como Sócio.")
                else:
                    n_esc = st.selectbox("Selecione o Escritório:", esc_existentes)
                    # Se já existe, o Master escolhe qual a função do novo membro
                    papel_padrao = st.selectbox("Função do Usuário:", ["Associado", "Controlador", "Sócio"], key="m_npapel")
                
                n_usr = st.text_input("Login (usuário):", key="m_nusr")
                n_nom = st.text_input("Nome Completo:", key="m_nnom")
            
            with c2:
                n_cpf = st.text_input("CPF (Será a senha inicial):", key="m_ncpf")
                n_eml = st.text_input("E-mail oficial:", key="m_neml")
                n_oab = st.text_input("OAB (Opcional):", key="m_noab")
                n_uf = st.selectbox("UF OAB:", ESTADOS_BR, index=18, key="m_nuf")

            if st.button("Finalizar Cadastro", type="primary", use_container_width=True):
                cpf_limpo = re.sub(r'\D', '', n_cpf)
                erros = []
                if any(u.get("usuario") == n_usr.lower() for u in usuarios): erros.append("Login já em uso.")
                if len(cpf_limpo) != 11: erros.append("CPF deve ter 11 dígitos.")
                if not n_usr.strip() or not n_esc: erros.append("Preencha Login e Escritório.")
                
                if erros:
                    for e in erros: st.error(e)
                else:
                    id_final = n_esc.strip().lower().replace(" ", "_")
                    usuarios.append({
                        "usuario": n_usr.strip().lower(),
                        "senha_hash": _hash(cpf_limpo),
                        "nome_completo": n_nom.strip(),
                        "cpf": cpf_limpo,
                        "email": n_eml.strip().lower(),
                        "oab": n_oab.strip(),
                        "oab_uf": n_uf,
                        "papel": papel_padrao,
                        "escritorio_id": id_final,
                        "admin": (papel_padrao == "Sócio"),
                        "ativo": True,
                        "requer_reset": True
                    })
                    salvar_usuarios(usuarios)
                    # Cria a pasta silo do escritório para isolar os dados
                    os.makedirs(os.path.join(PASTA_BASE, id_final), exist_ok=True)
                    st.success(f"✅ Usuário '{n_usr}' criado com sucesso no grupo '{id_final}'!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

    with tab_gestao:
        for u in sorted(usuarios, key=lambda x: x.get("escritorio_id", "")):
            if u.get("papel") == "Master": continue
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.markdown(f"**{u['nome_completo']}** ({u['papel']})")
                col1.caption(f"Escritório: **{u['escritorio_id']}** | CPF: {u.get('cpf', 'Não inf.')} | E-mail: {u.get('email', '')}")
                
                if col2.button("🔄 Resetar Senha", key=f"res_m_{u['usuario']}", use_container_width=True):
                    cpf_usuario = u.get("cpf", "")
                    if cpf_usuario:
                        u["senha_hash"] = _hash(cpf_usuario)
                        u["requer_reset"] = True
                        salvar_usuarios(usuarios)
                        st.success(f"Senha resetada para o CPF!")
                    else:
                        st.error("Usuário sem CPF cadastrado.")
                        
                if col3.button("🗑️ Excluir", key=f"del_m_{u['usuario']}", use_container_width=True):
                    usuarios = [gu for gu in usuarios if gu["usuario"] != u["usuario"]]
                    salvar_usuarios(usuarios)
                    st.rerun()

# 2. ADMINISTRAÇÃO DO SÓCIO - Gerencia apenas a equipe do seu próprio escritório
elif menu == "⚙️ Administracao" and papel_atual == "Sócio":
    st.header("⚙️ Administração da Equipe")
    
    # ── VARIÁVEL BLINDADA ──
    # Pega o escritório de forma segura e guarda numa variável para usar no resto da página
    escritorio_atual = st.session_state.get("escritorio_id", "matriz")
    st.caption(f"Escritório: **{escritorio_atual}**")

    # === BOTÕES DE BACKUP AQUI ===
    st.divider()
    st.subheader("🛡️ Segurança e Backup de Dados")
    col_back, col_rest = st.columns(2)

    with col_back:
        st.markdown("**1. Gerar Cópia de Segurança**")
        st.caption("Baixe todos os dados do escritório em um ZIP.")
        if st.button("Preparar Backup"):
            dados_zip = realizar_backup_completo()
            st.download_button("📥 Baixar Backup", data=dados_zip, file_name="backup_jurismind.zip", mime="application/zip")

    with col_rest:
        st.markdown("**2. Restaurar Dados (Upload)**")
        st.caption("⚠️ Substitui o banco de dados atual.")
        arquivo_upload = st.file_uploader("Subir arquivo .json (Ex: clientes.json)", type=["json"])
        if arquivo_upload and st.button("🚀 Confirmar Substituição", type="primary"):
            substituir_banco_dados(arquivo_upload.name, arquivo_upload.getvalue())
            st.success("✅ Arquivo substituído com sucesso!")
            time.sleep(2)
            st.rerun()
    
    usuarios = carregar_usuarios()
    # Filtra apenas os usuários que pertencem ao mesmo escritório do Sócio logado usando a variável segura
    equipe = [u for u in usuarios if u.get("escritorio_id") == escritorio_atual]
    
    with st.expander("👥 Adicionar Novo Membro ao Escritório"):
        n1, n2 = st.columns(2)
        with n1:
            n_usr = st.text_input("Login:", key="eq_log")
            n_nom = st.text_input("Nome completo:", key="eq_nom")
            n_cpf = st.text_input("CPF (Senha inicial):", key="eq_cpf")
        with n2:
            n_eml = st.text_input("E-mail:", key="eq_eml")
            # O Sócio pode escolher a função do novo membro
            n_papel = st.selectbox("Função no Escritório:", ["Associado", "Controlador", "Sócio"], key="eq_papel")
            n_oab = st.text_input("OAB (Opcional):", key="eq_oab")
            n_uf = st.selectbox("UF OAB:", ESTADOS_BR, index=18, key="eq_uf")
            
        if st.button("Salvar Membro", type="primary"):
            cpf_limpo = re.sub(r'\D', '', n_cpf)
            if len(cpf_limpo) == 11 and n_usr.strip():
                usuarios.append({
                    "usuario": n_usr.strip().lower(),
                    "senha_hash": _hash(cpf_limpo),
                    "nome_completo": n_nom.strip(),
                    "cpf": cpf_limpo,
                    "email": n_eml.strip().lower(),
                    "oab": n_oab.strip(),
                    "oab_uf": n_uf, 
                    "papel": n_papel,
                    "escritorio_id": escritorio_atual, # Variável segura aplicada aqui
                    "admin": (n_papel == "Sócio"),
                    "ativo": True,
                    "requer_reset": True
                })
                salvar_usuarios(usuarios)
                st.success("Membro adicionado com sucesso!")
                st.rerun()
            else:
                st.error("Erro: CPF inválido ou Login vazio.")

    st.divider()
    st.subheader("Membros da Equipe")
    for u in equipe:
        if u["usuario"] == usr_atual: continue
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{u['nome_completo']}** ({u['papel']})")
            c1.caption(f"E-mail: {u.get('email')} | CPF: {u.get('cpf')}")
            
            if c2.button("🔄 Resetar", key=f"res_eq_{u['usuario']}", use_container_width=True):
                cpf_usuario = u.get("cpf", "")
                if cpf_usuario:
                    for gu in usuarios:
                        if gu["usuario"] == u["usuario"]:
                            gu["senha_hash"] = _hash(cpf_usuario)
                            gu["requer_reset"] = True
                            break
                    salvar_usuarios(usuarios)
                    st.success("Senha resetada para o CPF!")
                else:
                    st.error("Usuário sem CPF.")
                    
            if c3.button("🗑️ Excluir", key=f"ex_eq_{u['usuario']}", use_container_width=True):
                usuarios = [gu for gu in usuarios if gu["usuario"] != u["usuario"]]
                salvar_usuarios(usuarios)
                st.rerun()

# =======================================================
# ALTERAÇÃO DE SENHA (TODOS OS USUÁRIOS)
# =======================================================
elif menu == "🔑 Alterar Senha":
    st.header("🔑 Alterar Minha Senha")
    st.caption("Mantenha sua conta segura. Sua nova senha deve ter pelo menos 6 caracteres.")
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            senha_atual = st.text_input("Senha Atual:", type="password", key="pwd_atual")
            nova_senha = st.text_input("Nova Senha:", type="password", key="pwd_nova")
            confirma_senha = st.text_input("Confirme a Nova Senha:", type="password", key="pwd_confirma")

        if st.button("Salvar Nova Senha", type="primary"):
            if not senha_atual or not nova_senha or not confirma_senha:
                st.error("Preencha todos os campos.")
            elif _hash(senha_atual) != st.session_state.usuario_logado.get("senha_hash"):
                st.error("A senha atual está incorreta.")
            elif nova_senha != confirma_senha:
                st.error("As novas senhas não coincidem.")
            elif len(nova_senha) < 6:
                st.error("A nova senha deve ter no mínimo 6 caracteres.")
            else:
                usuarios = carregar_usuarios()
                for u in usuarios:
                    if u["usuario"] == usr_atual:
                        u["senha_hash"] = _hash(nova_senha)
                        u["requer_reset"] = False
                        st.session_state.usuario_logado["senha_hash"] = u["senha_hash"]
                        break
                salvar_usuarios(usuarios)
                st.success("✅ Senha alterada com sucesso!")
                time.sleep(2)
                st.rerun()