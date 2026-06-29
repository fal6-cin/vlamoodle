import dash
from dash import Dash, html, dcc

# Iniciando o app com suporte a páginas (use_pages=True)
app = Dash(__name__, use_pages=True)

server = app.server 

app.layout = html.Div([
    
    # Cabeçalho / Menu de Navegação estilizado como Abas
    html.Div([
        html.Div(
            dcc.Link(
                f"{page['name']}", href=page["relative_path"],
                className='nav-link'
            )
        ) for page in dash.page_registry.values()
    ], className='nav-container'),
    
    # O conteúdo da página atual será injetado aqui
    html.Div([
        dash.page_container
    ], className='page-container')
])

if __name__ == '__main__':
     app.run_server(debug=True, port=7860)