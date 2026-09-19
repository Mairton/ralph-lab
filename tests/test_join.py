from pathlib import Path

import pandas as pd
import pytest

from pipeline.build import build_join

ROOT = Path(__file__).resolve().parents[1]
TOLERANCIA_BRL = 0.5


@pytest.fixture(scope="module")
def vendas_lojas() -> pd.DataFrame:
    build_join(ROOT)
    return pd.read_csv(ROOT / "vendas_lojas.csv", dtype={"receita_brl": float})


def test_join_tem_420_linhas(vendas_lojas):
    assert len(vendas_lojas) == 420


def test_join_receita_total(vendas_lojas):
    assert vendas_lojas["receita_brl"].sum() == pytest.approx(931274.06, abs=TOLERANCIA_BRL)


def test_join_mantem_colunas_de_vendas_e_acrescenta_loja(vendas_lojas):
    colunas_vendas = list(pd.read_csv(ROOT / "vendas.csv", nrows=0).columns)
    for col in colunas_vendas:
        assert col in vendas_lojas.columns
    for col in ("nome_loja", "regiao", "uf", "gerente"):
        assert col in vendas_lojas.columns


def test_join_descarta_orfas_e_loja_sem_vendas(vendas_lojas):
    assert not (vendas_lojas["id_loja"] == 999).any()
    assert not (vendas_lojas["id_loja"] == 108).any()
