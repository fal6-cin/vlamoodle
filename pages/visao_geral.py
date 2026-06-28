# ==============================================================================
# SEÇÃO 1: IMPORTS E CONFIGURAÇÕES INICIAIS
# ==============================================================================
import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Registrando esta página para que o app.py encontre
dash.register_page(__name__, path='/', name='Visão Geral')

# Carregar os dados
df_logstore = pd.read_csv('datasets/logstore_filtered.csv', sep=';')
df_logstore['timecreated_dt'] = pd.to_datetime(df_logstore['timecreated_dt'])
df_students = pd.read_csv('datasets/students_anon.csv', sep=';')
df_forums = pd.read_csv('datasets/forum_interations.csv', sep=';')
df_notas = pd.read_csv('datasets/notas.csv', sep=';')
df_atrasadas = pd.read_csv('datasets/atividadesatrasadas.csv', sep=';')
df_mods = pd.read_csv('datasets/mods.csv', sep=';')
df_quiz = pd.read_csv('datasets/quizattemp.csv', sep=';')

# ==============================================================================
# FUNÇÕES UTILITÁRIAS E PRÉ-CÁLCULOS
# ==============================================================================
def format_duration(seconds):
    if pd.isna(seconds) or seconds == 0: return "0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

# Pré-calcular estatísticas por turma (Somatórios)
_df_all = df_logstore.copy()
_df_all['timecreated_dt'] = pd.to_datetime(_df_all['timecreated_dt'], errors='coerce')
_df_all = _df_all.sort_values(by=['userid', 'timecreated_dt'])

_df_all['time_diff'] = _df_all.groupby('userid')['timecreated_dt'].diff().dt.total_seconds()
_df_all['is_new_session'] = (_df_all['time_diff'] > 3600) | _df_all['time_diff'].isna()
_df_all['session_id'] = _df_all.groupby('userid')['is_new_session'].cumsum()

_turmas_stats = []
_turmas = df_students['grupos_do_aluno'].dropna().unique()

for turma in _turmas:
    _alunos = df_students[df_students['grupos_do_aluno'] == turma]['userid']
    _df_t = _df_all[_df_all['grupos_do_aluno'] == turma]
    
    t_sessoes = _df_t['is_new_session'].sum()
    t_views = (_df_t['action'] == 'viewed').sum()
    t_dias = _df_t['data'].nunique() if 'data' in _df_t.columns else _df_t['timecreated_dt'].dt.date.nunique()
    
    _sess_dur = _df_t.groupby(['userid', 'session_id'])['timecreated_dt'].agg(lambda x: (x.max() - x.min()).total_seconds())
    t_tempo = _sess_dur.sum() if not _sess_dur.empty else 0.0
    t_duracao_media = _sess_dur.mean() if not _sess_dur.empty else 0.0
    
    _df_f = df_forums[df_forums['userid'].isin(_alunos)]
    t_posts = len(_df_f[_df_f['tipo_interacao'].astype(str).str.lower().isin(['postagem', 'post'])])
    t_resp = len(_df_f[_df_f['tipo_interacao'].astype(str).str.lower().isin(['resposta', 'reply'])])
    t_leit = len(_df_t[(_df_t['component'] == 'mod_forum') & (_df_t['action'] == 'viewed')])
    
    t_media_notas = 0.0
    _notas_alunos = df_notas[df_notas['userid'].isin(_alunos)]
    if not _notas_alunos.empty:
        t_media_notas = _notas_alunos.groupby('userid')['nota_normalizada'].mean().mean()
        if pd.isna(t_media_notas): t_media_notas = 0.0
        
    _turmas_stats.append({
        'turma': turma,
        'sessoes': t_sessoes, 'views': t_views, 'dias': t_dias, 
        'tempo': t_tempo, 'duracao': t_duracao_media,
        'posts': t_posts, 'resp': t_resp, 'leit': t_leit,
        'media_notas': t_media_notas
    })

_df_stats = pd.DataFrame(_turmas_stats)
GLOBAL_MEANS = {
    'sessoes': int(_df_stats['sessoes'].mean()),
    'views': int(_df_stats['views'].mean()),
    'dias': int(_df_stats['dias'].mean()),
    'tempo': _df_stats['tempo'].mean(),
    'duracao': _df_stats['duracao'].mean(),
    'posts': int(_df_stats['posts'].mean()),
    'resp': int(_df_stats['resp'].mean()),
    'leit': int(_df_stats['leit'].mean())
}

MEDIA_ACESSOS_GLOBAL = GLOBAL_MEANS['sessoes']
MEDIA_ALUNOS_TURMA = df_students.groupby('grupos_do_aluno').size().mean()

del _df_all
DF_STATS_GLOBAL = _df_stats


# PRE-CALCULO ALUNOS EM RISCO GLOBAIS
_dff_r = df_students.copy()
_last_access = df_logstore.groupby('userid')['timecreated_dt'].max().reset_index(name='ultimo_acesso')
_dff_r = pd.merge(_dff_r, _last_access, on='userid', how='left')

_criacao = df_forums[df_forums['tipo_interacao'] == 'create'].groupby('userid').size().reset_index(name='qtd_criacao_forum')
_dff_r = pd.merge(_dff_r, _criacao, on='userid', how='left')

_resposta = df_forums[df_forums['tipo_interacao'] == 'response'].groupby('userid').size().reset_index(name='qtd_resposta_forum')
_dff_r = pd.merge(_dff_r, _resposta, on='userid', how='left')

_leitura = df_logstore[(df_logstore['component'] == 'mod_forum') & (df_logstore['action'] == 'viewed')].groupby('userid').size().reset_index(name='qtd_leitura_forum')
_dff_r = pd.merge(_dff_r, _leitura, on='userid', how='left')

_data_limite = pd.to_datetime('2026-06-20')
_data_inicio = _data_limite - pd.Timedelta(days=30)
_mask_30_dias = (df_logstore['timecreated_dt'] >= _data_inicio) & (df_logstore['timecreated_dt'] <= _data_limite)
_df_30_dias = df_logstore[_mask_30_dias].copy()
_df_30_dias = _df_30_dias.sort_values(by=['userid', 'timecreated_dt'])
_df_30_dias['time_diff'] = _df_30_dias.groupby('userid')['timecreated_dt'].diff().dt.total_seconds()
_df_30_dias['is_new_session'] = (_df_30_dias['time_diff'] > 3600) | _df_30_dias['time_diff'].isna()
_acessos_30 = _df_30_dias.groupby('userid')['is_new_session'].sum().reset_index(name='acessos_30_dias')
_dff_r = pd.merge(_dff_r, _acessos_30, on='userid', how='left')

