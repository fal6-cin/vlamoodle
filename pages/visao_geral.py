import dash
from dash import html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd

# Registrando esta página para que o app.py encontre
dash.register_page(__name__, path='/', name='Visão Geral')

df = pd.read_csv('datasets/logstore_filtered.csv', sep=';')

# O que antes era app.layout, agora vira a variável 'layout' da página
layout = html.Div([
    html.H1(children='Title of Dash App', className='page-title'),
    html.Label("Selecione a Turma:", htmlFor='dropdown-selection'),
    dcc.Dropdown(df.grupos_do_aluno.dropna().unique(), 'E1', id='dropdown-selection'),
    
    # Card para mostrar os acessos únicos
    html.Div(id='session-card', className='session-card'),
    
    dcc.Graph(id='graph-content')
])

# Os callbacks ficam no mesmo arquivo da página
@callback(
    Output('session-card', 'children'),
    Input('dropdown-selection', 'value')
)
def update_card(value):
    dff = df[df.grupos_do_aluno == value].copy()
    
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
    dff = df[df.grupos_do_aluno==value]
    df_hits = dff.groupby('dia_da_semana').size().reset_index(name='hits')

    semana_map = {
        'Sunday': 1, 'Monday': 2, 'Tuesday': 3, 'Wednesday': 4,
        'Thursday': 5, 'Friday': 6, 'Saturday': 7
    }
    ordem_semana = list(semana_map.keys())
    
    return px.bar(df_hits, x='dia_da_semana', y='hits',
                  title='Número de hits durante a semana',
                  labels={'dia_da_semana': 'Dia da semana'},
                  category_orders={'dia_da_semana': ordem_semana})
