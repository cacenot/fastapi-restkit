# LLM Guide (FastAPI RestKit)

Este documento existe para ajudar LLMs (e pessoas) a entender rapidamente o `fastapi-restkit`, gerar mudanças consistentes e evitar decisões que quebram performance/compatibilidade.

> Objetivo: orientar contribuições e uso correto da API pública, com exemplos canônicos e regras de precedência.

## 1) O que é essa lib?

`fastapi-restkit` fornece utilitários reutilizáveis para endpoints de listagem em FastAPI com SQLModel/SQLAlchemy:

- paginação (`PaginationParams`, `PaginatedResponse`)
- filtros declarativos (`FilterSet` + `filter_as_query`)
- ordenação declarativa (`SortingSet` + `sorting_as_query`)
- projeção / expansão (no momento, acoplado ao `FilterSet`): `expand`, `omit`, `only`

## 2) API pública (conceitual)

- `PaginationParams`: calcula `offset`/`limit`
- `PaginatedResponse.create(items, total, pagination)`: monta metadados
- `FilterSet`:
  - `to_sqlalchemy(Model) -> list[ColumnElement]`
  - `apply_to_query(query, Model) -> query`
  - `apply_expands_to_query(query, Model) -> query` (eager loading + projeção de colunas)
- `filter_as_query(FilterSetSubclass)`: gera dependency para query params + OpenAPI
- `SortingSet`:
  - `to_sqlalchemy(Model) -> list[ColumnElement]`
  - `apply_to_query(query, Model) -> query`
- `sorting_as_query(SortingSetSubclass)`: gera dependency para query params + OpenAPI

## 3) Projection / Expansion no FilterSet

O `FilterSet` expõe 3 parâmetros de query:

- `expand`: relacionamentos a serem carregados via eager loading
- `omit`: remove relacionamentos e/ou colunas (quando configuradas)
- `only`: whitelist de relacionamentos e/ou colunas

Essas features são **configuradas no backend** via `FilterSet.Config`.

### 3.1 Configuração: relacionamentos (expand)

No `FilterSet.Config`:

- `expandable: dict[str, str]`
  - mapeia `api_name -> relationship_path` (aceita dot path, ex.: `owner.company`)
- `default_expand: set[str] | list[str]`
  - relações expandidas por default (sem `?expand=`)
- `default_joined: set[str] | list[str]`
  - allowlist para `joinedload`
- `expand_all: bool`
  - expande tudo em `expandable` por default (use com cuidado)

Estratégia:

- `selectinload` é o padrão (seguro para paginação e 1:N)
- `joinedload` só ocorre se a relação estiver em `default_joined`

### 3.2 Configuração: colunas (omit/only)

No `FilterSet.Config`:

- `column_fields: dict[str, str]`
  - mapeia `api_name -> column_path` (normalmente o próprio nome da coluna)
- `column_omit_mode: Literal["defer", "load_only"]`
  - `defer` (default): adia colunas omitidas
  - `load_only`: carrega apenas colunas não omitidas (considerando somente `column_fields`)

Observações:

- `only` para colunas sempre gera `load_only(...)` (whitelist explícita)
- omitir colunas pode causar lazy-load se o schema acessar campo omitido

### 3.3 Regras de precedência (importante)

1) `only` tem precedência sobre `expand` e `omit`
2) `omit` remove itens de `default_expand` e do `expand` da request
3) `expand_all=True` define base de expansão como todos os `expandable`, ainda respeitando `omit` e `only`

## 4) Exemplo canônico de endpoint

```python
from fastapi import Depends
from sqlmodel import Session, select
from fastapi_restkit.filterset import filter_as_query
from fastapi_restkit.sortingset import sorting_as_query
from fastapi_restkit import PaginationParams, PaginatedResponse


@router.get("/products", response_model=PaginatedResponse[ProductRead])
async def list_products(
    session: Session = Depends(get_session),
    filters: ProductFilterSet = Depends(filter_as_query(ProductFilterSet)),
    sorting: ProductSortingSet = Depends(sorting_as_query(ProductSortingSet)),
    pagination: PaginationParams = Depends(),
):
    query = select(Product)
    query = filters.apply_to_query(query, Product)
    query = filters.apply_expands_to_query(query, Product)
    query = sorting.apply_to_query(query, Product)

    # Execução e total variam por projeto; aqui é propositalmente explícito.
    items = session.exec(query.offset(pagination.offset).limit(pagination.limit)).all()

    # Conte corretamente o total (atenção se seu query tiver joins)
    total = session.exec(
        select(func.count()).select_from(Product)  # ou subquery se necessário
    ).one()

    return PaginatedResponse.create(items=items, total=total, pagination=pagination)
```

## 5) Pitfalls comuns (SQLAlchemy/SQLModel)

- `joinedload` em coleções (1:N / N:N) pode explodir linhas e quebrar paginação.
- `selectinload` é geralmente mais seguro e previsível para listas.
- `COUNT(*)` em queries com joins pode contar linhas duplicadas; considere `distinct`, subquery, ou count em entidade base.
- Em async, lazy loading pode falhar (ou virar custo oculto). Evite schemas que exigem campos não carregados.

## 6) Padrões de contribuição (para mudanças futuras)

- Mantenha as mudanças **pequenas e focadas**.
- Priorize compatibilidade retroativa: adicionar parâmetros é ok; renomear/remover é breaking.
- Atualize:
  - docstrings (classes/métodos públicos)
  - `README.md` (se for feature pública)
  - docs em `docs/` (guia detalhado)
  - testes em `tests/`

## 7) Onde mexer

- `src/fastapi_restkit/filterset.py`: filtros + expand/omit/only + dependency generator
- `src/fastapi_restkit/sortingset.py`: sorting declarativo + dependency generator
- `src/fastapi_restkit/models.py`: paginação params
- `src/fastapi_restkit/pagination.py`: `PaginatedResponse`
- `docs/FILTERS_AND_SORTING.md`: guia detalhado

## 8) Checklist rápido para LLMs

Antes de propor mudanças:

- A feature altera API pública?
- Quebra OpenAPI? (descrições, exemplos, aliases)
- Interage com `sqlalchemy.orm` options? (eager loading, load_only/defer)
- Tem testes cobrindo: validação, precedência, casos inválidos?

Após implementar:

- Rodar testes: `python -m pytest -q`
- Checar warnings relevantes (especialmente erros, não apenas deprecações)
