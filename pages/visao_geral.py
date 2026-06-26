import dash
from dash import html, dcc, callback, Output, Input, dash_table
import plotly.express as px
import pandas as pd

# Registrando esta página para que o app.py encontre
dash.register_page(__name__, path='/', name='Visão Geral')

df_logstore = pd.read_csv('datasets/logstore_filtered.csv', sep=';')
df_logstore['timecreated_dt'] = pd.to_datetime(df_logstore['timecreated_dt'])
df_students = pd.read_csv('datasets/students_anon.csv', sep=';')
df_forums = pd.read_csv('datasets/forum_interations.csv', sep=';')
df_notas = pd.read_csv('datasets/notas.csv', sep=';')
df_atrasadas = pd.read_csv('datasets/atividadesatrasadas.csv', sep=';')


# O que antes era app.layout, agora vira a variável 'layout' da página
layout = html.Div([
    html.H1(children='Visual Learning Analytics', className='page-title'),
    html.Label("Selecione a Turma:", htmlFor='dropdown-selection'),
    dcc.Dropdown(df_logstore.grupos_do_aluno.dropna().unique(), 'E1', id='dropdown-selection'),
    
    # Card para mostrar os acessos únicos
    html.Div(id='session-card', className='session-card'),
    
    html.Div([
        html.H3("Lista de Alunos da Turma", className='table-title', style={'marginTop': '30px'}),
        dash_table.DataTable(
            id='students-table',
            page_size=10,
            style_table={'overflowX': 'auto'}
        )
    ], style={'padding': '20px'}),

    html.H3("Alunos em Risco da Turma", className='table-title', style={'marginTop': '30px'}),

    html.Div(id='students-cards-container', className='students-cards-grid', style={'padding': '20px'}),

    dcc.Graph(id='graph-content')
    
])

# Os callbacks ficam no mesmo arquivo da página
@callback(
    Output('session-card', 'children'),
    Input('dropdown-selection', 'value')
)
def update_card(value):
    dff = df_logstore[df_logstore.grupos_do_aluno == value].copy()
    
    # Lógica de sessionization
    dff = dff.sort_values(by=['userid', 'timecreated'])
    dff['time_diff'] = dff.groupby('userid')['timecreated'].diff()
    dff['is_new_session'] = (dff['time_diff'] > 1800) | dff['time_diff'].isna()
    
    total_sessoes = dff['is_new_session'].sum()
    
    return [
        html.H4("Acessos Únicos (Sessões)", className='card-title'),
        html.H2(f"{int(total_sessoes)}", className='card-value')
    ]

@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    dff = df_logstore[df_logstore.grupos_do_aluno==value]
    df_hits = dff.groupby('dia_da_semana').size().reset_index(name='Interações')

    semana_map = {
        'Domingo': 1, 'Segunda': 2, 'Terça': 3, 'Quarta': 4,
        'Quinta': 5, 'Sexta': 6, 'Sábado': 7
    }
    ordem_semana = list(semana_map.keys())
    
    return px.bar(df_hits, x='dia_da_semana', y='Interações',
                  title='Número de interações durante a semana',
                  labels={'dia_da_semana': 'Dia da semana'},
                  category_orders={'dia_da_semana': ordem_semana})

@callback(
    Output('students-table', 'data'),
    Output('students-table', 'columns'),
    Output('students-cards-container', 'children'),
    Input('dropdown-selection', 'value')
)
def update_table(value):
    # Filtrar estudantes pelo grupo selecionado
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
    df_30_dias['is_new_session'] = (df_30_dias['time_diff'] > 1800) | df_30_dias['time_diff'].isna()
    
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
    
    # Filtro de alunos em risco
    dff = dff[
        (dff['qtd_criacao_forum'] == 0) & 
        (dff['qtd_resposta_forum'] == 0) & 
        (dff['qtd_leitura_forum'] == 0) & 
        (dff['acessos_30_dias'] == 0) & 
        (dff['media_notas'] < 6) & 
        (dff['qtd_atividades_atrasadas'] > 1) &
        (dff['ultimo_acesso'].notna())
    ]
    
    # Selecionar as colunas relevantes para exibição
    cols_to_show = ['userid', 'firstname', 'lastname', 'email', 'ultimo_acesso', 'qtd_criacao_forum', 'qtd_resposta_forum', 'qtd_leitura_forum', 'acessos_30_dias', 'media_notas', 'qtd_atividades_atrasadas', 'qtd_atividades_realizadas']
    df_show = dff[cols_to_show]
    
    # Definir colunas da tabela
    columns = []
    nomes_colunas = {
        'ultimo_acesso': 'Último Acesso',
        'qtd_criacao_forum': 'Fóruns Criados',
        'qtd_resposta_forum': 'Respostas no Fórum',
        'qtd_leitura_forum': 'Fóruns Lidos',
        'acessos_30_dias': 'Acessos Últimos 30 Dias (até 20/06/26)',
        'media_notas': 'Média das Notas',
        'qtd_atividades_atrasadas': 'Atividades Atrasadas'
    }
    
    for i in df_show.columns:
        if i in nomes_colunas:
            columns.append({'name': nomes_colunas[i], 'id': i})
        else:
            columns.append({'name': i.capitalize(), 'id': i})
    
    # Obter dados
    data = df_show.to_dict('records')
    
    # Gerar cards
    cards = []
    for row in data:
        lname_initial = str(row['lastname'])[0] + "." if pd.notna(row['lastname']) and str(row['lastname']) != "" else ""
        nome_exibicao = f"{row['firstname']} {lname_initial}"
        
        # Formatar data ultimo acesso
        ultimo_acesso_val = row.get('ultimo_acesso', '')
        if pd.notna(ultimo_acesso_val) and ultimo_acesso_val != '':
            ultimo_acesso_fmt = pd.to_datetime(ultimo_acesso_val).strftime('%d/%m/%Y %H:%M')
        else:
            ultimo_acesso_fmt = 'Nunca'
            
        valor_style = {'color': 'red'}
        
        card = html.Div(className='student-card', children=[
            html.Div("👤", className='student-avatar'),
            html.H4(nome_exibicao, className='student-name'),
            html.P([html.Strong("Último Acesso: "), html.Span(ultimo_acesso_fmt, style=valor_style)]),
            html.P([html.Strong("Fórum (Postagens): "), html.Span(f"{int(row.get('qtd_criacao_forum', 0)) + int(row.get('qtd_resposta_forum', 0))}", style=valor_style)]),
            html.P([html.Strong("Fórum (Leituras): "), html.Span(f"{int(row.get('qtd_leitura_forum', 0))}", style=valor_style)]),
            html.P([html.Strong("Média das Notas: "), html.Span(str(row.get('media_notas', '')), style=valor_style)]),
            html.P([html.Strong("Atividades Atrasadas: "), html.Span(str(row.get('qtd_atividades_atrasadas', 0)), style=valor_style)]),
            html.P([html.Strong("Atividades Realizadas: "), html.Span(str(row.get('qtd_atividades_realizadas', 0)), style=valor_style)])
        ])
        cards.append(card)
    
    return data, columns, cards
