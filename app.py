import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import html
from datetime import date
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Anime Tracker - Tiago Garcéa", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0a0a0c; color: #ffffff; }
    div[data-testid="stMetric"] {
        background-color: #16161a; border: 1px solid #2d2d33;
        border-radius: 12px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }
    section[data-testid="stSidebar"] { min-width: 280px; }
    [data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container {
        max-width: 1100px; margin-left: auto; margin-right: auto;
    }
    div[data-testid="stTabs"] button { font-weight: 600; font-size: 0.9rem; }
    div[data-testid="stSidebar"] .stButton > button {
        width: 100%; background: #1e1e24; border: 1px solid #3d3d45;
        color: #a1a1aa; border-radius: 8px; font-size: 0.82rem; transition: all 0.2s ease;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        border-color: #e50914; color: #fff; background: rgba(229,9,20,0.1);
    }
    </style>
""", unsafe_allow_html=True)

SHEET_URL   = "https://docs.google.com/spreadsheets/d/1a6Ylv7yKu8yb1DJkYpZynTSedbOzTUC_ti35fufDyWI/export?format=csv&gid=1713940120"
PLACEHOLDER = "https://via.placeholder.com/300x420/16161a/555555?text=Sem+Capa"
CHART_BG    = "#0a0a0c"
CHART_PAPER = "#16161a"
GRID_COLOR  = "#2d2d33"
TEXT_COLOR  = "#a1a1aa"
ACCENT      = "#e50914"
COLORS      = ["#e50914","#f47521","#2e51a2","#ffcc00","#22c55e",
               "#a855f7","#06b6d4","#ec4899","#84cc16","#f97316"]

SORT_COLS = {
    "N° (padrão)": "N°",
    "Nome":        "Nome",
    "Score":       "Score",
    "Episódios":   "Episodes",
    "Visto em":    "_last_seen_dt",
    "Ano":         "_ano",
    "Studio":      "Studio",
}

def safe_str(val, fallback=""):
    s = str(val).strip()
    return fallback if s.lower() in ("nan", "none", "") else s

def opts_from(series: pd.Series) -> list:
    return sorted({v for v in series.dropna().astype(str).str.strip()
                   if v.lower() not in ("nan", "none", "")})

def plotly_layout(fig, title="", xaxis_title="", yaxis_title=""):
    fig.update_layout(
        title=dict(text=title, font=dict(color="#fff", size=15), x=0.02),
        paper_bgcolor=CHART_PAPER, plot_bgcolor=CHART_BG,
        font=dict(color=TEXT_COLOR, size=11),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title=xaxis_title, gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
                   tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(title=yaxis_title, gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
                   tickfont=dict(color=TEXT_COLOR)),
        showlegend=False,
    )
    return fig

@st.cache_data(ttl=30)
def load_data():
    raw = pd.read_csv(SHEET_URL, header=None)
    header_idx = 0
    for i, row in raw.head(10).iterrows():
        if "Episodes" in row.values or "Nome" in row.values:
            header_idx = i
            break
    df = pd.read_csv(SHEET_URL, skiprows=header_idx)
    df.columns = df.columns.str.strip()
    for col in ['N°', 'Score', 'Episodes', 'Time/episode', 'Rewatched']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'Last seen' in df.columns:
        _dt = pd.to_datetime(df['Last seen'], dayfirst=True, errors='coerce')
        df['_last_seen_dt']    = _dt.dt.date
        df['_last_seen_year']  = _dt.dt.year
        df['_last_seen_month'] = _dt.dt.to_period('M').astype(str)
    else:
        df['_last_seen_dt'] = df['_last_seen_year'] = df['_last_seen_month'] = None
    if 'Temporada' in df.columns:
        split = df['Temporada'].astype(str).str.strip().str.split(' ', n=1, expand=True)
        df['_season'] = split[0].str.strip().replace({'nan': '', 'None': ''})
        df['_ano']    = split[1].str.strip().replace({'nan': '', 'None': ''}) if 1 in split.columns else ''
    else:
        df['_season'] = df['_ano'] = ''
    df['Tempo_Total_Dias'] = (df['Episodes'] * df['Time/episode'] * (df['Rewatched'] + 1)) / 1440
    # Episódios totais contando rewatches: eps * (1 + rewatched)
    df['_eps_total']   = df['Episodes'] * (df['Rewatched'] + 1)
    # Episódios só de rewatch (excluindo a primeira vez)
    df['_eps_rewatch'] = df['Episodes'] * df['Rewatched']
    return df

def build_card(item) -> str:
    img = ""
    for col in ['Link', 'Imagem']:
        val = safe_str(item.get(col, ""))
        if val and val.startswith("http"):
            img = val
            break
    if not img:
        img = PLACEHOLDER
    nome_display = html.escape(safe_str(item.get('Nome', ''), 'Sem título'))
    is_fav       = "FAV" in str(item.get('Favorite', '')).upper()
    rw_val       = int(item.get('Rewatched', 0))
    score        = item.get('Score', 0)
    studio       = html.escape(safe_str(item.get('Studio', ''), '—'))
    eps          = int(item.get('Episodes', 0))
    genero       = html.escape(safe_str(item.get('Gênero', item.get('Genero', '')), '—'))
    tema         = html.escape(safe_str(item.get('Tema', ''), '—'))
    temporada    = html.escape(safe_str(item.get('Temporada', ''), '—'))
    visto_em     = html.escape(safe_str(item.get('Last seen', ''), '—'))
    comentario   = html.escape(safe_str(item.get('Coments', item.get('Comments', '')), ''))
    mal_url      = safe_str(item.get('URL_Pagina', ''))
    crunchy_url  = safe_str(item.get('Link do Anime', ''))

    fav_html    = '<div class="badge-fav">&#10084;</div>' if is_fav else ""
    rw_offset   = "left: 42px;" if is_fav else "left: 10px;"
    rw_html     = f'<div class="badge-rewatch" style="{rw_offset}">&#128260; {rw_val}</div>' if rw_val > 0 else ""
    score_badge = f'<span class="d-badge score-badge">&#9733; {score}</span>'
    fav_badge   = "<span class='d-badge fav-badge'>&#10084; FAV</span>" if is_fav else ""
    rw_badge    = f"<span class='d-badge rw-badge'>&#128260; {rw_val}x</span>" if rw_val > 0 else ""
    com_html    = f'<p class="detail-review">"{comentario}"</p>' if comentario else ""
    mal_btn     = f'<a href="{mal_url}" target="_blank" class="ext-btn btn-mal">MAL</a>' if mal_url.startswith("http") else ""
    cry_btn     = f'<a href="{crunchy_url}" target="_blank" class="ext-btn btn-crunchy">Crunchyroll</a>' if crunchy_url.startswith("http") else ""
    btns        = f'<div class="detail-buttons">{mal_btn}{cry_btn}</div>' if (mal_btn or cry_btn) else ""

    overlay = f'''<div class="detail-overlay">
        <div class="overlay-title">{nome_display}</div>
        <div class="overlay-badges">{score_badge}{fav_badge}{rw_badge}</div>
        <div class="overlay-meta">
            <span><b>Estúdio:</b> {studio}</span><span><b>Gênero:</b> {genero}</span>
            <span><b>Tema:</b> {tema}</span><span><b>Temporada:</b> {temporada}</span>
            <span><b>Eps:</b> {eps}</span><span><b>Visto em:</b> {visto_em}</span>
        </div>{com_html}{btns}
    </div>'''

    return f'''<div class="anime-container">
        {fav_html}{rw_html}
        <div class="badge-score">&#9733; {score}</div>
        <img src="{img}" class="poster-img" onerror="this.src='{PLACEHOLDER}'">
        <div class="anime-info">
            <div class="anime-title">{nome_display}</div>
            <div class="anime-details">{studio} &bull; {eps} eps</div>
        </div>{overlay}
    </div>'''

# ══════════════════════════════════════════════════════════════════════════════
try:
    df_raw = load_data()

    if "v"         not in st.session_state: st.session_state["v"]        = 0
    if "sort_col"  not in st.session_state: st.session_state["sort_col"] = "N° (padrão)"
    if "sort_asc"  not in st.session_state: st.session_state["sort_asc"] = True

    v = st.session_state["v"]

    st.markdown("""
        <div style='margin-bottom:20px;'>
            <h1 style='margin:0;'>🎬 ANIME <span style='color:#e50914;'>TRACKER</span></h1>
            <p style='margin:0;color:#888;'>Versão 2.3.2</p>
        </div>
    """, unsafe_allow_html=True)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    # (serão recalculados depois do filtro; aqui mostramos os totais globais)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("ANIMES ASSISTIDOS", len(df_raw))
    k2.metric("SCORE MÉDIO", f"{df_raw['Score'].mean():.2f}")
    total_dias = df_raw['Tempo_Total_Dias'].sum()
    k3.metric("TEMPO ASSISTIDO", f"{int(total_dias)}d {int((total_dias % 1) * 24)}h")

    # Episódios: total com rewatch + subtítulo em vermelho
    eps_total   = int(df_raw['_eps_total'].sum())
    eps_rewatch = int(df_raw['_eps_rewatch'].sum())
    with k4:
        st.markdown(f"""
            <div data-testid="stMetric" style="background:#16161a;border:1px solid #2d2d33;
                 border-radius:12px;padding:20px;box-shadow:0 4px 10px rgba(0,0,0,.5);">
                <div style="font-size:0.75rem;color:#a1a1aa;font-weight:600;
                            text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;">
                    EPISÓDIOS TOTAIS
                </div>
                <div style="font-size:2rem;font-weight:700;color:#fff;line-height:1.1;">
                    {eps_total:,}
                </div>
                <div style="font-size:0.82rem;color:#e50914;margin-top:4px;font-weight:600;">
                    &#128260; {eps_rewatch:,} eps de rewatch
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════════════════════
    sb = st.sidebar
    sb.header("🎯 Filtros")

    if sb.button("🗑️ Limpar todos os filtros"):
        st.session_state["v"]        = v + 1
        st.session_state["sort_col"] = "N° (padrão)"
        st.session_state["sort_asc"] = True
        st.rerun()

    sb.markdown("---")

    pool = df_raw.copy()

    # 1. Busca
    busca = sb.text_input("🔍 Buscar nome...", placeholder="Nome em JP ou EN", key=f"busca_{v}")
    if busca:
        mask = pool['Nome'].str.contains(busca, case=False, na=False)
        if 'Nome_Ingles' in pool.columns:
            mask |= pool['Nome_Ingles'].str.contains(busca, case=False, na=False)
        pool = pool[mask]

    sb.markdown("---")

    # 2. Score slider
    score_vals = sorted(pool['Score'][pool['Score'] > 0].unique())
    if score_vals:
        s_min, s_max = int(min(score_vals)), int(max(score_vals))
        if s_min < s_max:
            sb.markdown("**⭐ Score**")
            sc_from, sc_to = sb.slider(
                "score_range", min_value=s_min, max_value=s_max,
                value=(s_min, s_max), format="%d",
                label_visibility="collapsed", key=f"score_slider_{v}")
            c1, c2 = sb.columns(2)
            c1.markdown(f"<div style='font-size:.78rem;color:#a1a1aa;'>De<br>"
                        f"<b style='color:#fff;font-size:.85rem;'>{sc_from}</b></div>",
                        unsafe_allow_html=True)
            c2.markdown(f"<div style='font-size:.78rem;color:#a1a1aa;text-align:right;'>Até<br>"
                        f"<b style='color:#fff;font-size:.85rem;'>{sc_to}</b></div>",
                        unsafe_allow_html=True)
            pool = pool[(pool['Score'] >= sc_from) & (pool['Score'] <= sc_to)]

    # 3. Visto Entre
    valid_dates = sorted(set(pool['_last_seen_dt'].dropna().tolist()))
    if len(valid_dates) > 1:
        n = len(valid_dates) - 1
        sb.markdown("**📆 Visto Entre**")
        idx_from, idx_to = sb.slider(
            "intervalo_data", min_value=0, max_value=n,
            value=(0, n), format="%d",
            label_visibility="collapsed", key=f"date_slider_{v}")
        date_from = valid_dates[idx_from]
        date_to   = valid_dates[idx_to]
        c1, c2 = sb.columns(2)
        c1.markdown(f"<div style='font-size:.78rem;color:#a1a1aa;'>De<br>"
                    f"<b style='color:#fff;font-size:.85rem;'>{date_from.strftime('%d/%m/%Y')}</b></div>",
                    unsafe_allow_html=True)
        c2.markdown(f"<div style='font-size:.78rem;color:#a1a1aa;text-align:right;'>Até<br>"
                    f"<b style='color:#fff;font-size:.85rem;'>{date_to.strftime('%d/%m/%Y')}</b></div>",
                    unsafe_allow_html=True)
        in_range = pool['_last_seen_dt'].apply(
            lambda d: d is not None and date_from <= d <= date_to)
        pool = pool[pool['_last_seen_dt'].notna() & in_range]
    elif len(valid_dates) == 1:
        sb.markdown("**📆 Visto Em**")
        sb.caption(valid_dates[0].strftime('%d/%m/%Y'))

    sb.markdown("---")

    # 4. Season
    sel_season = sb.multiselect("🌸 Season", opts_from(pool['_season']), key=f"season_{v}")
    if sel_season:
        pool = pool[pool['_season'].isin(sel_season)]

    # 5. Ano
    sel_ano = sb.multiselect("📅 Ano", opts_from(pool['_ano']), key=f"ano_{v}")
    if sel_ano:
        pool = pool[pool['_ano'].isin(sel_ano)]

    sb.markdown("---")

    # 6. Estúdio
    sel_studio = sb.multiselect("🏢 Estúdio",
                                opts_from(pool['Studio']) if 'Studio' in pool.columns else [],
                                key=f"studio_{v}")
    if sel_studio:
        pool = pool[pool['Studio'].astype(str).str.strip().isin(sel_studio)]

    # 7. Gênero
    col_g      = 'Gênero' if 'Gênero' in pool.columns else 'Genero'
    sel_genero = sb.multiselect("🎭 Gênero",
                                opts_from(pool[col_g]) if col_g in pool.columns else [],
                                key=f"genero_{v}")
    if sel_genero:
        pool = pool[pool[col_g].astype(str).str.strip().isin(sel_genero)]

    # 8. Tema
    sel_tema = sb.multiselect("🏷️ Tema",
                              opts_from(pool['Tema']) if 'Tema' in pool.columns else [],
                              key=f"tema_{v}")
    if sel_tema:
        pool = pool[pool['Tema'].astype(str).str.strip().isin(sel_tema)]

    # 9. Demografia
    sel_demog = sb.multiselect("👥 Demografia",
                               opts_from(pool['Demografia']) if 'Demografia' in pool.columns else [],
                               key=f"demog_{v}")
    if sel_demog:
        pool = pool[pool['Demografia'].astype(str).str.strip().isin(sel_demog)]

    # 10. Favorito
    fav_opts = [fv for fv in opts_from(pool['Favorite']) if fv] if 'Favorite' in pool.columns else []
    sel_fav  = sb.multiselect("❤️ Favorito", fav_opts, key=f"fav_{v}")
    if sel_fav:
        pool = pool[pool['Favorite'].astype(str).str.strip().isin(sel_fav)]

    # 11. Rewatched — inclui 0 para filtrar animes sem rewatch
    if 'Rewatched' in pool.columns:
        rw_opts_set  = sorted({int(x) for x in pool['Rewatched'].unique()})  # inclui 0
        sel_rw       = sb.multiselect("🔁 Rewatched (nº vezes)",
                                      [str(x) for x in rw_opts_set],
                                      key=f"rw_{v}")
        if sel_rw:
            pool = pool[pool['Rewatched'].astype(int).astype(str).isin(sel_rw)]
    else:
        sel_rw = []

    sb.markdown("---")

    # 12. Ordenação
    sb.markdown("**↕️ Ordenar por**")
    cur_sort = st.session_state["sort_col"]
    cur_asc  = st.session_state["sort_asc"]

    for label in SORT_COLS:
        is_active = (cur_sort == label)
        arrow     = ("↑" if cur_asc else "↓") if is_active else "↕"
        if sb.button(f"{arrow} {label}", key=f"sort_{label}_{v}", use_container_width=True):
            if is_active:
                st.session_state["sort_asc"] = not cur_asc
            else:
                st.session_state["sort_col"] = label
                st.session_state["sort_asc"] = True
            st.rerun()

    # ── Aplica ordenação ──────────────────────────────────────────────────────
    df = pool.copy()
    sort_col_key = SORT_COLS[st.session_state["sort_col"]]
    sort_asc     = st.session_state["sort_asc"]
    if sort_col_key in df.columns:
        try:
            df = df.sort_values(by=sort_col_key, ascending=sort_asc, na_position='last',
                                key=lambda x: pd.to_numeric(x, errors='ignore'))
        except Exception:
            df = df.sort_values(by=sort_col_key, ascending=sort_asc, na_position='last')
    elif 'N°' in df.columns:
        df = df.sort_values(by='N°', ascending=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════════════════════════════════════
    tab_colecao, tab_graficos = st.tabs(["🎬 Coleção", "📊 Gráficos"])

    # ── TAB COLEÇÃO ───────────────────────────────────────────────────────────
    with tab_colecao:
        sort_label = st.session_state["sort_col"]
        sort_dir   = "↑ crescente" if sort_asc else "↓ decrescente"
        st.markdown(
            f"### Sua coleção ({len(df)} animes) "
            f"<span style='font-size:0.8rem;color:#a1a1aa;font-weight:normal;'>"
            f"— ordenado por <b style='color:#e50914'>{sort_label}</b> {sort_dir}</span>",
            unsafe_allow_html=True)

        cards_html = "".join(build_card(row) for _, row in df.iterrows())

        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0a0a0c;font-family:sans-serif;padding:4px;overflow-x:hidden;}}