for col in ['qtd_criacao_forum', 'qtd_resposta_forum', 'qtd_leitura_forum', 'acessos_30_dias']:
    _dff_r[col] = _dff_r[col].fillna(0).astype(int)

_media_notas = df_notas.groupby('userid')['nota_normalizada'].mean().reset_index(name='media_notas')
_dff_r = pd.merge(_dff_r, _media_notas, on='userid', how='left')
_dff_r['media_notas'] = _dff_r['media_notas'].fillna(0)

_atrasadas = df_atrasadas.groupby('userid').size().reset_index(name='qtd_atividades_atrasadas')
_dff_r = pd.merge(_dff_r, _atrasadas, on='userid', how='left')
_dff_r['qtd_atividades_atrasadas'] = _dff_r['qtd_atividades_atrasadas'].fillna(0).astype(int)

_dff_r['Em Risco'] = (
    (_dff_r['qtd_criacao_forum'] == 0) & 
    (_dff_r['qtd_resposta_forum'] == 0) & 
    (_dff_r['qtd_leitura_forum'] == 0) & 
    (_dff_r['acessos_30_dias'] == 0) & 
    (_dff_r['media_notas'] < 6) & 
    (_dff_r['qtd_atividades_atrasadas'] > 1) &
    (_dff_r['ultimo_acesso'].notna())
)
_dff_r['Nunca Acessaram'] = _dff_r['ultimo_acesso'].isna()

_dff_r['Total'] = 1
DF_RISCO_GLOBAL = _dff_r.groupby('grupos_do_aluno')[['Em Risco', 'Nunca Acessaram', 'Total']].sum().reset_index()

del _dff_r, _last_access, _criacao, _resposta, _leitura, _df_30_dias, _acessos_30, _media_notas, _atrasadas



# ==============================================================================
# SEÇÃO 2: COMPONENTES DE INTERFACE ESTÁTICOS (LAYOUT BASE)
# ==============================================================================
layout = html.Div([
    dcc.Location(id='redirect-aluno-url', refresh=True),
    html.H1("Visual Learning Analytics", className='page-title'),
    
    # Filtros
    html.Div(className='filter-container', children=[
        html.Div(className='filter-box-1', children=[
            html.Label("Selecione a Turma:", className='filter-label', htmlFor='dropdown-selection'),
            dcc.Dropdown(
                options=[{'label': 'Todas as Turmas', 'value': 'Todas'}] + [{'label': str(t), 'value': str(t)} for t in df_logstore.grupos_do_aluno.dropna().unique()],
                value=str(df_logstore.grupos_do_aluno.dropna().unique()[0]) if len(df_logstore.grupos_do_aluno.dropna().unique()) > 0 else 'Todas', 
                id='dropdown-selection',
                placeholder="Selecione uma turma..."
            )
        ])
    ]),
    
    html.Div(className='dashboard-grid', children=[

        # Visão Geral da Turma
        html.Div(className='section-card', children=[
            html.H3("Visão Geral", className='section-title'),
            html.Div(id='session-card', className='stats-grid')
        ]),

        # Alunos em Risco
        html.Div(className='section-card', children=[
            html.H3("Alunos em Risco", className='section-title', style={'marginBottom': '5px'}),
            html.P("Critérios de risco: média < 6.0, mais de 1 atividade atrasada, nenhuma interação no fórum e inativo nos últimos 30 dias.", style={'fontSize': '0.85em', 'color': '#6c757d', 'marginBottom': '15px'}),
            
            html.Div(className='graphs-grid-2col', style={'marginBottom': '30px'}, children=[
                html.Div(className='graph-container', children=[
                    dcc.Graph(id='graph-risco-pizza'),
                    html.P("💡 Dica: Clique nas fatias do gráfico acima para filtrar a lista por status, e clique nos cartões abaixo para acessar os detalhes completos de cada aluno.", style={'textAlign': 'center', 'fontSize': '0.85em', 'color': '#666', 'marginTop': '10px', 'padding': '0 20px'})
                ]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-risco-turmas')])
            ]),
            
            html.Div(style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}, children=[
                html.Span(id='risk-students-count', className='badge')
            ]),
            
            html.Div(id='students-cards-container', className='students-cards-grid'),
            html.Div(className='pagination-container', style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginTop': '20px', 'gap': '10px'}, children=[
                html.Button("Anterior", id="btn-prev", n_clicks=0, className="btn-pagination", style={'padding': '5px 15px', 'cursor': 'pointer', 'borderRadius': '5px', 'border': '1px solid #ccc', 'background': '#f8f9fa'}),
                html.Span(id="pagination-info", style={'fontWeight': 'bold'}),
                html.Button("Próxima", id="btn-next", n_clicks=0, className="btn-pagination", style={'padding': '5px 15px', 'cursor': 'pointer', 'borderRadius': '5px', 'border': '1px solid #ccc', 'background': '#f8f9fa'})
            ])
        ]),
        
        dcc.Store(id='risk-students-store'),
        dcc.Store(id='current-page', data=1),

        # Indicadores Comportamentais
        html.Div(className='section-card', children=[
            html.H3("Indicadores Comportamentais", className='section-title'),
            html.Div(className='graphs-grid-2col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-sessoes-turmas')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-views-turmas')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-dias-turmas')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-tempo-turmas')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-duracao-turmas')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-content')])
            ]),
            html.Div(className='graphs-grid-1col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-forum-turmas')])
            ]),
            html.Div(className='graphs-grid-2col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-heatmap-turmas')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-horarios-turmas')])
            ]),
            html.Div(className='graphs-grid-1col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-materiais-turma')])
            ])
        ]),

        # Indicadores Cognitivos
        html.Div(className='section-card', children=[
            html.H3("Indicadores Cognitivos", className='section-title'),
            html.Div(className='graphs-grid-1col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-media-turmas')]),
                html.Div(className='graph-container', children=[
                    dcc.Graph(id='graph-scatter-tempo-notas'),
                    html.P("💡 Dica: No modo de Turma Específica, clique em qualquer ponto deste gráfico para acessar os detalhes daquele aluno.", style={'textAlign': 'center', 'fontSize': '0.85em', 'color': '#666', 'marginTop': '5px'})
                ])
            ]),
            html.Div(className='graphs-grid-2col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-taxa-atividades')]),
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-notas-atividade')])
            ]),
            html.Div(className='graphs-grid-1col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(id='graph-quiz-tentativas')])
            ])
        ])
    ])
], className='page-container')


