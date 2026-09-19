"""Pipeline do CSV ao grafico.

Etapas:
    build_join(root)  -> vendas_lojas.csv (inner join de vendas.csv com lojas.csv por id_loja)
    build_pivot(root) -> pivot_receita.csv (receita somada por regiao x mes, YYYY-MM)
    build_html(root)  -> index.html (grafico de linhas Chart.js + tabela + conclusao)

Decisao de join: INNER. Vendas orfas (id_loja sem correspondencia em lojas.csv)
e lojas sem vendas ficam de fora do relatorio. Os CSVs de origem nunca sao alterados.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

VENDAS_CSV = "vendas.csv"
LOJAS_CSV = "lojas.csv"
VENDAS_LOJAS_CSV = "vendas_lojas.csv"
PIVOT_RECEITA_CSV = "pivot_receita.csv"
INDEX_HTML = "index.html"

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js"

# Paleta categorica (uma cor fixa por regiao, em ordem alfabetica): azul, laranja, verde-agua, amarelo.
CORES_SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


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


def formatar_brl(valor: float) -> str:
    """Formata um valor em reais no padrao brasileiro: R$ 931.274,06."""
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _tabela_html(pivot: pd.DataFrame) -> str:
    """Tabela HTML simples com o conteudo do pivot (regiao x mes) e a coluna Total."""
    cabecalho = "".join(f"<th scope=\"col\">{html.escape(str(c))}</th>" for c in pivot.columns)
    linhas = []
    for regiao, valores in pivot.iterrows():
        celulas = "".join(f"<td>{formatar_brl(v)}</td>" for v in valores)
        total = formatar_brl(float(valores.sum()))
        linhas.append(
            f"<tr><th scope=\"row\">{html.escape(str(regiao))}</th>{celulas}<td>{total}</td></tr>"
        )
    return (
        "<table id=\"tabela\">\n"
        "<caption>Receita por regiao e mes (R$)</caption>\n"
        f"<thead><tr><th scope=\"col\">Regiao</th>{cabecalho}<th scope=\"col\">Total</th></tr></thead>\n"
        "<tbody>\n" + "\n".join(linhas) + "\n</tbody>\n</table>"
    )


def _conclusao(pivot: pd.DataFrame, vendas: pd.DataFrame, lojas: pd.DataFrame) -> str:
    """Paragrafo de conclusao em portugues com os numeros do relatorio (calculados, nao digitados)."""
    total = float(pivot.to_numpy().sum())
    por_regiao = pivot.sum(axis=1).sort_values(ascending=False)
    lider = str(por_regiao.index[0])
    receita_lider = float(por_regiao.iloc[0])
    participacao = 100.0 * receita_lider / total
    lanterna = str(por_regiao.index[-1])
    receita_lanterna = float(por_regiao.iloc[-1])

    orfas = vendas[~vendas["id_loja"].isin(lojas["id_loja"])]
    ids_orfas = ", ".join(sorted(orfas["id_venda"].astype(str)))
    id_loja_orfas = ", ".join(str(i) for i in sorted(orfas["id_loja"].unique()))
    lojas_sem_vendas = lojas[~lojas["id_loja"].isin(vendas["id_loja"])]
    descricao_lojas = ", ".join(
        f"loja {row.id_loja} ({row.nome_loja}/{row.uf})" for row in lojas_sem_vendas.itertuples(index=False)
    )
    primeiro_mes, ultimo_mes = str(pivot.columns[0]), str(pivot.columns[-1])

    return (
        f"Entre {primeiro_mes} e {ultimo_mes}, as {len(pivot)} regioes somaram uma receita total de "
        f"{formatar_brl(total)} em {len(vendas) - len(orfas)} vendas. A regiao lider foi {lider}, com "
        f"{formatar_brl(receita_lider)} ({participacao:.1f}% do total), enquanto {lanterna} ficou em ultimo, "
        f"com {formatar_brl(receita_lanterna)}. O relatorio usa inner join por id_loja entre vendas.csv e "
        f"lojas.csv: por isso as {len(orfas)} vendas orfas ({ids_orfas}, id_loja={id_loja_orfas}, "
        f"{formatar_brl(float(orfas['receita_brl'].sum()))}) nao constam do relatorio, e a "
        f"{descricao_lojas}, que nao registrou nenhuma venda, tambem nao aparece no grafico nem na tabela. "
        f"Os arquivos de origem permanecem intactos; a receita bruta de vendas.csv e de "
        f"{formatar_brl(float(vendas['receita_brl'].sum()))}."
    )


def build_html(root: Path = ROOT) -> str:
    """Le pivot_receita.csv e grava index.html na raiz com grafico de linhas (Chart.js), tabela e conclusao.

    Os dados ficam embutidos no HTML (sem fetch em runtime): eixo X = meses do pivot,
    uma serie (dataset) por regiao. O resultado e deterministico (sem timestamps).
    """
    root = Path(root)
    pivot = pd.read_csv(root / PIVOT_RECEITA_CSV, index_col="regiao")
    vendas, lojas = _read_sources(root)

    meses = [str(c) for c in pivot.columns]
    datasets = [
        {
            "label": str(regiao),
            "data": [round(float(v), 2) for v in valores],
            "borderColor": CORES_SERIES[i % len(CORES_SERIES)],
            "backgroundColor": CORES_SERIES[i % len(CORES_SERIES)],
            "borderWidth": 2,
            "pointRadius": 4,
            "pointHoverRadius": 6,
            "tension": 0,
            "fill": False,
        }
        for i, (regiao, valores) in enumerate(pivot.iterrows())
    ]
    dados_json = json.dumps({"labels": meses, "datasets": datasets}, ensure_ascii=False)
    conclusao = html.escape(_conclusao(pivot, vendas, lojas))
    tabela = _tabela_html(pivot)

    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Receita mensal por regiao ({meses[0]} a {meses[-1]})</title>
<style>
  :root {{ color-scheme: light; --surface: #fcfcfb; --text: #0b0b0b; --text-2: #52514e; --grid: #e6e5e0; }}
  body {{ margin: 0; padding: 24px; background: var(--surface); color: var(--text);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 4px; }}
  .subtitulo {{ color: var(--text-2); margin: 0 0 16px; }}
  .grafico {{ position: relative; height: 420px; margin: 0 0 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0 0 24px; font-variant-numeric: tabular-nums; }}
  caption {{ text-align: left; color: var(--text-2); padding: 0 0 8px; }}
  th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--grid); text-align: right; }}
  th[scope="row"], thead th:first-child {{ text-align: left; }}
  #conclusao {{ max-width: 72ch; }}
</style>
</head>
<body>
<main>
<h1>Receita mensal por regiao</h1>
<p class="subtitulo">Fonte: vendas.csv e lojas.csv (inner join por id_loja), {meses[0]} a {meses[-1]}. Valores em R$.</p>
<div class="grafico"><canvas id="grafico" role="img" aria-label="Grafico de linhas da receita mensal por regiao"></canvas></div>
{tabela}
<p id="conclusao">{conclusao}</p>
</main>
<script src="{CHART_JS_CDN}"></script>
<script id="dados-pivot" type="application/json">{dados_json}</script>
<script>
(function () {{
  var dados = JSON.parse(document.getElementById("dados-pivot").textContent);
  var brl = new Intl.NumberFormat("pt-BR", {{ style: "currency", currency: "BRL" }});
  new Chart(document.getElementById("grafico"), {{
    type: "line",
    data: dados,
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      interaction: {{ mode: "index", intersect: false }},
      plugins: {{
        legend: {{ position: "top", labels: {{ color: "#0b0b0b", usePointStyle: true }} }},
        tooltip: {{ callbacks: {{ label: function (c) {{ return c.dataset.label + ": " + brl.format(c.parsed.y); }} }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: "Mes" }}, grid: {{ display: false }}, ticks: {{ color: "#52514e" }} }},
        y: {{ title: {{ display: true, text: "Receita (R$)" }}, beginAtZero: true,
              grid: {{ color: "#e6e5e0" }}, ticks: {{ color: "#52514e", callback: function (v) {{ return brl.format(v); }} }} }}
      }}
    }}
  }});
}})();
</script>
</body>
</html>
"""
    (root / INDEX_HTML).write_text(pagina, encoding="utf-8")
    print(f"index.html gerado: {len(datasets)} series x {len(meses)} meses; conclusao com {len(_conclusao(pivot, vendas, lojas))} caracteres")
    return pagina


def build_all(root: Path = ROOT) -> None:
    """Ponto de entrada unico: regenera os tres artefatos na raiz, em sequencia e de forma deterministica."""
    root = Path(root)
    build_join(root)
    build_pivot(root)
    build_html(root)


if __name__ == "__main__":
    build_all(ROOT)
