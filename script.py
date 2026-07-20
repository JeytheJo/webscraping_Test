import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "http://books.toscrape.com/catalogue/page-{}.html"

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}

def pegar_livros_da_pagina(pagina):
    url = BASE_URL.format(pagina)
    resp = requests.get(url)
    resp.encoding = "utf-8"  # sem isso o £ vira "Â£" e quebra o float()

    if resp.status_code != 200:
        print(f"pagina {pagina} nao existe, parando")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    livros = soup.find_all("article", class_="product_pod")

    dados = []
    for livro in livros:
        titulo = livro.h3.a["title"]

        preco_texto = livro.find("p", class_="price_color").text
        preco = float(preco_texto.replace("£", ""))

        estrela = livro.p["class"][1] 
        avaliacao = RATING_MAP.get(estrela, 0)

        disponibilidade = livro.find("p", class_="instock availability").text.strip()

        dados.append({
            "titulo": titulo,
            "preco": preco,
            "avaliacao": avaliacao,
            "disponibilidade": disponibilidade,
        })

    return dados


def main():
    todos_livros = []

    # por enquanto so pega as 3 primeiras paginas pra nao demorar muito
    for pagina in range(1, 4):
        print(f"coletando pagina {pagina}...")
        dados = pegar_livros_da_pagina(pagina)

        if dados is None:
            break

        todos_livros.extend(dados)
        time.sleep(1)  # pra nao martelar o site

    df = pd.DataFrame(todos_livros)
    df.to_csv("livros.csv", index=False)

    print(f"pronto! {len(df)} livros salvos em livros.csv")


if __name__ == "__main__":
    main()