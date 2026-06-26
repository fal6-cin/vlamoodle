import pandas as pd

# all_dfs = []

# files_to_join = [
#     'datasets/raws/logstore_standard_log_courseid_993_26_03.csv',
#     'datasets/raws/logstore_standard_log_courseid_993_26_04.csv',
#     'datasets/raws/logstore_standard_log_courseid_993_26_05.csv',
#     'datasets/raws/logstore_standard_log_courseid_993_26_06.csv'
# ]

# # Carregar cada arquivo e adicionar à lista 'all_dfs'
# for file_name in files_to_join:
#     df_temp = pd.read_csv(file_name, sep=';')
#     all_dfs.append(df_temp)

# # Concatenar todos os dataframes em um único 'logstore'
# logstore = pd.concat(all_dfs, ignore_index=True)

# print(f"Total de linhas no dataframe logstore combinado: {len(logstore)}")
# print(logstore.head())

students = pd.read_csv('datasets/raws/course_993_students.csv', sep=';')

# # --- Funções de Anonimização ---
# def anonimizar_nome(nome):
#     if pd.isna(nome): return nome
#     nome = str(nome)
#     if len(nome) <= 1: return nome
#     if len(nome) == 2: return nome[0] + '*'
#     return nome[0] + '*' * (len(nome) - 2) + nome[-1]

# def anonimizar_email(email):
#     if pd.isna(email): return email
#     email = str(email)
#     if '@' not in email: return email
#     nome_usuario, dominio = email.split('@', 1)
#     return '*' * len(nome_usuario) + '@' + dominio

# # Aplicar anonimização preservando as outras colunas
# for col in ['username', 'firstname', 'lastname']:
#     if col in students.columns:
#         students[col] = students[col].apply(anonimizar_nome)

# if 'email' in students.columns:
#     students['email'] = students['email'].apply(anonimizar_email)

# print("Exemplo de dados anonimizados:")
# print(students.head())

# students.to_csv('datasets/students_anon.csv', sep=';', index=False)

# logstore_filtered = logstore[logstore['userid'].isin(students['userid'])]
# print(f"Total de linhas no dataframe logstore filtrado: {len(logstore_filtered)}")
# print(logstore_filtered.head())

# logstore_filtered = logstore_filtered.copy()
# # Adicionar o grupo do aluno
# logstore_filtered = logstore_filtered.merge(students[['userid', 'grupos_do_aluno']], on='userid', how='left')
# logstore_filtered['timecreated_dt'] = pd.to_datetime(logstore_filtered['timecreated'], unit='s')
# logstore_filtered['data'] = logstore_filtered['timecreated_dt'].dt.date
# logstore_filtered['hora'] = logstore_filtered['timecreated_dt'].dt.time

# logstore_filtered['dia_da_semana'] = logstore_filtered['timecreated_dt'].dt.day_name()
# # Mapeamento dos nomes dos dias da semana para português
# dia_da_semana_map = {
#     'Sunday': 'Domingo',
#     'Monday': 'Segunda',
#     'Tuesday': 'Terça',
#     'Wednesday': 'Quarta',
#     'Thursday': 'Quinta',
#     'Friday': 'Sexta',
#     'Saturday': 'Sábado'
# }

# # Aplicar o mapeamento para converter os nomes dos dias
# logstore_filtered['dia_da_semana'] = logstore_filtered['dia_da_semana'].map(dia_da_semana_map)

# print(logstore_filtered[['timecreated', 'timecreated_dt', 'data', 'hora', 'dia_da_semana']].head())

# # Exportar para CSV
# logstore_filtered.to_csv('datasets/logstore_filtered.csv', sep=';', index=False)
# print("Dataframe logstore_filtered exportado com sucesso para 'datasets/logstore_filtered.csv'.")

# forunsinterations = pd.read_csv('datasets/raws/course_993_foruns.csv', sep=';')
# forunsinterations = forunsinterations[forunsinterations['userid'].isin(students['userid'])]
# print(forunsinterations.head())
# forunsinterations.to_csv('datasets/forum_interations.csv', sep=';', index=False)

# notas = pd.read_csv('datasets/raws/course_993_notas.csv', sep=';')
# notas = notas[notas['userid'].isin(students['userid'])]
# if 'nome_aluno' in notas.columns:
#     notas = notas.drop(columns=['nome_aluno'])
# notas = notas.dropna(subset=['nota_final'])
# notas = notas[notas['tipo_item'] == 'mod']

# for col in ['nota_final', 'nota_minima_possivel', 'nota_maxima_possivel']:
#     notas[col] = notas[col].astype(str).str.replace(',', '.').astype(float)

# divisor = notas['nota_maxima_possivel'] - notas['nota_minima_possivel']
# notas['nota_normalizada'] = notas['nota_final'].where(
#     divisor == 0, 
#     ((notas['nota_final'] - notas['nota_minima_possivel']) / divisor) * 10
# )
# print(notas.head())
# notas.to_csv('datasets/notas.csv', sep=';', index=False)

atividadesatrasadas = pd.read_csv('datasets/raws/course_993_atividadesatrasadas.csv', sep=';')
atividadesatrasadas = atividadesatrasadas[atividadesatrasadas['userid'].isin(students['userid'])]
if 'nome_aluno' in atividadesatrasadas.columns:
    atividadesatrasadas = atividadesatrasadas.drop(columns=['nome_aluno'])
print(atividadesatrasadas.head())
atividadesatrasadas.to_csv('datasets/atividadesatrasadas.csv', sep=';', index=False)
