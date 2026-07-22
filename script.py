from __future__ import annotations
import argparse
import logging
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------- #

BASE_URL = "http://books.toscrape.com/"
CATALOGUE_URL = urljoin(BASE_URL, "catalogue/")
FIRST_PAGE = urljoin(CATALOGUE_URL, "page-1.html")

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

HEADERS = {
    "User-Agent": "BookScraperTeste/1.0 (https://books.toscrape.com)"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("book_scraper")


# Estrutura de dados
# --------------------------------------------------------------------------- #
@dataclass
class Book:
    titulo: str
    preco: float
    avaliacao_estrelas: int
    disponibilidade_qtd: Optional[int]
    categoria: Optional[str] = None
    upc: Optional[str] = None
    preco_sem_imposto: Optional[float] = None
    preco_com_imposto: Optional[float] = None
    imposto: Optional[float] = None
    numero_avaliacoes: Optional[int] = None
    descricao: Optional[str] = None
    url: Optional[str] = None

# Scraper
# --------------------------------------------------------------------------- #
class BookScraper:
    """Coleta dados do catálogo do site"""

    def __init__(self, delay: float = 0.5, max_retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        self.max_retries = max_retries

    # -- infra ------------------------------------------------- #
    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """Faz o GET de uma URL com retry simples e devolve o HTML parseado."""
        for tentativa in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, timeout=10)
                resp.raise_for_status()
                resp.encoding = "utf-8"  # senão o £ vira "Â£" e quebra o parse de preço
                return BeautifulSoup(resp.text, "lxml")
            except requests.RequestException as exc:
                logger.warning(
                    "Falha ao acessar %s (tentativa %d/%d): %s",
                    url, tentativa, self.max_retries, exc,
                )
                time.sleep(self.delay * tentativa)  # backoff simples
        logger.error("Desisti de %s após %d tentativas.", url, self.max_retries)
        return None

    # -- catálogo --------------------------------------------------------- #
    def scrape_catalog(self, max_pages: Optional[int] = None) -> list[str]:
        """Percorre as páginas do catálogo e devolve a URL de cada livro."""
        urls: list[str] = []
        page_url = FIRST_PAGE
        page_num = 1

        while page_url:
            if max_pages and page_num > max_pages:
                break

            logger.info("Lendo página %d do catálogo...", page_num)
            soup = self._get(page_url)
            if soup is None:
                break

            for artigo in soup.select("article.product_pod"):
                href = artigo.h3.a["href"]
                urls.append(urljoin(page_url, href))

            next_link = soup.select_one("li.next a")
            page_url = urljoin(page_url, next_link["href"]) if next_link else None
            page_num += 1
            time.sleep(self.delay)

        logger.info("Total de livros encontrados: %d", len(urls))
        return urls

    # -- página de detalhes ------------------------------------------------ #
    def scrape_book(self, url: str) -> Optional[Book]:
        """Extrai os dados de uma página individualmente."""
        soup = self._get(url)
        if soup is None:
            return None

        titulo = soup.h1.text.strip()

        preco_texto = soup.select_one("p.price_color").text
        preco = self._parse_preco(preco_texto)

        estrela_classe = soup.select_one("p.star-rating")["class"][1]
        avaliacao = RATING_MAP.get(estrela_classe, 0)

        breadcrumb = soup.select("ul.breadcrumb li a")
        categoria = breadcrumb[2].text.strip() if len(breadcrumb) >= 3 else None

        desc_tag = soup.select_one("#product_description")
        descricao = desc_tag.find_next_sibling("p").text.strip() if desc_tag else None

        tabela = {
            linha.th.text.strip(): linha.td.text.strip()
            for linha in soup.select("table.table-striped tr")
        }

        return Book(
            titulo=titulo,
            preco=preco,
            avaliacao_estrelas=avaliacao,
            disponibilidade_qtd=self._parse_disponibilidade(tabela.get("Availability")),
            categoria=categoria,
            upc=tabela.get("UPC"),
            preco_sem_imposto=self._parse_preco(tabela.get("Price (excl. tax)", "")),
            preco_com_imposto=self._parse_preco(tabela.get("Price (incl. tax)", "")),
            imposto=self._parse_preco(tabela.get("Tax", "")),
            numero_avaliacoes=int(tabela.get("Number of reviews", 0) or 0),
            descricao=descricao,
            url=url,
        )

    # -- helpers de parsing -------------------------------------------------- #
    @staticmethod
    def _parse_preco(texto: str) -> Optional[float]:
        if not texto:
            return None
        match = re.search(r"[\d.]+", texto)
        return float(match.group()) if match else None

    @staticmethod
    def _parse_disponibilidade(texto: Optional[str]) -> Optional[int]:
        if not texto:
            return None
        match = re.search(r"\((\d+)", texto)
        return int(match.group(1)) if match else 0

    # -- execução completa ---------------------------------------------------- #
    def run(self, max_pages: Optional[int] = None) -> pd.DataFrame:
        urls = self.scrape_catalog(max_pages=max_pages)

        livros: list[Book] = []
        for i, url in enumerate(urls, start=1):
            logger.info("Coletando livro %d/%d", i, len(urls))
            livro = self.scrape_book(url)
            if livro:
                livros.append(livro)
            time.sleep(self.delay)

        return pd.DataFrame([asdict(l) for l in livros])


# Data mining simples: estatísticas sobre os dados coletados
# --------------------------------------------------------------------------- #
def gerar_resumo(df: pd.DataFrame) -> pd.DataFrame:
    """gera estatísticas agregadas por categoria."""
    resumo = (
        df.groupby("categoria")
        .agg(
            qtd_livros=("titulo", "count"),
            preco_medio=("preco", "mean"),
            preco_min=("preco", "min"),
            preco_max=("preco", "max"),
            avaliacao_media=("avaliacao_estrelas", "mean"),
        )
        .round(2)
        .sort_values("qtd_livros", ascending=False)
        .reset_index()
    )
    return resumo


# Exportação
# --------------------------------------------------------------------------- #
def exportar(df: pd.DataFrame, resumo: pd.DataFrame, saida: Path, formato: str) -> None:
    saida.mkdir(parents=True, exist_ok=True)

    if formato in ("csv", "both"):
        caminho_csv = saida / "livros.csv"
        df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        logger.info("CSV salvo em %s", caminho_csv)

    if formato in ("excel", "both"):
        caminho_xlsx = saida / "livros.xlsx"
        with pd.ExcelWriter(caminho_xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Dados", index=False)
            resumo.to_excel(writer, sheet_name="Resumo por Categoria", index=False)
        logger.info("Excel salvo em %s", caminho_xlsx)


# CLI simples
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de exemplo para books.toscrape.com")
    parser.add_argument(
        "--pages", type=int, default=5,
        help="Número máximo de páginas do catálogo a percorrer (padrão: 5). Use 0 para todas (~50).",
    )
    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Segundos de espera entre requisições, para não sobrecarregar o site (padrão: 0.5)",
    )
    parser.add_argument(
        "--output", choices=["csv", "excel", "both"], default="both",
        help="Formato de saída (padrão: both)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("saida"),
        help="Diretório onde os arquivos serão salvos (padrão: ./saida)",
    )
    args = parser.parse_args()

    max_pages = None if args.pages == 0 else args.pages

    scraper = BookScraper(delay=args.delay)
    df = scraper.run(max_pages=max_pages)

    if df.empty:
        logger.error("Nenhum dado coletado. Encerrando.")
        return

    resumo = gerar_resumo(df)
    exportar(df, resumo, args.output_dir, args.output)

    logger.info("Concluído! %d livros coletados.", len(df))


if __name__ == "__main__":
    main()