# ==============================================================================
# SEÇÃO 3: CALLBACKS E LÓGICA DE INTERATIVIDADE
# ==============================================================================
@callback(
    Output('session-card', 'children'),
    Input('dropdown-selection', 'value')
)
def update_card(value):
    if value == 'Todas':
        dff = df_logstore.copy()
        total_alunos = len(df_students)
    else:
        dff = df_logstore[df_logstore.grupos_do_aluno == value].copy()
        total_alunos = len(df_students[df_students['grupos_do_aluno'] == value])
    
    # Lógica de sessionization
    dff = dff.sort_values(by=['userid', 'timecreated'])
    dff['time_diff'] = dff.groupby('userid')['timecreated'].diff()
    dff['is_new_session'] = (dff['time_diff'] > 3600) | dff['time_diff'].isna()
    
    total_sessoes = dff['is_new_session'].sum()
    
    nome_turma = value if value != 'Todas' else 'Todas as Turmas'
    
    if value == 'Todas':
        subtitle_acessos = html.P("Total das turmas", className='stat-subtitle')
        subtitle_alunos = html.P("Total em todas as turmas", className='stat-subtitle')
    else:
        subtitle_acessos = html.Div([
            html.P("Total da turma", className='stat-subtitle', style={'margin': '0 0 5px 0'}),
            html.P(f"Média das turmas: {int(MEDIA_ACESSOS_GLOBAL)}", className='stat-subtitle', style={'fontSize': '0.85em', 'color': '#6c757d', 'margin': '0'})
        ])
        subtitle_alunos = html.Div([
            html.P("Total da turma", className='stat-subtitle', style={'margin': '0 0 5px 0'}),
            html.P(f"Média das turmas: {int(MEDIA_ALUNOS_TURMA)}", className='stat-subtitle', style={'fontSize': '0.85em', 'color': '#6c757d', 'margin': '0'})
        ])
    
    # Lógica de notas
    if value == 'Todas':
        media_notas_turma = df_notas['nota_normalizada'].mean()
        media_notas_global = df_notas['nota_normalizada'].mean()
        subtitle_notas = html.P("Média de todas as turmas", className='stat-subtitle')
    else:
        alunos_ids = df_students[df_students['grupos_do_aluno'] == value]['userid'].tolist()
        notas_turma = df_notas[df_notas['userid'].isin(alunos_ids)]
        media_notas_turma = notas_turma['nota_normalizada'].mean() if not notas_turma.empty else 0.0
        media_notas_global = df_notas['nota_normalizada'].mean()
        subtitle_notas = html.Div([
            html.P("Média da turma", className='stat-subtitle', style={'margin': '0 0 5px 0'}),
            html.P(f"Média global: {media_notas_global:.2f}", className='stat-subtitle', style={'fontSize': '0.85em', 'color': '#6c757d', 'margin': '0'})
        ])

    return [
        html.Div(className='stat-card', children=[
            html.H4("Turma Selecionada", className='stat-title'),
            html.Div("🎓", className='stat-icon', style={'fontSize': '2.5rem', 'textAlign': 'center', 'margin': '10px 0'}),
            html.H2(nome_turma, className='stat-value', style={'textAlign': 'center'}),
        ]),
        html.Div(className='stat-card', children=[
            html.H4("Total de Alunos", className='stat-title'),
            html.H2(f"{total_alunos}", className='stat-value'),
            subtitle_alunos
        ]),
        html.Div(className='stat-card', children=[
            html.H4("Acessos Únicos (Sessões)", className='stat-title'),
            html.H2(f"{int(total_sessoes)}", className='stat-value'),
            subtitle_acessos
        ]),
        html.Div(className='stat-card', children=[
            html.H4("Média de Notas", className='stat-title'),
            html.H2(f"{media_notas_turma:.2f}", className='stat-value'),
            subtitle_notas
        ])
    ]

