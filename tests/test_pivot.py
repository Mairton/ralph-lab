import csv
from pathlib import Path

import pandas as pd
import pytest

from pipeline.build import build_join, build_pivot

ROOT = Path(__file__).resolve().parents[1]
TOLERANCIA_BRL = 0.5
CABECALHO_ESPERADO = "regiao,2026-01,2026-02,2026-03,2026-04,2026-05,2026-06"
REGIOES_ESPERADAS = ["Centro-Oeste", "Nordeste", "Sudeste", "Sul"]


@pytest.fixture(scope="module")
def pivot_path() -> Path:
    build_join(ROOT)
    build_pivot(ROOT)
    return ROOT / "pivot_receita.csv"


@pytest.fixture(scope="module")
def pivot(pivot_path) -> pd.DataFrame:
    return pd.read_csv(pivot_path, index_col="regiao")


def test_pivot_cabecalho_e_forma(pivot_path):
    linhas = pivot_path.read_text(encoding="utf-8").splitlines()
    assert linhas[0] == CABECALHO_ESPERADO
    dados = [linha for linha in linhas[1:] if linha.strip()]
    assert len(dados) == 4
    for linha in dados:
        assert len(linha.split(",")) == 7


def test_pivot_regioes_em_ordem_alfabetica(pivot):
    assert list(pivot.index) == REGIOES_ESPERADAS


def test_pivot_valores_com_ponto_e_duas_casas(pivot_path):
    with pivot_path.open(encoding="utf-8", newline="") as f:
        leitor = csv.reader(f)
        next(leitor)
        for linha in leitor:
            for celula in linha[1:]:
                assert "R$" not in celula
                inteiro, sep, decimais = celula.partition(".")
                assert sep == "." and len(decimais) == 2, celula
                assert inteiro.lstrip("-").isdigit(), celula


def test_pivot_total(pivot):
    assert pivot.to_numpy().sum() == pytest.approx(931274.06, abs=TOLERANCIA_BRL)


def test_pivot_sudeste_lidera(pivot):
    assert pivot.loc["Sudeste"].sum() == pytest.approx(265077.49, abs=TOLERANCIA_BRL)
    assert pivot.sum(axis=1).idxmax() == "Sudeste"
