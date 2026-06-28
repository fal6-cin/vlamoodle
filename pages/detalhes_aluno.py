# ==============================================================================
# SEÇÃO 1: IMPORTS E CONFIGURAÇÕES INICIAIS
# ==============================================================================
import dash
from dash import html, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Registrando a página com caminho base e template de rota
dash.register_page(__name__, path='/aluno', path_template='/aluno/<userid>')

# Carregar os dados (carregados no início para melhor performance)
df_students = pd.read_csv('datasets/students_anon.csv', sep=';')
df_notas = pd.read_csv('datasets/notas.csv', sep=';')
df_logstore = pd.read_csv('datasets/logstore_filtered.csv', sep=';')
df_mods = pd.read_csv('datasets/mods.csv', sep=';')
df_quiz = pd.read_csv('datasets/quizattemp.csv', sep=';')
df_forum = pd.read_csv('datasets/forum_interations.csv', sep=';')

# ==============================================================================
# SEÇÃO 2: FUNÇÕES UTILITÁRIAS E DE CÁLCULO
# ==============================================================================
def format_duration(seconds):
    """Converte segundos para uma string legível 'Xh Ym' ou 'Ym'."""
    if pd.isna(seconds) or seconds == 0: return "0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def calcular_metricas_turma(df_logs, tempo_inatividade_segundos=3600):
    """Calcula médias de engajamento da turma inteira iterando sobre os logstores."""
    if df_logs.empty:
        return 0, 0.0, 0.0, 0, 0
    
    df = df_logs.copy()
    df['timecreated_dt'] = pd.to_datetime(df['timecreated_dt'], errors='coerce')
    df = df.sort_values(by=['userid', 'timecreated_dt'])
    
    # Identificar quebras de sessão
    df['time_diff'] = df.groupby('userid')['timecreated_dt'].diff().dt.total_seconds()
    df['is_new_session'] = (df['time_diff'] > tempo_inatividade_segundos) | df['time_diff'].isna()
    df['session_id'] = df.groupby('userid')['is_new_session'].cumsum()
    
    # Calcular métricas baseadas na duração das sessões de cada usuário
    session_durations = df.groupby(['userid', 'session_id'])['timecreated_dt'].agg(lambda x: (x.max() - x.min()).total_seconds())
    
    media_tempo_total = session_durations.groupby('userid').sum().mean() if not session_durations.empty else 0.0
    media_duracao_media = session_durations.mean() if not session_durations.empty else 0.0
    
    media_sessoes = int(df.groupby('userid')['is_new_session'].sum().mean())
    media_views = int(df[df['action'] == 'viewed'].groupby('userid').size().mean())
    media_days = int(df.groupby('userid')['data'].nunique().mean())
    
    return media_sessoes, media_tempo_total, media_duracao_media, media_views, media_days


def calcular_metricas_aluno(df_logs, tempo_inatividade_segundos=3600):
    """Calcula o engajamento e cria coluna de tempo gasto para um aluno específico."""
    if df_logs.empty:
        return pd.DataFrame(), 0, 0.0, 0.0, 0, 0, "N/A", "Nunca acessou"
        
    df = df_logs.copy()
    df['timecreated_dt'] = pd.to_datetime(df['timecreated_dt'], errors='coerce')
    df = df.sort_values(by=['timecreated_dt'])
    
    primeiro_acesso = df['timecreated_dt'].min().strftime('%d/%m/%Y')
    ultimo_acesso = df['timecreated_dt'].max().strftime('%d/%m/%Y %H:%M')
    
    # Quebras de sessão
    df['time_diff'] = df['timecreated_dt'].diff().dt.total_seconds()
    df['is_new_session'] = (df['time_diff'] > tempo_inatividade_segundos) | df['time_diff'].isna()
    df['session_id'] = df['is_new_session'].cumsum()
    
    # Tempo gasto por ação/clique (diferença para o timestamp subsequente)
    df['time_spent_sec'] = (df['timecreated_dt'].shift(-1) - df['timecreated_dt']).dt.total_seconds()
    df.loc[df['time_spent_sec'] > tempo_inatividade_segundos, 'time_spent_sec'] = 60
    df['time_spent_sec'] = df['time_spent_sec'].fillna(60)
    
    # Métricas globais do aluno
    session_durations = df.groupby('session_id')['timecreated_dt'].agg(lambda x: (x.max() - x.min()).total_seconds())
    student_tempo_total = session_durations.sum() if not session_durations.empty else 0.0
    student_duracao_media = session_durations.mean() if not session_durations.empty else 0.0
    
    student_sessoes = int(df['is_new_session'].sum())
    student_views = len(df[df['action'] == 'viewed'])
    student_days = df['data'].nunique()
    
    return df, student_sessoes, student_tempo_total, student_duracao_media, student_views, student_days, primeiro_acesso, ultimo_acesso

