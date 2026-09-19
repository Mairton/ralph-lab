"""Pipeline do CSV ao grafico.

Etapas:
    build_join(root)  -> vendas_lojas.csv (inner join de vendas.csv com lojas.csv por id_loja)
    build_pivot(root) -> pivot_receita.csv (receita somada por regiao x mes, YYYY-MM)

Decisao de join: INNER. Vendas orfas (id_loja sem correspondencia em lojas.csv)
e lojas sem vendas ficam de fora do relatorio. Os CSVs de origem nunca sao alterados.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

VENDAS_CSV = "vendas.csv"
LOJAS_CSV = "lojas.csv"
VENDAS_LOJAS_CSV = "vendas_lojas.csv"
PIVOT_RECEITA_CSV = "pivot_receita.csv"


def _read_sources(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Le os CSVs de origem. receita_brl e lida como float, nunca como texto."""
    vendas = pd.read_csv(root / VENDAS_CSV, dtype={"receita_brl": float})
    lojas = pd.read_csv(root / LOJAS_CSV)
    return vendas, lojas


def build_join(root: Path = ROOT) -> pd.DataFrame:
    """Faz o inner join de vendas.csv com lojas.csv por id_loja e grava vendas_lojas.csv na raiz.

    Imprime no stdout um resumo: vendas de entrada, vendas orfas descartadas
    (id_loja sem loja correspondente) e lojas sem nenhuma venda.
    """
    root = Path(root)
    vendas, lojas = _read_sources(root)

    joined = vendas.merge(lojas, how="inner", on="id_loja")

    orfas = vendas[~vendas["id_loja"].isin(lojas["id_loja"])]
    lojas_sem_vendas = lojas[~lojas["id_loja"].isin(vendas["id_loja"])]

    print(f"Vendas de entrada: {len(vendas)}")
    ids_orfas = ", ".join(str(i) for i in sorted(orfas["id_loja"].unique()))
    print(
        f"Vendas orfas descartadas: {len(orfas)} "
        f"(id_loja={ids_orfas}, R$ {orfas['receita_brl'].sum():.2f})"
    )
    descricao_lojas = ", ".join(
        f"loja {row.id_loja} ({row.nome_loja}/{row.uf})"
        for row in lojas_sem_vendas.itertuples(index=False)
    )
    print(f"Lojas sem vendas: {len(lojas_sem_vendas)} ({descricao_lojas})")
    print(f"Vendas no join (inner): {len(joined)}")

    joined.to_csv(root / VENDAS_LOJAS_CSV, index=False)
    return joined


def build_pivot(root: Path = ROOT) -> pd.DataFrame:
    """Agrega a receita de vendas_lojas.csv por regiao (linhas) x mes (colunas) e grava pivot_receita.csv.

    O mes e derivado de `data` como YYYY-MM. As regioes saem em ordem alfabetica e os
    meses em ordem cronologica. O arredondamento para 2 casas acontece apenas na gravacao
    (float_format="%.2f"); as somas parciais usam os valores originais.
    """
    root = Path(root)
    vendas_lojas = pd.read_csv(root / VENDAS_LOJAS_CSV, dtype={"receita_brl": float})

    vendas_lojas["mes"] = vendas_lojas["data"].astype(str).str[:7]
    pivot = pd.pivot_table(
        vendas_lojas,
        index="regiao",
        columns="mes",
        values="receita_brl",
        aggfunc="sum",
        fill_value=0.0,
    )
    pivot = pivot.sort_index(axis=0).sort_index(axis=1)
    pivot.columns.name = None

    print(f"Pivot receita: {pivot.shape[0]} regioes x {pivot.shape[1]} meses "
          f"({pivot.columns[0]} a {pivot.columns[-1]})")
    print(f"Receita total do pivot: R$ {pivot.to_numpy().sum():.2f}")

    pivot.to_csv(root / PIVOT_RECEITA_CSV, index=True, float_format="%.2f")
    return pivot


if __name__ == "__main__":
    build_join(ROOT)
    build_pivot(ROOT)
