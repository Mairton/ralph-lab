import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from pipeline.build import build_all

ROOT = Path(__file__).resolve().parents[1]
ARTEFATOS = ("vendas_lojas.csv", "pivot_receita.csv", "index.html")
FONTES = ("vendas.csv", "lojas.csv")


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pipeline_executado() -> dict[str, str]:
    """Roda o pipeline via build_all e devolve os md5 dos artefatos gerados."""
    build_all(ROOT)
    return {nome: _md5(ROOT / nome) for nome in ARTEFATOS}


def test_pipeline_regenera_artefatos(pipeline_executado):
    for nome in ARTEFATOS:
        caminho = ROOT / nome
        assert caminho.is_file(), f"{nome} nao foi gerado na raiz"
        assert caminho.stat().st_size > 0, f"{nome} esta vazio"


def test_pipeline_e_deterministico(pipeline_executado):
    build_all(ROOT)
    for nome in ARTEFATOS:
        assert _md5(ROOT / nome) == pipeline_executado[nome], f"{nome} mudou entre duas execucoes"


def test_pipeline_nao_altera_fontes():
    antes = {nome: _md5(ROOT / nome) for nome in FONTES}
    build_all(ROOT)
    depois = {nome: _md5(ROOT / nome) for nome in FONTES}
    assert antes == depois
    assert len(pd.read_csv(ROOT / "vendas.csv")) == 423
    assert len(pd.read_csv(ROOT / "lojas.csv")) == 8


def test_pipeline_roda_como_script():
    resultado = subprocess.run(
        [sys.executable, "pipeline/build.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "Vendas no join (inner): 420" in resultado.stdout
    assert "index.html gerado" in resultado.stdout
