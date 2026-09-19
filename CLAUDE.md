# ralph-lab: do CSV ao grafico

Pipeline em Python/pandas: `vendas.csv` + `lojas.csv` -> `vendas_lojas.csv` -> `pivot_receita.csv` -> `index.html`.

## Convencoes
- `vendas.csv` e `lojas.csv` sao a fonte e **nunca** sao modificados. Nao inventar dados; nao preencher a loja 108.
- Os tres artefatos gerados ficam na **raiz** do repo (nao usar `data/` nem `web/`).
- Toda etapa e uma funcao `build_*(root: Path)` em `pipeline/build.py`; `ROOT = Path(__file__).resolve().parents[1]`.
- `build_all(root)` roda join -> pivot -> html em sequencia e e o que o `__main__` executa; testes de ponta a ponta chamam `build_all`, nao o `__main__`.
- README.md (secao "Decisao de join") repete os numeros de referencia (423/420/3 orfas/loja 108/R$ 931.274,06 vs R$ 939.394,06); se a logica do join mudar, atualizar README e os testes juntos.
- Ler `receita_brl` sempre com `dtype={"receita_brl": float}`; manter o nome da coluna (o autograder soma essa coluna).
- Join e **inner** por `id_loja`: 3 vendas orfas (id_loja=999) e a loja 108 ficam fora do relatorio.
- Arredondar apenas ao gravar CSV (`float_format="%.2f"`), nunca em somas parciais.
- Pivot: `mes = data.str[:7]`; antes de gravar, `pivot.columns.name = None` (senao o `to_csv` escreve uma linha extra `mes`) e `index=True` para a coluna `regiao` sair primeiro.
- HTML: `build_html` le `pivot_receita.csv` com `index_col="regiao"`; os dados do grafico ficam num `<script id="dados-pivot" type="application/json">` (sem fetch); os numeros da conclusao sao calculados (nunca digitados) e formatados com `formatar_brl` (R$ 931.274,06). Nao inserir timestamps: a saida deve ser deterministica.
- Sem browser nesta sessao: validar o HTML por parsing nos testes (`html.parser`/regex); a verificacao visual e manual.

## Comandos
- Pipeline: `python pipeline/build.py` (da raiz); deve ser deterministico (rodar 2x -> md5 identicos), coberto por `tests/test_pipeline.py`
- Testes: `python -m pytest -q` (da raiz; `pipeline` e importavel porque rootdir e a raiz)
- Typecheck: `python -m py_compile <arquivos .py>`

## Testes
- Ficam em `tests/test_*.py`, localizam a raiz com `Path(__file__).resolve().parents[1]` e podem chamar `build_*` antes de ler o artefato.
- Tolerancia para valores em R$: `pytest.approx(x, abs=0.5)`.
