# ralph-lab: do CSV ao grafico

Pipeline em Python/pandas: `vendas.csv` + `lojas.csv` -> `vendas_lojas.csv` -> `pivot_receita.csv` -> `index.html`.

## Convencoes
- `vendas.csv` e `lojas.csv` sao a fonte e **nunca** sao modificados. Nao inventar dados; nao preencher a loja 108.
- Os tres artefatos gerados ficam na **raiz** do repo (nao usar `data/` nem `web/`).
- Toda etapa e uma funcao `build_*(root: Path)` em `pipeline/build.py`; `ROOT = Path(__file__).resolve().parents[1]`.
- Ler `receita_brl` sempre com `dtype={"receita_brl": float}`; manter o nome da coluna (o autograder soma essa coluna).
- Join e **inner** por `id_loja`: 3 vendas orfas (id_loja=999) e a loja 108 ficam fora do relatorio.
- Arredondar apenas ao gravar CSV (`float_format="%.2f"`), nunca em somas parciais.

## Comandos
- Pipeline: `python pipeline/build.py` (da raiz)
- Testes: `python -m pytest -q` (da raiz; `pipeline` e importavel porque rootdir e a raiz)
- Typecheck: `python -m py_compile <arquivos .py>`

## Testes
- Ficam em `tests/test_*.py`, localizam a raiz com `Path(__file__).resolve().parents[1]` e podem chamar `build_*` antes de ler o artefato.
- Tolerancia para valores em R$: `pytest.approx(x, abs=0.5)`.
