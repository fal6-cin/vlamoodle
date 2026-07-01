# Dashboard de Análise de Logs de Alunos

Este projeto é uma aplicação analítica construída com **Plotly Dash** para visualizar e analisar logs de acesso de estudantes em um ambiente educacional. Ele inclui uma etapa de processamento de dados (ETL) que consolida registros de acessos, anonimiza informações sensíveis dos alunos e prepara os dados para a visualização.

## 🗂️ Estrutura do Projeto

O projeto utiliza o recurso **Dash Pages** para facilitar a criação de aplicativos modulares e escaláveis.

```text
plotlydash/
│
├── app.py                  # Ponto de entrada: inicializa o app e o layout de navegação (abas)
├── etl.py                  # Script de processamento, consolidação e anonimização de dados
├── requirements.txt        # Dependências do projeto (dash, pandas, plotly)
├── Dockerfile              # Configuração da imagem Docker (porta 7860 para Hugging Face)
├── render.yaml             # Configuração para deploy na plataforma Render
├── .gitignore              # Arquivos ignorados pelo Git (incluindo datasets brutos e venv)
│
├── pages/                  # Pasta que o Dash lê automaticamente para gerar as rotas/páginas
│   └── visao_geral.py      # Página inicial (Filtros, KPIs de Sessão e Gráficos)
│
├── assets/                 # Pasta de arquivos estáticos
│   └── style.css           # Estilização visual (CSS) do dashboard
│
└── datasets/               # Diretório para armazenamento de arquivos .csv
    ├── raws/               # Arquivos brutos (originais) baixados do sistema educacional
    ├── logstore_filtered.csv # Arquivo processado pelo etl.py para o Dash consumir
    └── students_anon.csv   # Base de alunos com nomes e e-mails anonimizados
```

## 🚀 Como Executar Localmente

### 1. Preparando o Ambiente
Ative o seu ambiente virtual e instale as dependências contidas no `requirements.txt`:
```bash
# Ativando o ambiente virtual (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Instalando dependências
pip install -r requirements.txt
```

### 2. Processando os Dados (ETL)
Antes de rodar o dashboard, é necessário gerar os arquivos processados e anonimizados. Certifique-se de que seus arquivos brutos estão na pasta `datasets/raws/`.
```bash
python etl.py
```
Isso irá gerar os arquivos `logstore_filtered.csv` e `students_anon.csv` na pasta `datasets/`.

### 3. Iniciando o Dashboard
Com os dados prontos, inicie o servidor web do Dash:
```bash
python app.py
```
Acesse o aplicativo no seu navegador através do endereço: [http://127.0.0.1:8050/](http://127.0.0.1:8050/)

### 4. Executando com Docker (Opcional)
Você também pode executar a aplicação utilizando Docker (útil para simular o ambiente de produção):
```bash
# Construir a imagem Docker
docker build -t vlamoodle .

# Executar o container
docker run -p 7860:7860 vlamoodle
```
Acesse no navegador: [http://127.0.0.1:7860/](http://127.0.0.1:7860/)

## ✨ Modificações Recentes
* **Suporte a Deploy:** Inclusão do arquivo `render.yaml` configurado com `gunicorn` para implantação no Render.
* **Suporte a Docker:** Adição do `Dockerfile` configurado para rodar na porta `7860`, atendendo aos requisitos do **Hugging Face**.
* **Compatibilidade WSGI:** Exportação da instância Flask no `app.py` (`server = app.server`) para execução otimizada com o Gunicorn em produção.


## 🛠️ Tecnologias Utilizadas
* **Python**
* **Plotly Dash:** Criação da interface web reativa e componentização HTML em Python.
* **Pandas:** Manipulação de dados (Limpeza, join, cálculo de tempo de sessão).
