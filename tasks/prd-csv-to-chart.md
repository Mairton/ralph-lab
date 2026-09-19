# PRD: Do CSV ao gráfico — pipeline vendas × lojas (ralph-lab)

## Perguntas de esclarecimento (respondidas pelo condutor do loop)

1. Qual é o objetivo principal?
   A. Explorar os dados livremente
   B. **Produzir três artefatos determinísticos (join, pivot, página com gráfico) validados por testes** ← escolhido
   C. Construir um dashboard interativo
2. Como tratar as anomalias dos dados (3 vendas órfãs `id_loja=999`; loja 108 sem vendas)?
   A. Left join a partir de `vendas.csv`
   B. **Inner join por `id_loja`, descartando as órfãs e a loja sem vendas, e documentando a perda** ← escolhido
   C. Apagar as linhas problemáticas dos CSVs de origem
3. Qual é o critério de pronto?
   A. "Os arquivos existem"
   B. **A suíte `pytest` inteira verde, com pelo menos 4 casos que checam os números de referência** ← escolhido
4. Qual stack?
   A. Shell + awk
   B. **Python 3 + pandas para o pipeline; HTML estático com Chart.js via CDN para o gráfico** ← escolhido
5. Onde ficam as saídas?
   A. Em `data/` e `web/`
   B. **Na raiz do repositório: `vendas_lojas.csv`, `pivot_receita.csv`, `index.html`** ← escolhido

## 1. Introdução / Visão geral

O repositório contém dois CSVs sintéticos: `vendas.csv` (423 vendas, fato) e `lojas.csv`
(8 lojas, dimensão). Precisamos de um pipeline reproduzível que junte os dois por `id_loja`,
agregue a receita por região e mês, e publique uma página estática com um gráfico da receita
mensal por região e um parágrafo de conclusão. O pipeline é construído pelo laço Ralph:
cada iteração implementa uma história, roda `pytest` e só commita com a suíte verde.

Os dados têm duas armadilhas propositais que NÃO são bugs e NÃO devem ser "consertadas"
editando os CSVs:

- Três vendas (`V00421`, `V00422`, `V00423`) têm `id_loja=999`, que não existe em `lojas.csv`.
  Somam R$ 8.120,00.
- A loja 108 (Batel/PR, região Sul) existe em `lojas.csv` mas não tem nenhuma venda.

Decisão: usar **inner join**. As 3 vendas órfãs ficam de fora (receita cai de 939.394,06
para 931.274,06) e a loja 108 não aparece no relatório. A decisão e a perda devem ser
registradas no `README.md`.

## 2. Objetivos

- Gerar `vendas_lojas.csv` na raiz com exatamente **420 linhas de dados** e a coluna `receita_brl` somando **931274.06** (tolerância 0,50).
- Gerar `pivot_receita.csv` na raiz com cabeçalho exato `regiao,2026-01,2026-02,2026-03,2026-04,2026-05,2026-06`, 4 linhas de dados (Centro-Oeste, Nordeste, Sudeste, Sul), valores com ponto decimal e 2 casas, soma total das células = **931274.06**.
- Gerar `index.html` na raiz com um elemento de gráfico (`<canvas>` com Chart.js) da receita mensal por região e um `<p>` de conclusão com **≥ 300 caracteres**.
- Ter uma suíte `pytest` em `tests/test_*.py` com **≥ 4 testes** passando que definem "pronto".
- Documentar no `README.md` a escolha do join e o que ficou de fora.

## 3. Histórias de usuário

### US-001: Script de join e teste do join
**Descrição:** Como analista, quero `vendas_lojas.csv` com o inner join de vendas e lojas por `id_loja` para ter cada venda enriquecida com região/UF.

**Critérios de aceitação:**
- [ ] Existe `pipeline/build.py` (ou módulo equivalente) com uma função `build_join()` que lê `vendas.csv` e `lojas.csv` com pandas, lendo `receita_brl` como float (`dtype={'receita_brl': float}`), faz `merge(how='inner', on='id_loja')` e grava `vendas_lojas.csv` na raiz do repo, `index=False`.
- [ ] `vendas_lojas.csv` mantém todas as colunas de `vendas.csv` (nome `receita_brl` inalterado) e acrescenta `nome_loja`, `regiao`, `uf`, `gerente`.
- [ ] `vendas_lojas.csv` tem 420 linhas de dados (421 linhas contando o cabeçalho).
- [ ] O script imprime no stdout quantas vendas entraram (423), quantas saíram (3 órfãs, `id_loja=999`, R$ 8120.00) e quantas lojas ficaram sem linha (1: loja 108).
- [ ] Os CSVs de origem `vendas.csv` e `lojas.csv` NÃO são modificados.
- [ ] Existe `tests/test_join.py` com pelo menos 2 testes: (a) `vendas_lojas.csv` tem 420 linhas de dados; (b) a soma de `receita_brl` é 931274.06 ± 0.5.
- [ ] `python -m pytest -q` passa.

### US-002: Pivot região × mês e teste do pivot
**Descrição:** Como gestor, quero `pivot_receita.csv` com a receita por região e mês para comparar regiões ao longo do semestre.