@callback(
    Output('graph-content', 'figure'),
    Output('graph-sessoes-turmas', 'figure'),
    Output('graph-views-turmas', 'figure'),
    Output('graph-dias-turmas', 'figure'),
    Output('graph-tempo-turmas', 'figure'),
    Output('graph-duracao-turmas', 'figure'),
    Output('graph-forum-turmas', 'figure'),
    Output('graph-heatmap-turmas', 'figure'),
    Output('graph-horarios-turmas', 'figure'),
    Output('graph-materiais-turma', 'figure'),
    Output('graph-media-turmas', 'figure'),
    Output('graph-scatter-tempo-notas', 'figure'),
    Output('graph-taxa-atividades', 'figure'),
    Output('graph-notas-atividade', 'figure'),
    Output('graph-quiz-tentativas', 'figure'),
    Output('graph-risco-pizza', 'figure'),
    Output('graph-risco-turmas', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    if value == 'Todas':
        dff = df_logstore.copy()
        alunos_ids = df_students['userid']
    else:
        dff = df_logstore[df_logstore.grupos_do_aluno==value].copy()
        alunos_ids = df_students[df_students['grupos_do_aluno']==value]['userid']
        
    # Lógica de sessionization e métricas
    dff['timecreated_dt'] = pd.to_datetime(dff['timecreated_dt'], errors='coerce')
    dff = dff.sort_values(by=['userid', 'timecreated_dt'])
    
    dff['time_diff'] = dff.groupby('userid')['timecreated_dt'].diff().dt.total_seconds()
    dff['is_new_session'] = (dff['time_diff'] > 3600) | dff['time_diff'].isna()
    
    # Filtrar apenas o início de cada sessão para o gráfico
    df_sessoes = dff[dff['is_new_session']]
    
    # Contabilizar sessões por dia da semana
    df_hits = df_sessoes.groupby('dia_da_semana').size().reset_index(name='Sessões')

    semana_map = {
        'Domingo': 1, 'Segunda': 2, 'Terça': 3, 'Quarta': 4,
        'Quinta': 5, 'Sexta': 6, 'Sábado': 7
    }
    ordem_semana = list(semana_map.keys())
    
    fig = px.bar(df_hits, x='dia_da_semana', y='Sessões',
                  title='Número de sessões durante a semana',
                  labels={'dia_da_semana': 'Dia da semana'},
                  category_orders={'dia_da_semana': ordem_semana})
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # -------------------------------------------------------------
    # Gráficos comparativos por turma
    # -------------------------------------------------------------
    df_chart = DF_STATS_GLOBAL.copy()
    
    # Garantir ordem alfabética
    df_chart['turma_str'] = df_chart['turma'].astype(str)
    df_chart = df_chart.sort_values('turma_str')
    ordem_turmas = df_chart['turma'].tolist()
    
    if value == 'Todas':
        df_chart['color'] = '#636efa'
    else:
        df_chart['color'] = df_chart['turma'].apply(lambda x: '#ef553b' if str(x) == str(value) else '#636efa')

    df_chart['tempo_h'] = df_chart['tempo'] / 3600.0
    df_chart['duracao_m'] = df_chart['duracao'] / 60.0
    df_chart['forum_tot'] = df_chart['posts'] + df_chart['resp'] + df_chart['leit']

    def build_bar(y_col, title, y_label):
        fig_b = px.bar(
            df_chart, x='turma', y=y_col, title=title,
            labels={'turma': 'Turma', y_col: y_label},
            color='color', color_discrete_map='identity',
            category_orders={'turma': ordem_turmas}
        )
        fig_b.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20), xaxis={'type': 'category'}
        )
        return fig_b

    fig_turmas = build_bar('sessoes', 'Sessões por Turma', 'Total de Sessões')
    fig_views = build_bar('views', 'Visualizações por Turma', 'Visualizações')
    fig_dias = build_bar('dias', 'Dias Ativos por Turma', 'Dias Ativos')
    fig_tempo = build_bar('tempo_h', 'Tempo Total Gasto (Horas)', 'Tempo (Horas)')
    fig_duracao = build_bar('duracao_m', 'Duração Média das Sessões (Minutos)', 'Duração (Minutos)')
    
    # --- Gráfico Empilhado para o Fórum ---
    df_forum = df_chart[['turma', 'turma_str', 'posts', 'resp', 'leit']].copy()
    df_forum_melt = df_forum.melt(
        id_vars=['turma', 'turma_str'], 
        value_vars=['posts', 'resp', 'leit'], 
        var_name='Tipo', value_name='Quantidade'
    )
    
    tipo_labels = {'posts': 'Postagens', 'resp': 'Respostas', 'leit': 'Leituras'}
    df_forum_melt['Tipo_Label'] = df_forum_melt['Tipo'].map(tipo_labels)
    
    def get_color_category(row):
        is_selected = (str(row['turma']) == str(value)) and (value != 'Todas')
        suffix = " (Selecionada)" if is_selected else ""
        return row['Tipo_Label'] + suffix
        
    df_forum_melt['Categoria'] = df_forum_melt.apply(get_color_category, axis=1)
    
    color_map = {
        'Postagens': '#1f77b4', 'Respostas': '#636efa', 'Leituras': '#aec7e8',
        'Postagens (Selecionada)': '#d62728', 'Respostas (Selecionada)': '#ff7f0e', 'Leituras (Selecionada)': '#ffbb78'
    }

    fig_forum = px.bar(
        df_forum_melt, 
        x='turma', 
        y='Quantidade', 
        color='Categoria', 
        title='Interações no Fórum (Detalhado)',
        labels={'turma': 'Turma', 'Quantidade': 'Interações', 'Categoria': 'Tipo'},
        category_orders={'turma': ordem_turmas},
        color_discrete_map=color_map,
        barmode='stack'
    )
    fig_forum.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20), xaxis={'type': 'category'}
    )
    
    # -------------------------------------------------------------
    # Mapa de Calor e Horários da Turma (Baseado nas sessões do dff)
    # -------------------------------------------------------------
    df_sessoes_local = df_sessoes.copy()
    if not df_sessoes_local.empty:
        # Heatmap
        df_sessoes_local['data'] = df_sessoes_local['timecreated_dt'].dt.normalize()
        sessoes_dia = df_sessoes_local.groupby('data').size().reset_index(name='Sessões')
        
        min_date = sessoes_dia['data'].min()
        max_date = sessoes_dia['data'].max()
        if pd.isna(min_date):
            min_date, max_date = pd.to_datetime('today').normalize() - pd.Timedelta(days=90), pd.to_datetime('today').normalize()
            
        min_date = min_date - pd.Timedelta(days=(min_date.dayofweek + 1) % 7)
        max_date = max_date + pd.Timedelta(days=6 - ((max_date.dayofweek + 1) % 7))
            
        all_dates = pd.DataFrame({'data': pd.date_range(start=min_date, end=max_date).normalize()})
        heatmap_df = pd.merge(all_dates, sessoes_dia, on='data', how='left').fillna({'Sessões': 0})
        
        heatmap_df['weekday'] = (heatmap_df['data'].dt.dayofweek + 1) % 7
        heatmap_df['week'] = ((heatmap_df['data'] - heatmap_df['data'].min()).dt.days // 7)
        heatmap_df['hover_text'] = heatmap_df['data'].dt.strftime('%d/%m/%Y') + '<br>Sessões: ' + heatmap_df['Sessões'].astype(int).astype(str)
        
        pivot_sessoes = heatmap_df.pivot(index='weekday', columns='week', values='Sessões')
        pivot_hover = heatmap_df.pivot(index='weekday', columns='week', values='hover_text')
        
        fig_heatmap = px.imshow(pivot_sessoes, title='Evolução de Sessões (Mapa de Calor)', color_continuous_scale=[[0,'#ccc'],[0.01,'#cff1a2'],[1,'#074050']])
        fig_heatmap.update_traces(customdata=pivot_hover, hovertemplate='%{customdata}<extra></extra>', xgap=3, ygap=3)
        fig_heatmap.update_layout(
            yaxis=dict(tickmode='array', tickvals=[0, 1, 2, 3, 4, 5, 6], ticktext=['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'], showgrid=False, zeroline=False, title=None),
            xaxis=dict(showgrid=False, zeroline=False, title=None, showticklabels=False),
            plot_bgcolor='white', margin=dict(l=40, r=20, t=40, b=20), coloraxis_showscale=False
        )
        
        # Horários
        df_sessoes_local['hora'] = df_sessoes_local['timecreated_dt'].dt.hour
        horarios = df_sessoes_local.groupby('hora').size().reset_index(name='Sessões')
        fig_horarios = px.bar(
            horarios, x='hora', y='Sessões', 
            title='Horários Mais Utilizados (Sessões)',
            labels={'hora': 'Hora do Dia', 'Sessões': 'Quantidade de Sessões'},
            color_discrete_sequence=['#30a14e']
        )
        fig_horarios.update_layout(
            xaxis=dict(tickmode='linear', tick0=0, dtick=1, range=[-0.5, 23.5]),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20)
        )
    else:
        fig_heatmap = px.line(title='Sem dados de acesso')
        fig_horarios = px.bar(title='Sem dados de horários')
        
    # -------------------------------------------------------------
    # Materiais Complementares
    # -------------------------------------------------------------
    dff['time_spent_sec'] = dff.groupby('userid')['timecreated_dt'].diff(-1).dt.total_seconds().abs()
    dff.loc[dff['time_spent_sec'] > 3600, 'time_spent_sec'] = 60
    dff['time_spent_sec'] = dff['time_spent_sec'].fillna(60)

    materiais = dff[(dff['component'].isin(['mod_resource', 'mod_folder', 'mod_page', 'mod_url', 'mod_book', 'mod_label'])) & (dff['action'] == 'viewed')].copy()
    if not materiais.empty:
        materiais_tempo = materiais.groupby(['component', 'contextinstanceid'])['time_spent_sec'].sum().reset_index(name='Tempo_Segundos')
        materiais_tempo['Tempo_Horas'] = (materiais_tempo['Tempo_Segundos'] / 3600.0).round(2)
        materiais_tempo = pd.merge(materiais_tempo, df_mods, left_on='contextinstanceid', right_on='cmid', how='left')
        
        tipo_map = {'mod_resource': 'Arquivo', 'mod_folder': 'Pasta', 'mod_page': 'Página', 'mod_url': 'Link', 'mod_book': 'Livro', 'mod_label': 'Texto e Mídia'}
        materiais_tempo['Tipo'] = materiais_tempo['component'].map(tipo_map).fillna(materiais_tempo['component'])
        materiais_tempo['Nome'] = materiais_tempo['nome_atividade'].fillna(materiais_tempo['Tipo'] + " (ID: " + materiais_tempo['contextinstanceid'].astype(str) + ")")
        materiais_tempo['Nome_Curto'] = materiais_tempo['Nome'].apply(lambda x: x if len(str(x)) <= 35 else str(x)[:32] + '...')
        
        materiais_agrupados = materiais_tempo.groupby('Nome_Curto')['Tempo_Horas'].sum().reset_index()
        materiais_agrupados = materiais_agrupados.sort_values(by='Tempo_Horas', ascending=True)
        
        if len(materiais_agrupados) > 10:
            materiais_agrupados = materiais_agrupados.tail(10)
            
        fig_materiais = px.bar(
            materiais_agrupados, x='Tempo_Horas', y='Nome_Curto', orientation='h',
            title='Materiais Mais Acessados (Tempo em Horas - Top 10)',
            labels={'Tempo_Horas': 'Horas', 'Nome_Curto': ''},
            color_discrete_sequence=['#40c463']
        )
        fig_materiais.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20)
        )
    else:
        fig_materiais = px.bar(title='Sem dados de materiais')
        
    # -------------------------------------------------------------
    # Gráfico Comparativo: Média das Turmas (Indicadores Cognitivos)
    # -------------------------------------------------------------
    fig_media_notas = build_bar('media_notas', 'Média de Notas por Turma (Normalizada)', 'Média (0 a 10)')
    fig_media_notas.update_traces(hovertemplate='Turma: %{x}<br>Média: %{y:.2f}<extra></extra>')
    
    # -------------------------------------------------------------
    # Scatterplot: Tempo de Estudo vs Média de Notas
    # -------------------------------------------------------------
    if value == 'Todas':
        df_scatter_turmas = df_chart[['turma', 'tempo_h', 'media_notas']].copy()
        
        fig_scatter = px.scatter(
            df_scatter_turmas, x='tempo_h', y='media_notas', 
            hover_name='turma', hover_data={'tempo_h': ':.2f', 'media_notas': ':.2f'},
            title='Tempo de Estudo vs Média de Notas (Por Turma)',
            labels={'tempo_h': 'Tempo de Estudo da Turma (Horas)', 'media_notas': 'Média da Turma'}
        )
        
        fig_scatter.update_traces(marker=dict(color='#636efa', size=15, opacity=0.8, line=dict(width=1, color='rgba(0,0,0,0.2)')))
        fig_scatter.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_range=[-0.5, 10.5]
        )
    else:
        dff['session_id'] = dff.groupby('userid')['is_new_session'].cumsum()
        sess_dur = dff.groupby(['userid', 'session_id'])['timecreated_dt'].agg(lambda x: (x.max() - x.min()).total_seconds())
        tempo_aluno = sess_dur.groupby('userid').sum().reset_index(name='tempo_total_segundos')
        tempo_aluno['tempo_h'] = tempo_aluno['tempo_total_segundos'] / 3600.0

        notas_aluno = df_notas[df_notas['userid'].isin(alunos_ids)]
        if not notas_aluno.empty:
            media_notas_aluno = notas_aluno.groupby('userid')['nota_normalizada'].mean().reset_index(name='media_notas')
            df_scatter = pd.merge(tempo_aluno, media_notas_aluno, on='userid', how='inner')
            
            alunos_info = df_students[['userid', 'firstname', 'lastname', 'grupos_do_aluno']].copy()
            alunos_info['nome'] = alunos_info['firstname'].fillna('') + ' ' + alunos_info['lastname'].fillna('')
            df_scatter = pd.merge(df_scatter, alunos_info, on='userid', how='left')
            
            fig_scatter = px.scatter(
                df_scatter, x='tempo_h', y='media_notas', 
                hover_name='nome', hover_data={'tempo_h': ':.2f', 'media_notas': ':.2f', 'grupos_do_aluno': True},
                custom_data=['userid'],
                title='Tempo de Estudo vs Média de Notas (Alunos)',
                labels={'tempo_h': 'Tempo de Estudo (Horas)', 'media_notas': 'Média de Notas', 'grupos_do_aluno': 'Turma'}
            )
            
            fig_scatter.update_traces(marker=dict(color='#ef553b', size=10, opacity=0.7, line=dict(width=1, color='rgba(0,0,0,0.2)')))
            fig_scatter.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis_range=[-0.5, 10.5]
            )
        else:
            fig_scatter = px.scatter(title='Sem dados para comparar notas')
            
    # -------------------------------------------------------------
    # Gráfico Comparativo: Média de Notas por Atividade
    # -------------------------------------------------------------
    if value == 'Todas':
        notas_turma = df_notas.copy()
    else:
        notas_turma = df_notas[df_notas['userid'].isin(alunos_ids)]
        
    if not notas_turma.empty:
        media_atividades = notas_turma.groupby('nome_atividade')['nota_normalizada'].mean().reset_index(name='media')
        media_atividades = media_atividades.sort_values(by='nome_atividade', ascending=False)
        
        fig_notas_atividade = px.bar(
            media_atividades, x='media', y='nome_atividade', orientation='h',
            title='Média de Notas por Atividade (Normalizada)',
            labels={'media': 'Média:', 'nome_atividade': ''},
            color_discrete_sequence=['#ef553b' if value != 'Todas' else '#636efa']
        )
        fig_notas_atividade.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_range=[0, 10.5]
        )
        
        # Média de Taxa de Realização de Atividades (Pizza)
        total_atividades = notas_turma['nome_atividade'].nunique()
        media_realizadas = notas_turma.groupby('userid')['nome_atividade'].nunique().mean()
        media_pendentes = max(0, total_atividades - media_realizadas)
        
        if total_atividades > 0:
            df_pie_taxa = pd.DataFrame({
                'Status': ['Realizadas (Média)', 'Pendentes (Média)'], 
                'Quantidade': [media_realizadas, media_pendentes]
            })
            fig_taxa_atividades = px.pie(
                df_pie_taxa, values='Quantidade', names='Status', color='Status', 
                color_discrete_map={'Realizadas (Média)': '#198754', 'Pendentes (Média)': '#dee2e6'}, 
                hole=0.65, title='Taxa Média de Realização'
            )
            fig_taxa_atividades.update_traces(hovertemplate='%{label}<br>%{value:.1f} atividade(s) em média (%{percent})<extra></extra>', textinfo='none')
            fig_taxa_atividades.update_layout(
                margin=dict(l=20, r=20, t=40, b=20), showlegend=True, 
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                annotations=[dict(text=f'<b>{(media_realizadas/total_atividades)*100:.0f}%</b>', x=0.5, y=0.5, font_size=22, showarrow=False, font=dict(color='#333'))]
            )
        else:
            fig_taxa_atividades = px.pie(title="Sem atividades")
            fig_taxa_atividades.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            
    else:
        fig_notas_atividade = px.bar(title='Sem dados de notas por atividade')
        fig_notas_atividade.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
        fig_taxa_atividades = px.pie(title='Sem dados de atividades')
        fig_taxa_atividades.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
    # -------------------------------------------------------------
    # Gráfico: Esforço nos Questionários (Tentativas e Tempo)
    # -------------------------------------------------------------
    if value == 'Todas':
        quiz_turma = df_quiz.copy()
    else:
        quiz_turma = df_quiz[df_quiz['userid'].isin(alunos_ids)].copy()
        
    if not quiz_turma.empty:
        quiz_turma['data_inicio_dt'] = pd.to_datetime(quiz_turma['data_inicio'], errors='coerce')
        
        # Primeiro calculamos o total/máximo de cada aluno no questionário
        student_quiz = quiz_turma.groupby(['nome_questionario', 'userid']).agg(
            tentativas=('numero_tentativa', 'max'), 
            minutos_gastos=('minutos_gastos', 'sum'),
            primeiro_acesso=('data_inicio_dt', 'min')
        ).reset_index()
        
        # Depois calculamos a média da turma por questionário
        quiz_stats = student_quiz.groupby('nome_questionario').agg(
            media_tentativas=('tentativas', 'mean'), 
            media_minutos=('minutos_gastos', 'mean'),
            primeiro_acesso=('primeiro_acesso', 'min')
        ).reset_index()
        quiz_stats = quiz_stats.sort_values(by='primeiro_acesso')
        
        fig_quiz = make_subplots(specs=[[{"secondary_y": True}]])
        fig_quiz.add_trace(
            go.Bar(
                x=quiz_stats['nome_questionario'], y=quiz_stats['media_minutos'], 
                name='Tempo Médio Gasto (min)', marker_color='#ffc107', 
                hovertemplate='%{x}<br>Tempo Médio: %{y:.0f} min<extra></extra>'
            ), 
            secondary_y=False
        )
        fig_quiz.add_trace(
            go.Scatter(
                x=quiz_stats['nome_questionario'], y=quiz_stats['media_tentativas'], 
                name='Média de Tentativas', mode='lines+markers', 
                marker=dict(size=12, color='#0c63e4', symbol='circle'), 
                line=dict(width=2, color='#0c63e4'), 
                hovertemplate='Média de Tentativas: %{y:.1f}<extra></extra>'
            ), 
            secondary_y=True
        )
        fig_quiz.update_layout(
            title="Esforço Médio nos Questionários (Tentativas e Tempo Gasto)", 
            xaxis_title="Questionário", xaxis_tickangle=-45, 
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), 
            margin=dict(l=20, r=20, t=40, b=80), hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
        )
        fig_quiz.update_yaxes(title_text="Tempo Médio (minutos)", secondary_y=False, showgrid=False)
        fig_quiz.update_yaxes(title_text="Média de Tentativas", secondary_y=True, dtick=1, showgrid=False)
    else:
        fig_quiz = px.bar(title='Nenhum questionário respondido')
        fig_quiz.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
    # -------------------------------------------------------------
    # Gráfico de Pizza: Proporção de Alunos por Status
    # -------------------------------------------------------------
    if value == 'Todas':
        total_risco = DF_RISCO_GLOBAL['Em Risco'].sum()
        total_nunca = DF_RISCO_GLOBAL['Nunca Acessaram'].sum()
        total_geral = DF_RISCO_GLOBAL['Total'].sum()
    else:
        df_turma = DF_RISCO_GLOBAL[DF_RISCO_GLOBAL['grupos_do_aluno'] == value]
        total_risco = df_turma['Em Risco'].sum()
        total_nunca = df_turma['Nunca Acessaram'].sum()
        total_geral = df_turma['Total'].sum()
        
    total_regulares = total_geral - total_risco - total_nunca
    
    df_pizza = pd.DataFrame({
        'Status': ['Em Risco', 'Nunca Acessaram', 'Regulares'],
        'Quantidade': [total_risco, total_nunca, total_regulares]
    })
    
    fig_risco_pizza = px.pie(
        df_pizza, values='Quantidade', names='Status',
        title='Proporção de Alunos por Status',
        color='Status',
        color_discrete_map={
            'Em Risco': '#ffc107',
            'Nunca Acessaram': '#dc3545',
            'Regulares': '#40c463'
        },
        hole=0.4
    )
    fig_risco_pizza.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20)
    )

    # -------------------------------------------------------------
    # Gráfico Comparativo: Alunos em Risco por Turma
    # -------------------------------------------------------------
    df_risco_chart = DF_RISCO_GLOBAL.copy()
    df_risco_chart = df_risco_chart.melt(id_vars='grupos_do_aluno', value_vars=['Em Risco', 'Nunca Acessaram'], var_name='Status', value_name='Quantidade')
    
    if value == 'Todas':
        color_map = {
            'Em Risco': '#ffc107',
            'Nunca Acessaram': '#dc3545'
        }
        df_risco_chart['Cor_Grupo'] = df_risco_chart['Status']
    else:
        def get_color(row):
            if str(row['grupos_do_aluno']) == str(value):
                if row['Status'] == 'Em Risco': return 'Em Risco (Selecionada)'
                else: return 'Nunca Acessaram (Selecionada)'
            else:
                if row['Status'] == 'Em Risco': return 'Em Risco (Outras)'
                else: return 'Nunca Acessaram (Outras)'
        
        df_risco_chart['Cor_Grupo'] = df_risco_chart.apply(get_color, axis=1)
        color_map = {
            'Em Risco (Selecionada)': '#ffc107', 
            'Nunca Acessaram (Selecionada)': '#dc3545',
            'Em Risco (Outras)': 'rgba(255, 193, 7, 0.3)', 
            'Nunca Acessaram (Outras)': 'rgba(220, 53, 69, 0.3)'
        }
    
    fig_risco_turmas = px.bar(
        df_risco_chart, x='grupos_do_aluno', y='Quantidade', color='Cor_Grupo',
        title='Comparativo de Alunos em Risco por Turma',
        labels={'grupos_do_aluno': 'Turma', 'Quantidade': 'Alunos', 'Cor_Grupo': 'Status'},
        color_discrete_map=color_map,
        category_orders={'grupos_do_aluno': sorted(df_risco_chart['grupos_do_aluno'].unique())}
    )
    fig_risco_turmas.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        barmode='stack',
        showlegend=True
    )
    
    return fig, fig_turmas, fig_views, fig_dias, fig_tempo, fig_duracao, fig_forum, fig_heatmap, fig_horarios, fig_materiais, fig_media_notas, fig_scatter, fig_taxa_atividades, fig_notas_atividade, fig_quiz, fig_risco_pizza, fig_risco_turmas