.grid{{display:flex;flex-wrap:wrap;gap:14px;justify-content:flex-start;}}
.anime-container{{position:relative;background-color:#16161a;border-radius:12px;overflow:hidden;
  border:1px solid #2d2d33;transition:border-color .25s ease;width:calc(20% - 12px);min-width:160px;margin-bottom:5px;}}
.anime-container:hover{{border-color:#e50914;}}
.poster-img{{width:100%;height:280px;object-fit:cover;border-radius:12px 12px 0 0;border-bottom:1px solid #2d2d33;display:block;}}
.anime-info{{padding:10px;}}
.anime-title{{font-size:.82rem;font-weight:bold;color:#fff;margin-bottom:4px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.3;height:2.2rem;}}
.anime-details{{font-size:.74rem;color:#a1a1aa;}}
.badge-score{{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.75);padding:4px 8px;
  border-radius:6px;color:#ffcc00;font-weight:bold;font-size:.82em;z-index:5;}}
.badge-fav{{position:absolute;top:10px;left:10px;background:#e50914;color:white;width:26px;height:26px;
  border-radius:50%;display:flex;justify-content:center;align-items:center;font-size:.75em;z-index:5;}}
.badge-rewatch{{position:absolute;top:10px;background:rgba(255,255,255,.2);backdrop-filter:blur(5px);
  padding:2px 8px;border-radius:12px;font-size:.72em;z-index:5;color:#fff;}}
.detail-overlay{{position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(13,13,16,.97);
  border-radius:12px;padding:14px;z-index:20;pointer-events:none;opacity:0;transform:scale(.97);
  transition:opacity .2s ease,transform .2s ease;display:flex;flex-direction:column;gap:8px;overflow-y:auto;}}
.anime-container:hover .detail-overlay{{opacity:1;transform:scale(1);pointer-events:auto;}}
.overlay-title{{font-size:.88rem;font-weight:bold;color:#fff;line-height:1.35;}}
.overlay-badges{{display:flex;flex-wrap:wrap;gap:5px;}}
.d-badge{{padding:2px 8px;border-radius:10px;font-size:.72em;font-weight:bold;}}
.score-badge{{background:rgba(255,204,0,.15);color:#ffcc00;border:1px solid #ffcc00;}}
.fav-badge{{background:rgba(229,9,20,.2);color:#e50914;border:1px solid #e50914;}}
.rw-badge{{background:rgba(255,255,255,.1);color:#ccc;border:1px solid #555;}}
.overlay-meta{{display:flex;flex-direction:column;gap:3px;font-size:.74rem;color:#a1a1aa;}}
.overlay-meta b{{color:#ddd;}}
.detail-review{{font-size:.72rem;color:#888;font-style:italic;border-left:2px solid #e50914;padding-left:8px;line-height:1.4;}}
.detail-buttons{{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto;padding-top:4px;}}
.ext-btn{{display:inline-block;padding:5px 14px;border-radius:8px;font-size:.74rem;font-weight:bold;
  text-decoration:none;text-align:center;transition:opacity .15s ease,transform .15s ease;cursor:pointer;}}
.ext-btn:hover{{opacity:.85;transform:translateY(-1px);}}
.btn-mal{{background:#2e51a2;color:#fff;border:1px solid #3d65c4;}}
.btn-crunchy{{background:#f47521;color:#fff;border:1px solid #ff8c3a;}}
</style></head><body><div class="grid">{cards_html}</div></body></html>"""

        num_rows = (len(df) + 4) // 5
        components.html(full_html, height=max(500, num_rows * 395), scrolling=False)

    # ── TAB GRÁFICOS ──────────────────────────────────────────────────────────
    with tab_graficos:
        st.markdown("### 📊 Distribuição da Coleção")
        st.caption(f"Baseado nos {len(df)} animes filtrados atualmente.")

        def clean(col):
            return df[col].astype(str).str.strip().replace(
                {'nan': None, 'None': None, '': None}).dropna()

        # Linha 1: Score + Ano
        c1, c2 = st.columns(2)
        with c1:
            sc_df = df[df['Score'] > 0]['Score'].astype(int).value_counts().sort_index().reset_index()
            sc_df.columns = ['Score', 'Qtd']
            fig = px.bar(sc_df, x='Score', y='Qtd', color='Score',
                         color_continuous_scale=['#2e51a2','#e50914'], text='Qtd')
            fig.update_traces(textposition='outside', textfont_color='#fff')
            fig.update_coloraxes(showscale=False)
            plotly_layout(fig, "⭐ Distribuição por Score", "Score", "Animes")
            fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            ano_df = clean('_ano').value_counts().sort_index().reset_index()
            ano_df.columns = ['Ano', 'Qtd']
            fig = px.bar(ano_df, x='Ano', y='Qtd', text='Qtd', color_discrete_sequence=[ACCENT])
            fig.update_traces(textposition='outside', textfont_color='#fff')
            plotly_layout(fig, "📅 Animes por Ano de Lançamento", "Ano", "Animes")
            fig.update_layout(height=320)
            st.plotly_chart(fig, use_container_width=True)

        # Linha 2: Visto em (área)
        if '_last_seen_month' in df.columns:
            visto_df = df['_last_seen_month'].dropna().value_counts().sort_index().reset_index()
            visto_df.columns = ['Período', 'Qtd']
            if not visto_df.empty:
                fig = px.area(visto_df, x='Período', y='Qtd', color_discrete_sequence=[ACCENT])
                fig.update_traces(line_color=ACCENT, fillcolor="rgba(229,9,20,0.15)")
                plotly_layout(fig, "📆 Animes Assistidos ao Longo do Tempo", "Mês", "Animes")
                fig.update_layout(height=280)
                st.plotly_chart(fig, use_container_width=True)

        # Linha 3: Rewatch por anime (top 20, só quem tem rewatch > 0)
        rw_df = df[df['Rewatched'] > 0][['Nome', 'Rewatched']].copy()
        rw_df = rw_df.sort_values('Rewatched', ascending=False).head(20)
        if not rw_df.empty:
            rw_df = rw_df.sort_values('Rewatched', ascending=True)
            fig = px.bar(rw_df, x='Rewatched', y='Nome', orientation='h',
                         text='Rewatched', color='Rewatched',
                         color_continuous_scale=['#2d2d33', '#f47521'])
            fig.update_traces(textposition='outside', textfont_color='#fff')
            fig.update_coloraxes(showscale=False)
            plotly_layout(fig, "🔁 Top 20 Animes com Mais Rewatches", "Rewatches", "")
            fig.update_layout(height=max(320, len(rw_df) * 28 + 60),
                              yaxis=dict(tickfont=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True)

        # Linha 4: Estúdio + Tema
        c3, c4 = st.columns(2)
        with c3:
            st_df = clean('Studio').value_counts().head(15).reset_index()
            st_df.columns = ['Studio', 'Qtd']
            st_df = st_df.sort_values('Qtd')
            fig = px.bar(st_df, x='Qtd', y='Studio', orientation='h', text='Qtd',
                         color='Qtd', color_continuous_scale=['#2d2d33', ACCENT])
            fig.update_traces(textposition='outside', textfont_color='#fff')
            fig.update_coloraxes(showscale=False)
            plotly_layout(fig, "🏢 Top 15 Estúdios", "Animes", "")
            fig.update_layout(height=420, yaxis=dict(tickfont=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True)
        with c4:
            if 'Tema' in df.columns:
                tm_df = clean('Tema').value_counts().head(12).reset_index()
                tm_df.columns = ['Tema', 'Qtd']
                tm_df = tm_df.sort_values('Qtd')
                fig = px.bar(tm_df, x='Qtd', y='Tema', orientation='h', text='Qtd',
                             color='Qtd', color_continuous_scale=['#2d2d33', '#f47521'])
                fig.update_traces(textposition='outside', textfont_color='#fff')
                fig.update_coloraxes(showscale=False)
                plotly_layout(fig, "🏷️ Top 12 Temas", "Animes", "")
                fig.update_layout(height=420, yaxis=dict(tickfont=dict(size=10)))
                st.plotly_chart(fig, use_container_width=True)

        # Linha 5: Demografia + Gênero
        c5, c6 = st.columns(2)
        with c5:
            if 'Demografia' in df.columns:
                dem_df = clean('Demografia').value_counts().reset_index()
                dem_df.columns = ['Demografia', 'Qtd']
                fig = px.pie(dem_df, names='Demografia', values='Qtd',
                             color_discrete_sequence=COLORS, hole=0.45)
                fig.update_traces(textposition='outside', textinfo='label+percent',
                                  textfont_color='#ddd',
                                  marker=dict(line=dict(color='#0a0a0c', width=2)))
                fig.update_layout(
                    title=dict(text="👥 Distribuição por Demografia",
                               font=dict(color="#fff", size=15), x=0.02),
                    paper_bgcolor=CHART_PAPER, plot_bgcolor=CHART_BG,
                    font=dict(color=TEXT_COLOR), showlegend=True, height=360,
                    margin=dict(l=10, r=10, t=40, b=10),
                    legend=dict(font=dict(color=TEXT_COLOR), bgcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fig, use_container_width=True)
        with c6:
            col_g2 = 'Gênero' if 'Gênero' in df.columns else 'Genero'
            if col_g2 in df.columns:
                gen_df = clean(col_g2).value_counts().reset_index()
                gen_df.columns = ['Gênero', 'Qtd']
                fig = px.pie(gen_df, names='Gênero', values='Qtd',
                             color_discrete_sequence=COLORS, hole=0.45)
                fig.update_traces(textposition='outside', textinfo='label+percent',
                                  textfont_color='#ddd',
                                  marker=dict(line=dict(color='#0a0a0c', width=2)))
                fig.update_layout(
                    title=dict(text="🎭 Distribuição por Gênero",
                               font=dict(color="#fff", size=15), x=0.02),
                    paper_bgcolor=CHART_PAPER, plot_bgcolor=CHART_BG,
                    font=dict(color=TEXT_COLOR), showlegend=True, height=360,
                    margin=dict(l=10, r=10, t=40, b=10),
                    legend=dict(font=dict(color=TEXT_COLOR), bgcolor='rgba(0,0,0,0)'))
                st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.exception(e)