# ==============================================================================
# SEÇÃO 3: COMPONENTES DE INTERFACE ESTÁTICOS (LAYOUT BASE)
# ==============================================================================
def layout(userid=None, **kwargs):
    turma_inicial = None
    aluno_inicial = None
    
    # Inicializar estado a partir da URL
    if userid:
        try:
            user_id_int = int(userid)
            student_info = df_students[df_students['userid'] == user_id_int]
            if not student_info.empty:
                aluno_inicial = user_id_int
                turma_inicial = student_info.iloc[0]['grupos_do_aluno']
        except ValueError:
            pass

    # Opções do dropdown de turma
    turmas_unicas = df_students['grupos_do_aluno'].dropna().unique()
    turmas_options = [{'label': str(t), 'value': str(t)} for t in turmas_unicas]
    
    # Opções iniciais de alunos
    alunos_options = []
    if turma_inicial:
        dff = df_students[df_students['grupos_do_aluno'] == turma_inicial].sort_values('firstname')
        for _, row in dff.iterrows():
            nome = f"{row.get('firstname', '')} {row.get('lastname', '')}".strip()
            alunos_options.append({'label': f"{nome}", 'value': row['userid']})
    
    return html.Div([
        html.H1("Painel do Aluno", className='page-title'),
        html.P("Selecione a turma e o aluno para visualizar os detalhes", className='page-description'),
        
        # Filtros (Dropdowns)
        html.Div(className='filter-container', children=[
            html.Div(className='filter-box-1', children=[
                html.Label("Turma:", className='filter-label'),
                dcc.Dropdown(
                    id='detalhes-turma-dropdown',
                    options=turmas_options,
                    value=turma_inicial,
                    placeholder="Selecione uma turma..."
                )
            ]),
            html.Div(className='filter-box-2', children=[
                html.Label("Aluno:", className='filter-label'),
                dcc.Dropdown(
                    id='detalhes-aluno-dropdown',
                    options=alunos_options,
                    value=aluno_inicial,
                    placeholder="Selecione um aluno..."
                )
            ])
        ]),
        
        # Container do Dashboard
        html.Div(id='detalhes-aluno-container'),
        
        # Botão Voltar
        html.Div(className='back-button-container', children=[
            dcc.Link("← Voltar para Visão Geral", href="/", className='back-button')
        ])
    ], className='page-container')

# ==============================================================================
# SEÇÃO 4: CALLBACKS E LÓGICA DE INTERATIVIDADE
# ==============================================================================

@callback(
    Output('detalhes-aluno-dropdown', 'options'),
    Input('detalhes-turma-dropdown', 'value')
)
def atualizar_dropdown_alunos(turma):
    """Atualiza o dropdown de estudantes quando uma turma é selecionada."""
    if not turma: return []
    dff = df_students[df_students['grupos_do_aluno'] == turma].sort_values('firstname')
    return [{'label': f"{row.get('firstname', '')} {row.get('lastname', '')}".strip(), 'value': row['userid']} for _, row in dff.iterrows()]


