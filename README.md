# ralph-lab: do CSV ao grafico

Pipeline reproduzivel em Python/pandas que parte de dois CSVs de origem
(`vendas.csv` e `lojas.csv`), junta-os por `id_loja`, agrega a receita por
regiao e mes e publica uma pagina estatica com um grafico de linhas (Chart.js)
e um paragrafo de conclusao.

```
vendas.csv + lojas.csv  ->  vendas_lojas.csv  ->  pivot_receita.csv  ->  index.html
```

Os tres artefatos gerados ficam na raiz do repositorio e sao regenerados de
forma deterministica: rodar o pipeline duas vezes produz arquivos identicos.

## Como rodar

Requisitos: Python 3.10+ com `pandas` e `pytest` instalados.

```bash
# Regenera vendas_lojas.csv, pivot_receita.csv e index.html (rodar da raiz)
python pipeline/build.py

# Suite de testes (rodar da raiz; `pipeline` e importavel porque o rootdir e a raiz)
python -m pytest -q

# "Typecheck": compilacao dos .py sem erro
python -m py_compile pipeline/build.py tests/*.py
```

Para ver o grafico, abra `index.html` no navegador com acesso a internet
(o Chart.js e carregado da CDN jsDelivr; os dados ficam embutidos na pagina,
sem fetch em tempo de execucao).

## Decisao de join

O relatorio usa **inner join por `id_loja`** entre `vendas.csv` e `lojas.csv`.
Isso significa que so entram no relatorio as vendas cuja loja existe no cadastro
e so aparecem as lojas que tiveram ao menos uma venda.

| Item | Valor |
| --- | --- |
| Vendas de entrada (`vendas.csv`) | 423 |
| Vendas de saida (`vendas_lojas.csv`) | 420 |
| Vendas orfas descartadas | 3 (V00421, V00422, V00423; `id_loja=999`; R$ 8.120,00) |
| Loja ausente do relatorio | 108 (Batel/PR), sem nenhuma venda no periodo |
| Receita total do relatorio | R$ 931.274,06 |
| Receita total do arquivo bruto | R$ 939.394,06 |

Consequencias da decisao:

- As 3 vendas orfas (V00421, V00422 e V00423) apontam para `id_loja=999`, que
  nao existe em `lojas.csv`. Sem regiao/UF conhecidas, elas nao podem ser
  alocadas no pivot e sao descartadas. A diferenca entre a receita bruta
  (R$ 939.394,06) e a do relatorio (R$ 931.274,06) e exatamente a receita
  dessas 3 vendas (R$ 8.120,00).
- A loja 108 (Batel/PR, regiao Sul) esta cadastrada, mas nao registrou nenhuma
  venda. Ela nao aparece em `vendas_lojas.csv`, no pivot, no grafico nem na
  tabela. A regiao Sul continua no relatorio por causa da loja 107 (Moinhos/RS).
- Os arquivos de origem **nunca** sao modificados: as vendas orfas nao sao
  apagadas nem corrigidas, e a loja 108 nao recebe valores ficticios.
  `build_join` imprime esses descartes no stdout para deixar a perda de dados
  explicita a cada execucao.

## Artefatos gerados

- `vendas_lojas.csv`: 420 linhas de dados com todas as colunas de `vendas.csv`
  (`receita_brl` inalterada) mais `nome_loja`, `regiao`, `uf` e `gerente`.
- `pivot_receita.csv`: receita somada por regiao (linhas, em ordem alfabetica)
  x mes (colunas `2026-01` a `2026-06`). Cabecalho exato
  `regiao,2026-01,2026-02,2026-03,2026-04,2026-05,2026-06`, valores com ponto
  decimal e 2 casas, sem `R$` e sem separador de milhar. O arredondamento
  acontece apenas na gravacao, nunca nas somas parciais.
- `index.html`: pagina com `<h1>`, grafico de linhas (`<canvas id="grafico">`,
  uma serie por regiao, eixo X = meses), tabela HTML do pivot e
  `<p id="conclusao">` com os numeros calculados a partir do pivot
  (receita total, regiao lider e itens excluidos pelo inner join).

## Estrutura do repositorio

```
.
|-- vendas.csv             # fonte (423 vendas) - nunca modificado
|-- lojas.csv              # fonte (8 lojas) - nunca modificado
|-- vendas_lojas.csv       # gerado: inner join por id_loja (420 linhas)
|-- pivot_receita.csv      # gerado: receita por regiao x mes
|-- index.html             # gerado: grafico Chart.js + tabela + conclusao
|-- pipeline/
|   |-- __init__.py
|   `-- build.py           # build_join, build_pivot, build_html, build_all (+ __main__)
|-- tests/
|   |-- test_join.py       # 420 linhas, receita total, colunas, exclusoes
|   |-- test_pivot.py      # cabecalho exato, forma 4x7, formato, totais
|   |-- test_html.py       # canvas/CDN, conclusao >= 300 chars, JSON embutido
|   `-- test_pipeline.py   # ponto de entrada, determinismo, fontes intactas
|-- scripts/ralph/         # laco Ralph: prd.json, progress.txt, ralph.sh
|-- tasks/                 # PRD em markdown
|-- CLAUDE.md              # convencoes do projeto para agentes
`-- README.md
```

Cada etapa do pipeline e uma funcao `build_*(root: Path)` em
`pipeline/build.py` que le e grava na raiz do repositorio
(`ROOT = Path(__file__).resolve().parents[1]`). `build_all(root)` roda as tres
em sequencia e e o que o bloco `if __name__ == "__main__"` executa.
