# 📚 Book Scraper — Web Scraping & Data Mining

![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-HTML%20Parsing-4B8BBE?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?style=for-the-badge&logo=pandas&logoColor=white)
![OpenPyXL](https://img.shields.io/badge/OpenPyXL-Excel%20Export-217346?style=for-the-badge&logo=microsoftexcel&logoColor=white)
![Status](https://img.shields.io/badge/Status-Ambiente%20de%20Teste-orange?style=for-the-badge)

> ⚠️ **Aviso importante**
> Este projeto foi desenvolvido **exclusivamente em ambiente controlado, para fins didáticos e de teste**. O alvo utilizado é o [books.toscrape.com](http://books.toscrape.com), um site público **criado propositalmente para treino de web scraping**, sem dados reais, sem autenticação e sem restrições de acesso. Nenhuma técnica aqui foi aplicada contra sistemas de terceiros sem autorização. Antes de aplicar scraping em qualquer outro site, sempre verifique o `robots.txt`, os Termos de Uso e a legislação aplicável (como a LGPD, no caso de dados pessoais).

---

## 📖 Sobre o projeto

Script de automação em Python que **coleta, estrutura e analisa dados** do catálogo de um site de livros, exportando o resultado para CSV e Excel. Foi construído como material de estudo sobre as técnicas mais comuns de **Web Scraping** e **Data Mining** aplicadas no mundo real.

---

## 🧠 Conceitos

### O que é Web Scraping?

Web Scraping é o processo de **extrair dados de páginas web de forma automatizada**, simulando o comportamento de um navegador (fazendo requisições HTTP) e depois interpretando o HTML retornado para localizar as informações desejadas. Em vez de copiar e colar manualmente, um script faz isso em escala, de forma repetível e rápida.

De forma resumida, o processo passa por três etapas:

1. **Requisição** — o script pede a página ao servidor (`GET`), como um navegador faria;
2. **Parsing** — o HTML bruto (texto) é transformado em uma árvore de elementos navegável, permitindo localizar tags, classes e atributos específicos;
3. **Extração** — os dados de interesse (texto, atributos, links) são retirados dessa árvore e organizados em uma estrutura (listas, dicionários, DataFrames).

### O que é Data Mining?

Data Mining (mineração de dados) é a etapa **posterior** à coleta: depois que os dados brutos estão organizados, o objetivo é **encontrar padrões, tendências e relações** que não são óbvias olhando os dados individualmente. Isso costuma envolver agregações, estatísticas descritivas, agrupamentos e comparações.

No projeto, isso aparece na função `gerar_resumo()`, que agrupa os livros por categoria e calcula:
- Quantidade de livros por categoria;
- Preço médio, mínimo e máximo;
- Avaliação média.

Ou seja: o scraping resolve o "como coletar", e o data mining resolve o "o que esses dados me dizem".

---

## ⚙️ Como o código funciona

O script segue um fluxo linear, dividido em responsabilidades bem definidas:

```
scrape_catalog()  →  scrape_book()  →  DataFrame  →  gerar_resumo()  →  exportar()
   (lista de URLs)   (dados de cada    (pandas)      (estatísticas)     (CSV/Excel)
                       livro)
```

### 1. `BookScraper.scrape_catalog()`
Percorre as páginas paginadas do catálogo (`/catalogue/page-N.html`), seguindo o link "next" até não existir mais próxima página (ou até atingir o limite definido em `--pages`). De cada página, extrai apenas os **links** para a página individual de cada livro — a coleta detalhada acontece depois, sob demanda.

### 2. `BookScraper.scrape_book()`
Para cada link coletado, o script visita a página do produto e extrai:
- Título, preço, avaliação (1 a 5 estrelas) e disponibilidade;
- Categoria (via breadcrumb de navegação);
- UPC, preço com/sem imposto, número de avaliações e descrição (via tabela de especificações).

Os dados são organizados numa `dataclass` (`Book`), o que documenta explicitamente o "formato" de um livro no sistema — deixando claro quais campos existem e seus tipos.

### 3. `gerar_resumo()`
Recebe o DataFrame completo e aplica um `groupby("categoria")` com agregações (`mean`, `min`, `max`, `count`) — a parte de data mining do projeto.

### 4. `exportar()`
Grava os dados brutos e o resumo em disco, em CSV (`utf-8-sig`, para evitar problemas de acentuação no Excel) e/ou em uma planilha Excel com duas abas (`Dados` e `Resumo por Categoria`), usando `pandas.ExcelWriter`.

---

## 🛠️ Estratégias utilizadas

| Estratégia | Onde | Por quê |
|---|---|---|
| **Reutilização de sessão HTTP** (`requests.Session()`) | `BookScraper.__init__` | Reaproveita a conexão TCP entre requisições, reduzindo overhead |
| **User-Agent customizado** | `HEADERS` | Identifica o script de forma transparente, em vez de se passar por navegador |
| **Retry com backoff simples** | `_get()` | Se uma requisição falhar (timeout, erro 5xx), tenta novamente com espera crescente, em vez de derrubar o script |
| **Rate limiting (delay entre requisições)** | `time.sleep(self.delay)` | Evita sobrecarregar o servidor de destino — scraping ético |
| **Correção explícita de encoding** | `resp.encoding = "utf-8"` | Evita que caracteres especiais (como `£`) sejam interpretados errado e quebrem o parsing |
| **Separação entre "listar" e "detalhar"** | `scrape_catalog()` vs `scrape_book()` | Permite paginar rapidamente sem baixar todos os detalhes de uma vez, e reaproveitar cada função isoladamente |
| **Parsing resiliente com regex** | `_parse_preco()`, `_parse_disponibilidade()` | Extrai apenas os dígitos relevantes de strings formatadas (`"£51.77"`, `"In stock (22 available)"`), tolerando variações de texto |
| **Modelagem explícita de dados (`dataclass`)** | `Book` | Documenta o formato dos dados e evita dicionários soltos sem contrato definido |
| **Logging estruturado** | `logging` | Registra progresso e falhas com timestamp, mais adequado que `print()` para automações |
| **CLI configurável** | `argparse` | Permite ajustar páginas, delay e formato de saída sem editar o código |

---

## 📦 Instalação

```bash
git clone <url-do-repositorio>
cd book-scraper
pip install -r requirements.txt
```

## ▶️ Uso

```bash
# padrão: 5 páginas, delay de 0.5s, exporta CSV + Excel
python book_scraper.py

# customizando
python book_scraper.py --pages 10 --delay 1 --output excel --output-dir dados
```

| Argumento | Descrição | Padrão |
|---|---|---|
| `--pages` | Quantidade de páginas do catálogo a percorrer (`0` = todas, ~50) | `5` |
| `--delay` | Segundos de espera entre requisições | `0.5` |
| `--output` | Formato de saída: `csv`, `excel` ou `both` | `both` |
| `--output-dir` | Pasta onde os arquivos serão salvos | `./saida` |

---

## 📁 Estrutura de saída

```
saida/
├── livros.csv
└── livros.xlsx
    ├── Dados                    (dados brutos, um livro por linha)
    └── Resumo por Categoria     (estatísticas agregadas)
```

---

## 🎯 Objetivo do projeto

Este repositório serve como material de estudo/portfólio sobre:
- Fundamentos de requisições HTTP e parsing de HTML;
- Boas práticas de scraping responsável (rate limiting, retries, identificação via User-Agent);
- Organização e agregação de dados com `pandas`;
- Exportação de dados para formatos amplamente utilizados (CSV/Excel).

Sinta-se à vontade para adaptar o código para outros sites — sempre respeitando os Termos de Uso e o `robots.txt` de cada um.