@callback(
    Output('detalhes-aluno-container', 'children'),
    Input('detalhes-aluno-dropdown', 'value')
)
def atualizar_conteudo_aluno(user_id_int):
    """Função principal que busca dados e desenha todos os painéis e gráficos do aluno selecionado."""
    
    # --------------------------------------------------------------------------
    # Bloco A: Validações e Resgate de Dados Cadastrais
    # --------------------------------------------------------------------------
    if not user_id_int:
        return html.Div([html.P("Nenhum aluno selecionado. Por favor, escolha uma turma e um aluno acima.", className='no-student-msg')], className='no-student-container')
        
    student_info = df_students[df_students['userid'] == user_id_int]
    if student_info.empty:
        return html.Div([html.H3("Erro: Dados do aluno não encontrados.", className='error-msg')])
        
    aluno = student_info.iloc[0]
    nome_completo = f"{aluno.get('firstname', '')} {aluno.get('lastname', '')}".strip()
    email = aluno.get('email', 'Email não disponível')
    grupo = aluno.get('grupos_do_aluno', 'Sem grupo')

    # --------------------------------------------------------------------------
    # Bloco B: Processamento de Engajamento e Acessos Globais
    # --------------------------------------------------------------------------
    user_logs_raw = df_logstore[df_logstore['userid'] == user_id_int]
    class_logs_raw = df_logstore[df_logstore['grupos_do_aluno'] == grupo]
    
    m_sessoes, m_tempo_total, m_duracao_media, m_views, m_days = calcular_metricas_turma(class_logs_raw)
    
    (user_logs, s_sessoes, s_tempo_total, s_duracao_media, 
     s_views, s_days, primeiro_acesso, ultimo_acesso) = calcular_metricas_aluno(user_logs_raw)
     
    # Interações no Fórum
    try:
        user_forum = df_forum[df_forum['userid'] == user_id_int] if not df_forum.empty else pd.DataFrame()
        class_forum = df_forum[df_forum['userid'].isin(df_students[df_students['grupos_do_aluno'] == grupo]['userid'])] if not df_forum.empty else pd.DataFrame()
        
        s_postagens = len(user_forum[user_forum['tipo_interacao'].astype(str).str.lower().isin(['postagem', 'post'])]) if not user_forum.empty and 'tipo_interacao' in user_forum.columns else 0
        s_respostas = len(user_forum[user_forum['tipo_interacao'].astype(str).str.lower().isin(['resposta', 'reply'])]) if not user_forum.empty and 'tipo_interacao' in user_forum.columns else 0
        
        # Leitura no fórum a partir do df_logstore
        s_leituras = len(user_logs_raw[(user_logs_raw['component'] == 'mod_forum') & (user_logs_raw['action'] == 'viewed')])
        
        m_postagens = int(class_forum[class_forum['tipo_interacao'].astype(str).str.lower().isin(['postagem', 'post'])].groupby('userid').size().mean()) if not class_forum.empty and 'tipo_interacao' in class_forum.columns and not class_forum[class_forum['tipo_interacao'].astype(str).str.lower().isin(['postagem', 'post'])].empty else 0
        m_respostas = int(class_forum[class_forum['tipo_interacao'].astype(str).str.lower().isin(['resposta', 'reply'])].groupby('userid').size().mean()) if not class_forum.empty and 'tipo_interacao' in class_forum.columns and not class_forum[class_forum['tipo_interacao'].astype(str).str.lower().isin(['resposta', 'reply'])].empty else 0
        
        m_leituras_df = class_logs_raw[(class_logs_raw['component'] == 'mod_forum') & (class_logs_raw['action'] == 'viewed')]
        m_leituras = int(m_leituras_df.groupby('userid').size().mean()) if not m_leituras_df.empty else 0
    except Exception:
        s_postagens = s_respostas = s_leituras = 0
        m_postagens = m_respostas = m_leituras = 0

    # --------------------------------------------------------------------------
    # Bloco C: Processamento de Desempenho e Questionários
    # --------------------------------------------------------------------------
    alunos_turma = df_students[df_students['grupos_do_aluno'] == grupo]['userid']
    class_notas = df_notas[df_notas['userid'].isin(alunos_turma)].dropna(subset=['nota_normalizada'])
    media_turma_notas = class_notas['nota_normalizada'].mean() if not class_notas.empty else 0
    
    user_notas = df_notas[df_notas['userid'] == user_id_int].copy()
    media_aluno_notas = 0
    atividades_aluno = []
    
    if not user_notas.empty:
        if 'data_avaliacao' in user_notas.columns:
            user_notas['data_avaliacao'] = pd.to_datetime(user_notas['data_avaliacao'], errors='coerce')
            user_notas = user_notas.sort_values(by='data_avaliacao')
            user_notas['data_formatada'] = user_notas['data_avaliacao'].dt.strftime('%d/%m/%Y').fillna('Sem data')
        else:
            user_notas['data_formatada'] = 'Sem data'
            
        user_notas = user_notas.dropna(subset=['nota_normalizada'])
        media_aluno_notas = user_notas['nota_normalizada'].mean() if not user_notas.empty else 0
        atividades_aluno = user_notas['nome_atividade'].drop_duplicates().tolist()

    # Taxa de Realização (Cognitivos)
    total_atividades_turma = class_notas['nome_atividade'].nunique() if not class_notas.empty else 0
    atividades_realizadas_aluno = user_notas['nome_atividade'].nunique() if not user_notas.empty else 0
    atividades_pendentes = max(0, total_atividades_turma - atividades_realizadas_aluno)
    media_atividades_turma = class_notas.groupby('userid')['nome_atividade'].nunique().mean() if not class_notas.empty else 0

    # --------------------------------------------------------------------------
    # Bloco D: Construção de Gráficos (Plotly)
    # --------------------------------------------------------------------------
    
    # D.1 - Mapa de Calor de Sessões (Evolução ao Longo da Semana)
    if not user_logs.empty:
        sessoes_dia = user_logs[user_logs['is_new_session']].groupby('data').size().reset_index(name='Sessões')
        sessoes_dia['data'] = pd.to_datetime(sessoes_dia['data'], format='%Y-%m-%d', errors='coerce').dt.normalize()
        
        # Garantir limite de calendário para o aluno
        class_dates = pd.to_datetime(class_logs_raw['timecreated_dt'], errors='coerce')
        min_date = class_dates.min().normalize() if not class_dates.dropna().empty else sessoes_dia['data'].min()
        max_date = class_dates.max().normalize() if not class_dates.dropna().empty else sessoes_dia['data'].max()
        if pd.isna(min_date):
            min_date, max_date = pd.to_datetime('today').normalize() - pd.Timedelta(days=90), pd.to_datetime('today').normalize()
            
        # Arredondar para domingo e sábado subsequente, fechando as semanas
        min_date = min_date - pd.Timedelta(days=(min_date.dayofweek + 1) % 7)
        max_date = max_date + pd.Timedelta(days=6 - ((max_date.dayofweek + 1) % 7))
            
        all_dates = pd.DataFrame({'data': pd.date_range(start=min_date, end=max_date).normalize()})
        heatmap_df = pd.merge(all_dates, sessoes_dia, on='data', how='left').fillna({'Sessões': 0})
        
        heatmap_df['weekday'] = (heatmap_df['data'].dt.dayofweek + 1) % 7
        heatmap_df['week'] = ((heatmap_df['data'] - heatmap_df['data'].min()).dt.days // 7)
        heatmap_df['hover_text'] = heatmap_df['data'].dt.strftime('%d/%m/%Y') + '<br>Sessões: ' + heatmap_df['Sessões'].astype(int).astype(str)
        
        pivot_sessoes = heatmap_df.pivot(index='weekday', columns='week', values='Sessões')
        pivot_hover = heatmap_df.pivot(index='weekday', columns='week', values='hover_text')
        
        fig_acessos = px.imshow(pivot_sessoes, title='Evolução de Sessões (Mapa de Calor)', color_continuous_scale=[[0,'#ccc'],[0.01,'#cff1a2'],[1,'#074050']])
        fig_acessos.update_traces(customdata=pivot_hover, hovertemplate='%{customdata}<extra></extra>', xgap=3, ygap=3)
        fig_acessos.update_layout(
            yaxis=dict(tickmode='array', tickvals=[0, 1, 2, 3, 4, 5, 6], ticktext=['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'], showgrid=False, zeroline=False, title=None),
            xaxis=dict(showgrid=False, zeroline=False, title=None, showticklabels=False),
            plot_bgcolor='white', margin=dict(l=40, r=20, t=40, b=20), coloraxis_showscale=False
        )
    else:
        fig_acessos = px.line(title='Sem dados de acesso')

    # D.1.b - Horários das Sessões
    df_sessoes_start = user_logs[user_logs['is_new_session']].copy()
    if not df_sessoes_start.empty:
        df_sessoes_start['hora'] = pd.to_datetime(df_sessoes_start['timecreated_dt'], errors='coerce').dt.hour
        horarios = df_sessoes_start.groupby('hora').size().reset_index(name='Sessões')
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
        fig_horarios = px.bar(title='Sem dados de horários')

    # D.2 - Tempo Gasto por Material Complementar
    materiais = user_logs[(user_logs['component'].isin(['mod_resource', 'mod_folder', 'mod_page', 'mod_url', 'mod_book', 'mod_label'])) & (user_logs['action'] == 'viewed')].copy() if not user_logs.empty else pd.DataFrame()
    if not materiais.empty:
        materiais_tempo = materiais.groupby(['component', 'contextinstanceid'])['time_spent_sec'].sum().reset_index(name='Tempo_Segundos')
        materiais_tempo['Tempo_Minutos'] = (materiais_tempo['Tempo_Segundos'] / 60).round(1)
        materiais_tempo = pd.merge(materiais_tempo, df_mods, left_on='contextinstanceid', right_on='cmid', how='left')
        
        tipo_map = {'mod_resource': 'Arquivo', 'mod_folder': 'Pasta', 'mod_page': 'Página', 'mod_url': 'Link', 'mod_book': 'Livro', 'mod_label': 'Texto e Mídia'}
        materiais_tempo['Tipo'] = materiais_tempo['component'].map(tipo_map).fillna(materiais_tempo['component'])
        materiais_tempo['Nome'] = materiais_tempo['nome_atividade'].fillna(materiais_tempo['Tipo'] + " (ID: " + materiais_tempo['contextinstanceid'].astype(str) + ")")
        materiais_tempo['Nome_Curto'] = materiais_tempo['Nome'].apply(lambda x: x if len(str(x)) <= 35 else str(x)[:32] + '...')
        materiais_tempo = materiais_tempo.sort_values(by='Tempo_Minutos', ascending=False).head(10)
        
        fig_materiais = px.bar(
            materiais_tempo, x='Tempo_Minutos', y='Nome_Curto', orientation='h', title='Tempo Gasto por Material (Top 10)',
            text='Tempo_Minutos', color='Tempo_Minutos', color_continuous_scale='Emrld',
            hover_data={'Nome': True, 'Nome_Curto': False, 'Tempo_Minutos': True, 'Tempo_Segundos': False}
        )
        fig_materiais.update_traces(texttemplate='%{text} min', textposition='outside')
        fig_materiais.update_layout(xaxis_title="Minutos", yaxis={'categoryorder':'total ascending'}, yaxis_title=None, margin=dict(l=20, r=60, t=40, b=20))
    else:
        fig_materiais = px.bar(title='Nenhum material complementar acessado')

    # D.3 - Notas de Avaliação (Scatter) versus Média da Turma
    if not user_notas.empty and atividades_aluno:
        class_notas_filtradas = class_notas[class_notas['nome_atividade'].isin(atividades_aluno)]
        turma_stats = class_notas_filtradas.groupby('nome_atividade')['nota_normalizada'].agg(['mean', 'min', 'max']).reset_index()
        turma_stats['nome_atividade'] = pd.Categorical(turma_stats['nome_atividade'], categories=atividades_aluno, ordered=True)
        turma_stats = turma_stats.sort_values('nome_atividade')
        turma_stats['error_plus'] = turma_stats['max'] - turma_stats['mean']
        turma_stats['error_minus'] = turma_stats['mean'] - turma_stats['min']
        
        fig_notas = px.scatter(
            turma_stats, x='nome_atividade', y='mean', error_y='error_plus', error_y_minus='error_minus',
            title='Desempenho por Atividade (Média e Amplitude da Turma vs Aluno)', color='mean',
            color_continuous_scale='RdYlGn', range_color=[0, 10], category_orders={'nome_atividade': atividades_aluno}
        )
        fig_notas.update_traces(name='Média da Turma', showlegend=True, marker=dict(size=12, line=dict(width=1, color='rgba(0,0,0,0.3)')), hovertemplate='Média: %{y:.1f}<extra></extra>')
        fig_notas.add_scatter(x=turma_stats['nome_atividade'], y=turma_stats['max'], mode='markers', name='Maior Nota', marker=dict(size=15, color='rgba(0,0,0,0)'), showlegend=False, hovertemplate='Maior Nota: %{y:.1f}<extra></extra>')
        fig_notas.add_scatter(x=turma_stats['nome_atividade'], y=turma_stats['min'], mode='markers', name='Menor Nota', marker=dict(size=15, color='rgba(0,0,0,0)'), showlegend=False, hovertemplate='Menor Nota: %{y:.1f}<extra></extra>')
        fig_notas.add_scatter(
            x=user_notas['nome_atividade'], y=user_notas['nota_normalizada'], mode='markers+text', name='Nota do Aluno', customdata=user_notas['data_formatada'],
            marker=dict(color=user_notas['nota_normalizada'], colorscale='RdYlGn', cmin=0, cmax=10, size=14, symbol='diamond', line=dict(width=1, color='rgba(0,0,0,0.5)'), showscale=False),
            text=user_notas['nota_normalizada'].round(1), textposition='top center', textfont=dict(size=13, color='black'), hovertemplate='%{x}<br>Data: %{customdata}<br>Nota: %{y:.1f}<extra></extra>'
        )
        fig_notas.update_layout(xaxis_title="Atividade", yaxis_title="Nota Normalizada", xaxis_tickangle=-45, margin=dict(l=20, r=20, t=40, b=80), yaxis_range=[-1, 11.5], legend_title_text=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), coloraxis_showscale=False)
    else:
        fig_notas = px.bar(title='Nenhuma nota registrada')

    # D.4 - Taxa de Realização de Atividades (Gráfico de Pizza)
    if total_atividades_turma > 0:
        df_pie = pd.DataFrame({'Status': ['Realizadas', 'Pendentes'], 'Quantidade': [atividades_realizadas_aluno, atividades_pendentes]})
        fig_pie = px.pie(df_pie, values='Quantidade', names='Status', color='Status', color_discrete_map={'Realizadas': '#198754', 'Pendentes': '#dee2e6'}, hole=0.65)
        fig_pie.update_traces(hovertemplate='%{label}<br>%{value} atividade(s) (%{percent})<extra></extra>', textinfo='none')
        fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', annotations=[dict(text=f'<b>{(atividades_realizadas_aluno/total_atividades_turma)*100:.0f}%</b>', x=0.5, y=0.5, font_size=22, showarrow=False, font=dict(color='#333'))])
    else:
        fig_pie = px.pie(title="Sem atividades")
        fig_pie.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    # D.5 - Esforço nos Questionários (Tentativas e Tempo)
    user_quiz = df_quiz[df_quiz['userid'] == user_id_int].copy()
    if not user_quiz.empty:
        user_quiz['data_inicio_dt'] = pd.to_datetime(user_quiz['data_inicio'], errors='coerce')
        quiz_stats = user_quiz.groupby('nome_questionario').agg(tentativas=('numero_tentativa', 'max'), minutos_gastos=('minutos_gastos', 'sum'), primeiro_acesso=('data_inicio_dt', 'min')).reset_index()
        quiz_stats = quiz_stats.sort_values(by='primeiro_acesso')
        
        fig_quiz = make_subplots(specs=[[{"secondary_y": True}]])
        fig_quiz.add_trace(go.Bar(x=quiz_stats['nome_questionario'], y=quiz_stats['minutos_gastos'], name='Tempo Gasto (min)', marker_color='#ffc107', hovertemplate='%{x}<br>Tempo Gasto: %{y:.0f} min<extra></extra>'), secondary_y=False)
        fig_quiz.add_trace(go.Scatter(x=quiz_stats['nome_questionario'], y=quiz_stats['tentativas'], name='Nº de Tentativas', mode='lines+markers', marker=dict(size=12, color='#0c63e4', symbol='circle'), line=dict(width=2, color='#0c63e4'), hovertemplate='Tentativas: %{y}<extra></extra>'), secondary_y=True)
        fig_quiz.update_layout(title="Desempenho nos Questionários (Tentativas e Tempo Gasto)", xaxis_title="Questionário", xaxis_tickangle=-45, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=20, r=20, t=40, b=80), hovermode='x unified')
        fig_quiz.update_yaxes(title_text="Tempo (minutos)", secondary_y=False, showgrid=False)
        fig_quiz.update_yaxes(title_text="Tentativas", secondary_y=True, dtick=1, showgrid=False)
    else:
        fig_quiz = px.bar(title='Nenhum questionário respondido')

    # --------------------------------------------------------------------------
    # Bloco E: Construção do Grid de Interface (HTML)
    # --------------------------------------------------------------------------
    return html.Div(className='dashboard-grid', children=[
        
        # 1. Resumo do Aluno
        html.Div(className='student-header-card', children=[
            html.Div("👤", className='student-icon'),
            html.H2(nome_completo, className='student-name'),
            html.P([html.Strong("Email: "), email, " | ", html.Strong("Turma: "), grupo], className='student-meta'),
        ]),
        
        # 2. Indicadores Comportamentais
        html.Div(className='section-card', children=[
            html.H3("Indicadores Comportamentais (Engajamento e Acesso)", className='section-title'),
            html.Div(className='stats-grid', children=[
                html.Div(className='stat-card', children=[html.H4("Total de Sessões", className='stat-title'), html.H2(str(s_sessoes), className='stat-value'), html.P(f"Média da Turma: {m_sessoes}", className='stat-subtitle')]),
                html.Div(className='stat-card', children=[html.H4("Visualizações de Páginas", className='stat-title'), html.H2(str(s_views), className='stat-value'), html.P(f"Média da Turma: {m_views}", className='stat-subtitle')]),
                html.Div(className='stat-card', children=[html.H4("Dias Ativos", className='stat-title'), html.H2(str(s_days), className='stat-value'), html.P(f"Média da Turma: {m_days}", className='stat-subtitle')]),
            ]),
            html.Div(className='stats-grid', children=[
                html.Div(className='stat-card', children=[html.H4("Tempo Total Gasto", className='stat-title'), html.H2(format_duration(s_tempo_total), className='stat-value'), html.P(f"Média da Turma: {format_duration(m_tempo_total)}", className='stat-subtitle')]),
                html.Div(className='stat-card', children=[html.H4("Duração Média das Sessões", className='stat-title'), html.H2(format_duration(s_duracao_media), className='stat-value'), html.P(f"Média da Turma: {format_duration(m_duracao_media)}", className='stat-subtitle')]),
                html.Div(className='stat-card-flex', children=[html.H4("Período de Acesso", className='stat-title'), html.P([html.Strong("Primeiro: "), primeiro_acesso], className='access-date-text'), html.P([html.Strong("Último: "), ultimo_acesso], className='access-date-text text-danger' if ultimo_acesso == 'Nunca acessou' else 'access-date-text text-success')]),
            ]),
            html.Div(className='stats-grid', children=[
                html.Div(className='stat-card', children=[html.H4("Postagens no Fórum", className='stat-title'), html.H2(str(s_postagens), className='stat-value'), html.P(f"Média da Turma: {m_postagens}", className='stat-subtitle')]),
                html.Div(className='stat-card', children=[html.H4("Respostas no Fórum", className='stat-title'), html.H2(str(s_respostas), className='stat-value'), html.P(f"Média da Turma: {m_respostas}", className='stat-subtitle')]),
                html.Div(className='stat-card', children=[html.H4("Leituras no Fórum", className='stat-title'), html.H2(str(s_leituras), className='stat-value'), html.P(f"Média da Turma: {m_leituras}", className='stat-subtitle')]),
            ]),
            html.Div(className='graphs-grid-2col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(figure=fig_acessos)]),
                html.Div(className='graph-container', children=[dcc.Graph(figure=fig_horarios)])
            ]),
            html.Div(className='graphs-grid-1col', children=[
                html.Div(className='graph-container', children=[dcc.Graph(figure=fig_materiais)])
            ])
        ]),
        
        # 3. Indicadores Cognitivos
        html.Div(className='section-card', children=[
            html.H3("Indicadores Cognitivos", className='section-title'),
            html.Div(className='stats-grid-cognitive', children=[
                html.Div(className='stat-card-flex', children=[html.H4("Média Geral do Aluno", className='stat-title'), html.H2(f"{media_aluno_notas:.1f}", className='stat-value' if media_aluno_notas >= media_turma_notas else 'stat-value-danger'), html.P(f"Média da Turma: {media_turma_notas:.1f}", className='stat-subtitle')]),
                html.Div(className='stat-card-flex', children=[html.H4("Taxa de Realização de Atividades", className='stat-title-zero'), dcc.Graph(figure=fig_pie, className='graph-pie-style', config={'displayModeBar': False}), html.P(f"Média da Turma: {media_atividades_turma:.1f} atividades", className='stat-subtitle-zero')])
            ]),
            html.Div(className='graphs-grid-1col', children=[
                html.Div(className='graph-container-mb', children=[dcc.Graph(figure=fig_notas)]),
                html.Div(className='graph-container', children=[dcc.Graph(figure=fig_quiz)])
            ])
        ])
    ])