@callback(
    Output('risk-students-store', 'data'),
    Output('risk-students-count', 'children'),
    Output('risk-students-count', 'style'),
    Input('dropdown-selection', 'value'),
    Input('graph-risco-pizza', 'clickData')
)
def update_table(value, clickData):
    risk_type = 'risco'
    if clickData and 'points' in clickData:
        label = clickData['points'][0].get('label')
        if label == 'Nunca Acessaram':
            risk_type = 'nunca_acessou'
        elif label == 'Regulares':
            risk_type = 'regulares'
            
    # Filtrar estudantes pelo grupo selecionado
    if value == 'Todas':
        dff = df_students.copy()
    else:
        dff = df_students[df_students['grupos_do_aluno'] == value]
    
    # 1. Último acesso
    last_access = df_logstore.groupby('userid')['timecreated_dt'].max().reset_index()
    last_access.rename(columns={'timecreated_dt': 'ultimo_acesso'}, inplace=True)
    dff = pd.merge(dff, last_access, on='userid', how='left')
    
    # 2. Criação de postagens em fóruns
    criacao = df_forums[df_forums['tipo_interacao'] == 'create'].groupby('userid').size().reset_index(name='qtd_criacao_forum')
    dff = pd.merge(dff, criacao, on='userid', how='left')
    
    # 3. Respostas em fóruns
    resposta = df_forums[df_forums['tipo_interacao'] == 'response'].groupby('userid').size().reset_index(name='qtd_resposta_forum')
    dff = pd.merge(dff, resposta, on='userid', how='left')
    
    # 4. Leitura de postagens em fóruns (component=mod_forum, action=viewed)
    leitura = df_logstore[(df_logstore['component'] == 'mod_forum') & (df_logstore['action'] == 'viewed')].groupby('userid').size().reset_index(name='qtd_leitura_forum')
    dff = pd.merge(dff, leitura, on='userid', how='left')
    
    # 5. Acessos nos 30 dias antes de 20/06/2026 (agrupados por sessões)
    data_limite = pd.to_datetime('2026-06-20')
    data_inicio = data_limite - pd.Timedelta(days=30)
    mask_30_dias = (df_logstore['timecreated_dt'] >= data_inicio) & (df_logstore['timecreated_dt'] <= data_limite)
    
    df_30_dias = df_logstore[mask_30_dias].copy()
    
    # Ordenar por userid e tempo para o cálculo de diferença
    df_30_dias = df_30_dias.sort_values(by=['userid', 'timecreated'])
    df_30_dias['time_diff'] = df_30_dias.groupby('userid')['timecreated'].diff()
    df_30_dias['is_new_session'] = (df_30_dias['time_diff'] > 3600) | df_30_dias['time_diff'].isna()
    
    # Contar as sessões por usuário
    acessos_30_dias = df_30_dias.groupby('userid')['is_new_session'].sum().reset_index(name='acessos_30_dias')
    dff = pd.merge(dff, acessos_30_dias, on='userid', how='left')
    
    # Preencher NaN com 0 para as contagens
    for col in ['qtd_criacao_forum', 'qtd_resposta_forum', 'qtd_leitura_forum', 'acessos_30_dias']:
        dff[col] = dff[col].fillna(0).astype(int)
        
    # 6. Média de Notas Normalizadas
    media_notas = df_notas.groupby('userid')['nota_normalizada'].mean().reset_index(name='media_notas')
    dff = pd.merge(dff, media_notas, on='userid', how='left')
    dff['media_notas'] = dff['media_notas'].fillna(0).round(2)
    
    # 7. Atividades Atrasadas
    atividades_atrasadas = df_atrasadas.groupby('userid').size().reset_index(name='qtd_atividades_atrasadas')
    dff = pd.merge(dff, atividades_atrasadas, on='userid', how='left')
    dff['qtd_atividades_atrasadas'] = dff['qtd_atividades_atrasadas'].fillna(0).astype(int)
    
    # 8. Atividades Realizadas
    atividades_realizadas = df_notas.groupby('userid').size().reset_index(name='qtd_atividades_realizadas')
    dff = pd.merge(dff, atividades_realizadas, on='userid', how='left')
    dff['qtd_atividades_realizadas'] = dff['qtd_atividades_realizadas'].fillna(0).astype(int)
    
    # Calcular contagens totais antes do filtro
    mask_risco = (
        (dff['qtd_criacao_forum'] == 0) & 
        (dff['qtd_resposta_forum'] == 0) & 
        (dff['qtd_leitura_forum'] == 0) & 
        (dff['acessos_30_dias'] == 0) & 
        (dff['media_notas'] < 6) & 
        (dff['qtd_atividades_atrasadas'] > 1) &
        (dff['ultimo_acesso'].notna())
    )
    mask_nunca_acessou = dff['ultimo_acesso'].isna()
    
    total_problemas = mask_risco.sum() + mask_nunca_acessou.sum()
    
    # Filtro de alunos baseado na seleção
    # Filtro de alunos baseado na seleção para os CARDS
    if risk_type == 'risco':
        dff_risk = dff[mask_risco]
        badge_style = {'backgroundColor': '#ffc107', 'color': 'black', 'padding': '6px 12px', 'borderRadius': '12px', 'fontSize': '0.9em', 'fontWeight': 'bold'}
    elif risk_type == 'nunca_acessou':
        dff_risk = dff[mask_nunca_acessou]
        badge_style = {'backgroundColor': '#dc3545', 'color': 'white', 'padding': '6px 12px', 'borderRadius': '12px', 'fontSize': '0.9em', 'fontWeight': 'bold'}
    else:
        # Regulares
        dff_risk = dff[~mask_risco & ~mask_nunca_acessou]
        badge_style = {'backgroundColor': '#40c463', 'color': 'white', 'padding': '6px 12px', 'borderRadius': '12px', 'fontSize': '0.9em', 'fontWeight': 'bold'}
        
    count_text = f"{len(dff_risk)} alunos encontrados (Filtro: {risk_type.replace('_', ' ').title()})"
    
    risk_data = dff_risk.to_dict('records')
    
    return risk_data, count_text, badge_style

