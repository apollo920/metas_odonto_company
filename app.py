import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO

# ------------------------------------------------------------
# CONFIG DO LAYOUT
# ------------------------------------------------------------
st.set_page_config(page_title="Dashboard Smile – Estilizado", layout="wide")

STYLE = """
<style>
.big-title {
    font-size: 42px;
    font-weight: 900;
    color: #764ba2;
    margin-bottom: 25px;
}
.card {
    padding: 25px;
    border-radius: 18px;
    color: white;
    font-size: 22px;
    font-weight: bold;
    box-shadow: 0 4px 18px rgba(0,0,0,0.18);
}
.venda {background: linear-gradient(135deg,#667eea,#764ba2);}
.vista {background: linear-gradient(135deg,#56ab2f,#a8e063);}
.crediario {background: linear-gradient(135deg,#f093fb,#f5576c);}
.orto {background: linear-gradient(135deg,#4facfe,#00f2fe);}
.section-title {
    font-size: 26px;
    font-weight: 700;
    margin-top: 40px;
    margin-bottom: -10px;
    color: #5a67d8;
}
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

st.markdown("<div class='big-title'>📊 Dashboard Smile Concept</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# LINK FIXO DO GOOGLE DRIVE
# ------------------------------------------------------------
DRIVE_LINK = "https://docs.google.com/spreadsheets/d/1iVq7BxrI7HBnjKR_BM9-TvOnYinGeF0a/edit?usp=sharing&ouid=108175523352005481997&rtpof=true&sd=true"


# ------------------------------------------------------------
# FUNÇÃO PARA BAIXAR ARQUIVO DO GOOGLE DRIVE
# ------------------------------------------------------------
def load_drive(url):
    file_id = url.split("/d/")[1].split("/")[0]
    download = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    response = requests.get(download)
    content = response.content

    if content[:15].lower().startswith(b"<!doctype html"):
        raise ValueError("⚠ O Google Drive devolveu HTML. O arquivo precisa estar público.")
    
    # Ler SEM cabeçalho, todas as linhas como dados
    return pd.read_excel(BytesIO(content), sheet_name="Planilha1", engine="openpyxl", header=None)

df = load_drive(DRIVE_LINK)

# Mostrar preview da estrutura da planilha para debug
st.sidebar.write("**Preview da Planilha (primeiras 10 linhas):**")
st.sidebar.dataframe(df.head(10))

# ------------------------------------------------------------
# DETECTAR COLUNA ONDE COMEÇAM OS DIAS
# ------------------------------------------------------------
def detectar_coluna_primeiro_dia(df):
    """
    Procura em TODAS as linhas da planilha por uma célula que contenha
    um valor que pareça ser o dia 1 (ou 01).
    Retorna (linha, coluna) onde encontrou.
    """
    import re
    
    for row_idx in range(min(20, len(df))):  # Procurar nas primeiras 20 linhas
        for col_idx in range(len(df.columns)):
            valor = df.iloc[row_idx, col_idx]
            
            # Pular valores vazios/NaN
            if pd.isna(valor):
                continue
            
            # Converter para string
            valor_str = str(valor).strip().lower()
            
            # Remover caracteres especiais
            valor_str = re.sub(r"[^0-9a-zA-Z/.\- ]", "", valor_str)
            
            # Verificar padrões de dia 1
            padroes_dia_1 = [
                r"^1$",                # Apenas "1"
                r"^01$",               # Apenas "01"
                r"^1[-/]",             # "1-" ou "1/"
                r"^01[-/]",            # "01-" ou "01/"
                r"^1nov",              # "1nov"
                r"^01nov",             # "01nov"
                r"^1 de",              # "1 de novembro"
                r"2025-11-01",         # ISO format
            ]
            
            for padrao in padroes_dia_1:
                if re.search(padrao, valor_str):
                    st.sidebar.success(f"✅ Encontrei o dia 1 na linha {row_idx}, coluna {col_idx}: '{valor}'")
                    return row_idx, col_idx
    
    # Se não encontrou, mostrar erro detalhado
    st.error("❌ Não consegui encontrar a coluna do dia 1 em nenhuma linha.")
    st.write("**Primeiras 10 linhas da planilha:**")
    st.dataframe(df.head(10))
    raise ValueError("Não encontrei o primeiro dia na planilha.")

linha_dias, col_inicio = detectar_coluna_primeiro_dia(df)


# ------------------------------------------------------------
# FUNÇÃO DE LEITURA COMPLETA
# ------------------------------------------------------------
def ler_planilha(df, linha_dias, col_inicio):
    """
    Agora que sabemos onde estão os dias, vamos ajustar os índices.
    Se linha_dias não for 0, precisamos ajustar todas as referências.
    """

    # Índices das linhas (0-based do pandas)
    # Baseado na planilha Excel
    LIN_VENDA      = 5   # Linha 6 no Excel - VENDA
    LIN_VISTA      = 6   # Linha 7 no Excel - VENDA À VISTA
    LIN_CREDIARIO  = 7   # Linha 8 no Excel - RECEBIMENTO PARTICULAR CREDIÁRIO
    LIN_ORTO       = 8   # Linha 9 no Excel - RECEBIMENTO ORTO

    LIN_META_TOTAL = 14  # Linha 15 no Excel - RECEBIMENTO TOTAL MÊS
    LIN_CONVERSAO  = 16  # Linha 17 no Excel
    LIN_ORCAMENTOS = 17  # Linha 18 no Excel
    LIN_ORTOS_PGTO = 19  # Linha 20 no Excel
    LIN_INST_AP    = 20  # Linha 21 no Excel

    # Colunas base
    COL_META = 2  # Coluna C - META
    COL_DIA = 3   # Coluna D - DIA
    COL_ACUM = 4  # Coluna E - ACUMULADO MÊS

    # Nome do Mês - procurar em várias células possíveis
    mes_nome = "NOVEMBRO"
    for i in range(min(10, len(df))):
        for j in range(min(5, len(df.columns))):
            val = str(df.iloc[i, j]).upper()
            if "NOVEMBRO" in val or "DEZEMBRO" in val or "JANEIRO" in val:
                # Extrair só o nome do mês
                for mes in ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
                           "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]:
                    if mes in val:
                        mes_nome = mes
                        break
                break

    # Pegar os dias da linha identificada (linha 3, índice 3)
    # As colunas vão de F (índice 5) até AI (índice 34) = 30 dias
    col_inicio_real = 5  # Coluna F
    col_fim = 35  # Coluna AI (30 colunas: F até AI)
    
    dias_raw = df.iloc[3, col_inicio_real:col_fim].values  # Linha 4 do Excel = índice 3
    
    # Criar nomes formatados dos dias
    dias_formatados = []
    for dia_val in dias_raw:
        if pd.isna(dia_val):
            # Se não tem valor, usar número sequencial
            dias_formatados.append(f"{len(dias_formatados) + 1} {mes_nome}")
            continue
        try:
            # Tentar extrair o número do dia
            dia_str = str(dia_val).strip()
            if "-" in dia_str or "/" in dia_str:
                numero = int(dia_str.split("-")[0].split("/")[0])
            else:
                numero = int(float(dia_str))
            dias_formatados.append(f"{numero} {mes_nome}")
        except:
            # Se falhar, usar número sequencial
            dias_formatados.append(f"{len(dias_formatados) + 1} {mes_nome}")
    
    # Número de dias = quantidade de colunas entre F e AI
    n_dias = len(dias_formatados)
    
    # Ajustar col_inicio para pegar dados das mesmas colunas
    col_inicio = col_inicio_real

    # Valores diários (ajustar linhas conforme necessário)
    venda = pd.to_numeric(df.iloc[LIN_VENDA, col_inicio:col_inicio+n_dias], errors="coerce").fillna(0)
    vista = pd.to_numeric(df.iloc[LIN_VISTA, col_inicio:col_inicio+n_dias], errors="coerce").fillna(0)
    cred  = pd.to_numeric(df.iloc[LIN_CREDIARIO, col_inicio:col_inicio+n_dias], errors="coerce").fillna(0)
    orto  = pd.to_numeric(df.iloc[LIN_ORTO, col_inicio:col_inicio+n_dias], errors="coerce").fillna(0)

    dados_diarios = pd.DataFrame({
        "Dia": dias_formatados,
        "Venda": venda.values,
        "Vista": vista.values,
        "Crediário": cred.values,
        "Orto": orto.values
    })

    # Metas e indicadores
    try:
        metas = {
            "venda": pd.to_numeric(df.iloc[LIN_VENDA, COL_META], errors="coerce"),
            "vista": pd.to_numeric(df.iloc[LIN_VISTA, COL_META], errors="coerce"),
            "crediario": pd.to_numeric(df.iloc[LIN_CREDIARIO, COL_META], errors="coerce"),
            "orto": pd.to_numeric(df.iloc[LIN_ORTO, COL_META], errors="coerce"),
            "meta_total": pd.to_numeric(df.iloc[LIN_META_TOTAL, COL_META], errors="coerce"),
        }
        
        # Valores acumulados do mês (Coluna E)
        acumulados = {
            "venda": pd.to_numeric(df.iloc[LIN_VENDA, COL_ACUM], errors="coerce"),
            "vista": pd.to_numeric(df.iloc[LIN_VISTA, COL_ACUM], errors="coerce"),
            "crediario": pd.to_numeric(df.iloc[LIN_CREDIARIO, COL_ACUM], errors="coerce"),
            "orto": pd.to_numeric(df.iloc[LIN_ORTO, COL_ACUM], errors="coerce"),
        }

        # Indicadores das linhas 12 e 13 (índices 11 e 12)
        indicadores = {
            "conversao": 50,  # Valor padrão - ajustar conforme a planilha
            "orcamentos": 60,  # Valor padrão
            "ortos_pgto": pd.to_numeric(df.iloc[11, COL_DIA], errors="coerce") if pd.notna(df.iloc[11, COL_DIA]) else 0,
            "instalacao": pd.to_numeric(df.iloc[12, COL_DIA], errors="coerce") if pd.notna(df.iloc[12, COL_DIA]) else 0,
        }
        
        # Debug para verificar os valores lidos
        st.sidebar.write("**Debug - Valores extraídos:**")
        st.sidebar.write(f"VENDA - Meta: R$ {metas['venda']:,.2f} | Acumulado: R$ {acumulados['venda']:,.2f}")
        st.sidebar.write(f"VISTA - Meta: R$ {metas['vista']:,.2f} | Acumulado: R$ {acumulados['vista']:,.2f}")
        st.sidebar.write(f"CREDIÁRIO - Meta: R$ {metas['crediario']:,.2f} | Acumulado: R$ {acumulados['crediario']:,.2f}")
        st.sidebar.write(f"ORTO - Meta: R$ {metas['orto']:,.2f} | Acumulado: R$ {acumulados['orto']:,.2f}")
        
    except Exception as e:
        st.warning(f"⚠️ Erro ao ler metas/indicadores: {str(e)}")
        metas = {"venda": 100000, "vista": 58000, "crediario": 33127.16, "orto": 16670, "meta_total": 107797.16}
        acumulados = {"venda": 82745, "vista": 44104.77, "crediario": 19116.15, "orto": 13425.23}
        indicadores = {"conversao": 50, "orcamentos": 60, "ortos_pgto": 0, "instalacao": 0}

    return metas, indicadores, dados_diarios, acumulados


# ------------------------------------------------------------
# PEGAR OS DADOS DA PLANILHA
# ------------------------------------------------------------
metas, indicadores, dados_diarios, acumulados = ler_planilha(df, linha_dias, col_inicio)


# ------------------------------------------------------------
# CARDS RESUMO (usando valores acumulados)
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"<div class='card venda'>💰 Venda<br>R$ {acumulados['venda']:,.2f}</div>", unsafe_allow_html=True)
col2.markdown(f"<div class='card vista'>💵 Vista<br>R$ {acumulados['vista']:,.2f}</div>", unsafe_allow_html=True)
col3.markdown(f"<div class='card crediario'>💳 Crediário<br>R$ {acumulados['crediario']:,.2f}</div>", unsafe_allow_html=True)
col4.markdown(f"<div class='card orto'>🦷 Orto<br>R$ {acumulados['orto']:,.2f}</div>", unsafe_allow_html=True)


# ------------------------------------------------------------
# GRÁFICOS
# ------------------------------------------------------------
st.markdown("<div class='section-title'>📊 Gráficos de Performance</div>", unsafe_allow_html=True)

g1, g2 = st.columns(2)
g3, g4 = st.columns(2)


# 1) Meta vs Realizado (com valores nas colunas)
with g1:
    st.markdown("**Meta vs Realizado**")

    df_meta = pd.DataFrame({
        "Categoria": ["Venda", "Vista", "Crediário", "Orto"],
        "Meta": [
            metas["venda"], metas["vista"], metas["crediario"], metas["orto"]
        ],
        "Realizado": [
            acumulados["venda"], acumulados["vista"], acumulados["crediario"], acumulados["orto"]
        ]
    })
    
    fig1 = px.bar(df_meta, x="Categoria", y=["Meta", "Realizado"], 
                  barmode="group", 
                  text_auto='.2s')  # Formato abreviado dos números
    
    fig1.update_traces(texttemplate='R$ %{y:,.0f}', textposition='outside')
    fig1.update_layout(yaxis_title="Valor (R$)", height=450)
    
    st.plotly_chart(fig1, use_container_width=True)


# 2) Evolução diária (eixos invertidos)
with g2:
    st.markdown("**Evolução Diária**")
    st.plotly_chart(px.line(dados_diarios, x="Dia",
                            y=["Venda", "Vista", "Crediário", "Orto"],
                            markers=True,
                            orientation='h'), use_container_width=True)


# 3) Composição das vendas
with g3:
    st.markdown("**Composição das Vendas**")
    st.plotly_chart(
        px.pie(
            names=["Vista", "Crediário", "Orto"],
            values=[acumulados["vista"], acumulados["crediario"], acumulados["orto"]],
            hole=0.35
        ),
        use_container_width=True
    )


# 4) Gap para metas (com valores destacados)
with g4:
    st.markdown("**Gap para atingir metas**")
    df_gap = df_meta.copy()
    df_gap["Gap"] = df_gap["Meta"] - df_gap["Realizado"]
    
    fig4 = px.bar(df_gap, x="Categoria", y="Gap", 
                  color="Gap",
                  text="Gap")
    
    fig4.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
    fig4.update_layout(
        yaxis_title="Gap (R$)",
        height=450,
        showlegend=False
    )
    
    st.plotly_chart(fig4, use_container_width=True)


# ------------------------------------------------------------
# TABELA FINAL COM ESTILO SIMPLIFICADO
# ------------------------------------------------------------
st.markdown("<div class='section-title'>📋 Dados Diários</div>", unsafe_allow_html=True)

# Adicionar índice começando de 0
dados_display = dados_diarios.copy()
dados_display.insert(0, 'Índice', range(len(dados_display)))

# Reordenar colunas para melhor visualização
dados_display = dados_display[['Índice', 'Dia', 'Venda', 'Vista', 'Crediário', 'Orto']]

# Formatar valores como moeda
for col in ['Venda', 'Vista', 'Crediário', 'Orto']:
    dados_display[col] = dados_display[col].apply(lambda x: f'R$ {x:,.2f}')

# Exibir tabela
st.dataframe(
    dados_display,
    use_container_width=True,
    height=400,
    hide_index=True
)