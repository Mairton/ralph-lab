import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from pipeline.build import build_html, build_join, build_pivot

ROOT = Path(__file__).resolve().parents[1]
MESES_ESPERADOS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
REGIOES_ESPERADAS = ["Centro-Oeste", "Nordeste", "Sudeste", "Sul"]


class _ExtratorTexto(HTMLParser):
    """Extrai o texto de dentro do elemento com o id pedido."""

    def __init__(self, id_alvo: str) -> None:
        super().__init__()
        self.id_alvo = id_alvo
        self.dentro = False
        self.profundidade = 0
        self.texto: list[str] = []

    def handle_starttag(self, tag, attrs):
        if self.dentro:
            self.profundidade += 1
        elif dict(attrs).get("id") == self.id_alvo:
            self.dentro = True

    def handle_endtag(self, tag):
        if self.dentro:
            if self.profundidade == 0:
                self.dentro = False
            else:
                self.profundidade -= 1

    def handle_data(self, data):
        if self.dentro:
            self.texto.append(data)


def _texto_do_elemento(html: str, id_alvo: str) -> str:
    parser = _ExtratorTexto(id_alvo)
    parser.feed(html)
    return "".join(parser.texto).strip()


@pytest.fixture(scope="module")
def html() -> str:
    build_join(ROOT)
    build_pivot(ROOT)
    build_html(ROOT)
    return (ROOT / "index.html").read_text(encoding="utf-8")


def test_html_tem_grafico(html):
    assert "<canvas" in html or "<svg" in html
    assert 'id="grafico"' in html
    assert '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>' in html


def test_html_conclusao_300_chars(html):
    texto = _texto_do_elemento(html, "conclusao")
    assert len(texto) >= 300


def test_html_conclusao_cita_numeros_e_excluidos(html):
    texto = _texto_do_elemento(html, "conclusao")
    assert "R$ 931.274,06" in texto
    assert "Sudeste" in texto and "R$ 265.077,49" in texto
    assert "id_loja=999" in texto
    assert "loja 108" in texto and "Batel/PR" in texto
    assert "inner join" in texto


def test_html_dados_embutidos_linhas_por_regiao(html):
    assert "fetch(" not in html
    match = re.search(r'<script id="dados-pivot" type="application/json">(.*?)</script>', html, re.S)
    assert match is not None
    dados = json.loads(match.group(1))
    assert dados["labels"] == MESES_ESPERADOS
    assert [d["label"] for d in dados["datasets"]] == REGIOES_ESPERADAS
    assert all(len(d["data"]) == len(MESES_ESPERADOS) for d in dados["datasets"])
    assert 'type: "line"' in html


def test_html_estrutura_basica(html):
    assert '<meta charset="utf-8">' in html
    assert "<h1>" in html
    assert "<table" in html
    for regiao in REGIOES_ESPERADAS:
        assert regiao in html


def test_html_conclusao_e_unico_p(html):
    # O validador externo pode ler o primeiro <p> da pagina: ele deve ser a conclusao.
    aberturas = re.findall(r"<p[^>]*>", html)
    assert len(aberturas) == 1
    assert 'id="conclusao"' in aberturas[0]
    assert html.count("<p") == 1