**Critérios de aceitação:**
- [ ] Função `build_pivot()` lê `vendas_lojas.csv`, deriva o mês como `YYYY-MM` a partir de `data`, e faz `pivot_table(index='regiao', columns='mes', values='receita_brl', aggfunc='sum')`.
- [ ] O arquivo `pivot_receita.csv` na raiz tem o cabeçalho EXATO: `regiao,2026-01,2026-02,2026-03,2026-04,2026-05,2026-06`.
- [ ] 4 linhas de dados em ordem alfabética: Centro-Oeste, Nordeste, Sudeste, Sul; 7 colunas.
- [ ] Valores com ponto como separador decimal e 2 casas (`float_format='%.2f'`), sem `R$` e sem separador de milhar. Arredondar só na hora de escrever, não em somas parciais.
- [ ] A soma de todas as 24 células numéricas é 931274.06 ± 0.5; a linha Sudeste soma 265077.49 ± 0.5.
- [ ] Existe `tests/test_pivot.py` com pelo menos 2 testes: (a) cabeçalho exato e forma 4×7; (b) soma das células = 931274.06 ± 0.5.
- [ ] `python -m pytest -q` passa.

### US-003: Página `index.html` com gráfico e conclusão
**Descrição:** Como gestor, quero uma página estática com um gráfico da receita mensal por região e um parágrafo de conclusão.

**Critérios de aceitação:**
- [ ] Função `build_html()` lê `pivot_receita.csv` e gera `index.html` na raiz do repo.
- [ ] A página tem um `<canvas id="grafico">` e usa Chart.js via CDN (`https://cdn.jsdelivr.net/npm/chart.js`) com um gráfico de linhas (ou barras agrupadas): eixo X = meses 2026-01..2026-06, uma série por região, dados embutidos no HTML (sem fetch em runtime).
- [ ] A página tem um `<p id="conclusao">` com pelo menos 300 caracteres, em português, citando a receita total (R$ 931.274,06), a região líder (Sudeste, R$ 265.077,49) e o fato de a loja 108 e as 3 vendas órfãs não constarem do relatório.
- [ ] Existe `tests/test_html.py` com pelo menos 2 testes: (a) `index.html` contém `<canvas` ou `<svg`; (b) o texto do `<p id="conclusao">` tem ≥ 300 caracteres.
- [ ] `python -m pytest -q` passa.

### US-004: Ponto de entrada único e README com a decisão de join
**Descrição:** Como condutor do loop, quero rodar `python pipeline/build.py` e regenerar os três artefatos, e ler no README qual join foi usado e o que ficou de fora.

**Critérios de aceitação:**
- [ ] `python pipeline/build.py` roda `build_join()`, `build_pivot()` e `build_html()` em sequência e regenera os três arquivos de forma determinística (rodar duas vezes gera arquivos idênticos).
- [ ] `README.md` na raiz tem uma seção "Decisão de join" dizendo: inner join por `id_loja`; 423 vendas de entrada, 420 de saída; 3 vendas órfãs (`id_loja=999`, R$ 8.120,00) descartadas; loja 108 (Batel/PR) ausente do relatório; receita total 931.274,06.
- [ ] `README.md` explica como rodar o pipeline e os testes.
- [ ] A suíte inteira `python -m pytest -q` tem ≥ 4 testes e passa sem falhas.

## 4. Requisitos funcionais

- FR-1: Ler `vendas.csv` e `lojas.csv` com pandas; `receita_brl` como número (float), nunca como texto.
- FR-2: Inner join por `id_loja`; salvar em `vendas_lojas.csv` na raiz, sem índice, mantendo o nome `receita_brl`.
- FR-3: Pivot região × mês (`YYYY-MM`) somando `receita_brl`; salvar em `pivot_receita.csv` na raiz com o cabeçalho exato e 2 casas decimais.
- FR-4: `index.html` na raiz com `<canvas>` + Chart.js e `<p id="conclusao">` ≥ 300 caracteres.
- FR-5: Testes em `tests/test_*.py` (≥ 4) que verifiquem: 420 linhas do join, soma 931274.06, cabeçalho/forma do pivot, soma do pivot, gráfico e conclusão na página.
- FR-6: Os testes devem ler os artefatos gerados na raiz (usar `Path(__file__).resolve().parents[1]` como raiz), e um `conftest.py` ou fixture pode regenerar os artefatos chamando o pipeline antes dos testes.
- FR-7: Registrar no README a escolha do join e a perda de receita.

## 5. Não-objetivos

- Não modificar, limpar ou apagar linhas de `vendas.csv` e `lojas.csv`.
- Não inventar dados nem preencher a loja 108 com valores fictícios.
- Não construir servidor web, API ou dashboard interativo; a página é estática.
- Não usar formatação monetária (`R$`, separador de milhar) dentro dos CSVs.
- Não usar left join; a decisão é inner join, documentada.

## 6. Considerações técnicas

- Ambiente: Python 3, pandas, pytest. Sem outras dependências obrigatórias.
- Rodar sempre a partir da raiz do repositório; caminhos relativos à raiz.
- `python -m pytest -q` é o comando de verificação. `python` e `python3` estão disponíveis.
- Sem typecheck configurado: "Typecheck passes" equivale a `python -m py_compile` dos arquivos alterados.
- Não commitar segredos (`.env`, `.pem`, `credentials.json`), nem `__pycache__`/`.pytest_cache`.

## 7. Métricas de sucesso

- `vendas_lojas.csv`: 420 linhas; soma `receita_brl` = 931274.06.
- `pivot_receita.csv`: cabeçalho exato; 4×7; soma = 931274.06; Sudeste = 265077.49.
- `index.html`: elemento de gráfico + `<p>` ≥ 300 caracteres.
- `pytest`: ≥ 4 testes, 0 falhas.

## 8. Questões em aberto

- Nenhuma. Os valores de referência vêm do README dos dados e foram conferidos manualmente.