@callback(
    Output('students-cards-container', 'children'),
    Output('pagination-info', 'children'),
    Output('current-page', 'data'),
    Input('risk-students-store', 'data'),
    Input('btn-prev', 'n_clicks'),
    Input('btn-next', 'n_clicks'),
    State('current-page', 'data')
)
def update_pagination(risk_data, btn_prev, btn_next, current_page):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    if not risk_data:
        return [], "0 / 0", 1

    items_per_page = 8
    total_items = len(risk_data)
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

    if triggered_id == 'risk-students-store':
        current_page = 1
    elif triggered_id == 'btn-prev' and current_page > 1:
        current_page -= 1
    elif triggered_id == 'btn-next' and current_page < total_pages:
        current_page += 1
    
    current_page = max(1, min(current_page, total_pages))
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_data = risk_data[start_idx:end_idx]

    cards = []
    for row in page_data:
        lname_initial = str(row['lastname'])[0] + "." if pd.notna(row['lastname']) and str(row['lastname']) != "" else ""
        nome_exibicao = f"{row['firstname']} {lname_initial}"
        
        ultimo_acesso_val = row.get('ultimo_acesso', '')
        if pd.notna(ultimo_acesso_val) and ultimo_acesso_val != '':
            ultimo_acesso_fmt = pd.to_datetime(ultimo_acesso_val).strftime('%d/%m/%Y %H:%M')
        else:
            ultimo_acesso_fmt = 'Nunca'
            
        valor_style = {'color': 'red'}
        
        card_content = html.Div(className='student-card', style={'padding': '12px'}, children=[
            html.Div(className='student-card-icon', children=[
                html.Div("👤", className='student-avatar', style={'fontSize': '3rem', 'margin': '0'})
            ]),
            html.Div(className='student-card-info', children=[
                html.H4(nome_exibicao, className='student-name', style={'margin': '0 0 8px 0', 'fontSize': '1.1rem'}),
                html.Div([
                    html.P([html.Strong("Últ. Acesso: "), html.Span(ultimo_acesso_fmt, style=valor_style)], style={'margin': '2px 0', 'fontSize': '0.85em'}),
                    html.P([html.Strong("Média Notas: "), html.Span(str(row.get('media_notas', '')), style=valor_style)], style={'margin': '2px 0', 'fontSize': '0.85em'}),
                    html.P([html.Strong("Fórum: "), html.Span(f"{int(row.get('qtd_criacao_forum', 0)) + int(row.get('qtd_resposta_forum', 0))} posts, {int(row.get('qtd_leitura_forum', 0))} lidos", style=valor_style)], style={'margin': '2px 0', 'fontSize': '0.85em'}),
                    html.P([html.Strong("Atividades: "), html.Span(f"{row.get('qtd_atividades_atrasadas', 0)} atrasadas, {row.get('qtd_atividades_realizadas', 0)} feitas", style=valor_style)], style={'margin': '2px 0', 'fontSize': '0.85em'})
                ])
            ])
        ])
        
        card = dcc.Link(
            href=f"/aluno/{row['userid']}",
            style={'textDecoration': 'none', 'color': 'inherit', 'display': 'block'},
            children=[card_content]
        )
        
        cards.append(card)
        
    return cards, f"{current_page} / {total_pages}", current_page

@callback(
    Output('redirect-aluno-url', 'href'),
    Input('graph-scatter-tempo-notas', 'clickData'),
    prevent_initial_call=True
)
def redirect_to_student(clickData):
    if clickData and 'points' in clickData:
        point = clickData['points'][0]
        # Quando 'Todas' está selecionado, customdata não existe.
        if 'customdata' in point and len(point['customdata']) > 0:
            userid = point['customdata'][0]
            if userid:
                return f"/aluno/{userid}"
    return dash.no_update
