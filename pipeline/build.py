"""Pipeline do CSV ao grafico.

Etapas:
    build_join(root)  -> vendas_lojas.csv (inner join de vendas.csv com lojas.csv por id_loja)

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


if __name__ == "__main__":
    build_join(ROOT)
