# Filters e Sorting - Guia Completo

Este guia mostra como criar e usar filtros e ordenação no FastAPI RestKit, tanto no código Python quanto nas URLs de requisição.

## Índice

- [Filtros](#filtros)
  - [Tipos de Filtros Disponíveis](#tipos-de-filtros-disponíveis)
  - [Criando um FilterSet](#criando-um-filterset)
  - [Usando Filtros no Endpoint](#usando-filtros-no-endpoint)
  - [Parâmetros de URL para Filtros](#parâmetros-de-url-para-filtros)
- [Sorting (Ordenação)](#sorting-ordenação)
  - [Criando um SortingSet](#criando-um-sortingset)
  - [Usando Sorting no Endpoint](#usando-sorting-no-endpoint)
  - [Parâmetros de URL para Sorting](#parâmetros-de-url-para-sorting)
- [Combinando Filtros e Sorting](#combinando-filtros-e-sorting)
- [Exemplos Completos](#exemplos-completos)

---

## Filtros

### Tipos de Filtros Disponíveis

| Filtro | Descrição | Tipo de Valor | Exemplo de URL |
|--------|-----------|---------------|----------------|
| `SearchFilter` | Busca de texto (case-insensitive por padrão) | `str` | `?name=João` |
| `BooleanFilter` | Filtro booleano | `bool` | `?is_active=true` |
| `NumberFilter` | Filtro numérico com comparações | `float` | `?price=99.99` |
| `ListFilter[T]` | Lista de valores (IN clause) | `list` | `?status=active&status=pending` |
| `DateFilter` | Filtro de data | `date` | `?created_at=2024-01-15` |
| `DateRangeFilter` | Range de datas (min/max) | `date` | `?created_at[min]=2024-01-01&created_at[max]=2024-12-31` |
| `DateFromToRangeFilter` | Range de datas (from/to) | `date` | `?period[from]=2024-01-01&period[to]=2024-12-31` |
| `DateTimeFilter` | Filtro de datetime | `datetime` | `?updated_at=2024-01-15T10:30:00Z` |
| `DateTimeFromToRangeFilter` | Range de datetime | `datetime` | `?period[from]=2024-01-15T00:00:00&period[to]=2024-01-15T23:59:59` |
| `NumericRangeFilter` | Range numérico | `float` | `?price[min]=10&price[max]=100` |
| `TimeRangeFilter` | Range de horário | `time` | `?work_hours[min]=08:00:00&work_hours[max]=17:00:00` |

### Lookup Types (Operadores de Comparação)

Para filtros que suportam lookup, você pode usar os seguintes operadores:

| Lookup | Descrição | Exemplo SQL |
|--------|-----------|-------------|
| `exact` | Igual (padrão) | `column = 'value'` |
| `iexact` | Igual (case-insensitive) | `column ILIKE 'value'` |
| `contains` | Contém | `column LIKE '%value%'` |
| `icontains` | Contém (case-insensitive) | `column ILIKE '%value%'` |
| `startswith` | Começa com | `column LIKE 'value%'` |
| `istartswith` | Começa com (case-insensitive) | `column ILIKE 'value%'` |
| `endswith` | Termina com | `column LIKE '%value'` |
| `iendswith` | Termina com (case-insensitive) | `column ILIKE '%value'` |
| `gt` | Maior que | `column > value` |
| `gte` | Maior ou igual | `column >= value` |
| `lt` | Menor que | `column < value` |
| `lte` | Menor ou igual | `column <= value` |
| `isnull` | É nulo | `column IS NULL` ou `column IS NOT NULL` |

---

### Criando um FilterSet

#### Exemplo Básico

```python
from typing import Optional
from pydantic import Field
from fastapi_restkit.filterset import FilterSet
from fastapi_restkit.filters import (
    SearchFilter,
    BooleanFilter,
    ListFilter,
    NumberFilter,
    DateRangeFilter,
)


class ProductFilterSet(FilterSet):
    """Filtros para produtos."""
    
    # Filtro de busca por nome (auto-mapeado para coluna 'name')
    name: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Buscar por nome do produto"
    )
    
    # Filtro booleano
    is_active: Optional[BooleanFilter] = Field(
        default_factory=BooleanFilter,
        description="Filtrar por status ativo"
    )
    
    # Filtro de lista (IN clause)
    category: Optional[ListFilter[str]] = Field(
        default_factory=ListFilter,
        description="Filtrar por categorias"
    )
    
    # Filtro numérico
    price: Optional[NumberFilter] = Field(
        default_factory=NumberFilter,
        description="Filtrar por preço"
    )
    
    # Range de datas
    created_at: Optional[DateRangeFilter] = Field(
        default_factory=DateRangeFilter,
        description="Filtrar por data de criação"
    )
```

#### Mapeamento de Colunas Personalizado

Quando o nome do campo é diferente do nome da coluna no banco, ou quando você quer buscar em múltiplas colunas:

```python
class UserFilterSet(FilterSet):
    """Filtros para usuários."""
    
    # Busca em múltiplas colunas (OR)
    search: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Buscar em nome, email ou username"
    )
    
    # Campo com nome diferente da coluna
    active: Optional[BooleanFilter] = Field(
        default_factory=BooleanFilter,
        description="Usuário ativo"
    )
    
    email: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Buscar por email"
    )

    class Config:
        # Mapeamento personalizado
        field_columns = {
            # Busca OR em múltiplas colunas
            "search": ["name", "email", "username"],
            # Mapeia 'active' para coluna 'is_active'
            "active": "is_active",
            # 'email' não precisa mapear - auto-mapeado!
        }
```

---

### Usando Filtros no Endpoint

#### Com Dependency Injection (Recomendado)

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from fastapi_restkit.filterset import filter_as_query

router = APIRouter()


@router.get("/products")
async def list_products(
    session: Session = Depends(get_session),
    filters: ProductFilterSet = Depends(filter_as_query(ProductFilterSet)),
):
    """Lista produtos com filtros via query params."""
    
    # Cria query base
    query = select(Product)
    
    # Aplica filtros (retorna condições AND por padrão)
    conditions = filters.to_sqlalchemy(Product)
    if conditions:
        query = query.where(*conditions)
    
    # Ou use o método auxiliar
    # query = filters.apply_to_query(query, Product)
    
    result = session.exec(query)
    return result.all()
```

#### Uso Manual (Sem Dependency)

```python
from fastapi_restkit.filters import SearchFilter, ListFilter, BooleanFilter


@router.get("/products/manual")
async def list_products_manual(
    session: Session = Depends(get_session),
    name: str | None = None,
    categories: list[str] | None = None,
    is_active: bool | None = None,
):
    """Lista produtos com filtros manuais."""
    
    # Cria FilterSet manualmente
    filters = ProductFilterSet(
        name=SearchFilter(value=name) if name else None,
        category=ListFilter(values=categories) if categories else None,
        is_active=BooleanFilter(value=is_active) if is_active is not None else None,
    )
    
    query = select(Product)
    query = filters.apply_to_query(query, Product)
    
    result = session.exec(query)
    return result.all()
```

---

### Parâmetros de URL para Filtros

#### SearchFilter

```bash
# Busca simples (case-insensitive contains por padrão)
GET /products?name=laptop

# Com lookup personalizado
GET /products?name=laptop&name[lookup]=exact
GET /products?name=lap&name[lookup]=startswith
```

#### BooleanFilter

```bash
# Booleanos
GET /products?is_active=true
GET /products?is_active=false
```

#### ListFilter (IN clause)

```bash
# Lista de valores (usando múltiplos parâmetros com mesmo nome)
GET /products?category=electronics&category=computers&category=accessories

# Resulta em: WHERE category IN ('electronics', 'computers', 'accessories')
```

#### NumberFilter

```bash
# Valor exato
GET /products?price=99.99

# Com comparações
GET /products?price=100&price[lookup]=gte    # >= 100
GET /products?price=50&price[lookup]=lt      # < 50
```

#### DateRangeFilter

```bash
# Range com min e max
GET /products?created_at[min]=2024-01-01&created_at[max]=2024-12-31

# Apenas mínimo
GET /products?created_at[min]=2024-06-01

# Apenas máximo
GET /products?created_at[max]=2024-06-30
```

#### DateFromToRangeFilter

```bash
# Range com from e to
GET /products?period[from]=2024-01-01&period[to]=2024-12-31
```

#### DateTimeFromToRangeFilter

```bash
# Range de datetime
GET /logs?timestamp[from]=2024-01-15T00:00:00Z&timestamp[to]=2024-01-15T23:59:59Z

# Com timezone
GET /logs?timestamp[from]=2024-01-15T00:00:00-03:00&timestamp[to]=2024-01-15T23:59:59-03:00
```

#### NumericRangeFilter

```bash
# Range numérico
GET /products?price[min]=10&price[max]=100
```

---

## Sorting (Ordenação)

### Criando um SortingSet

```python
from pydantic import Field
from fastapi_restkit.sortingset import SortingSet, SortableField


class ProductSortingSet(SortingSet):
    """Ordenação para produtos."""
    
    # Campos ordenáveis
    id: SortableField = SortableField(description="ID do produto")
    name: SortableField = SortableField(description="Nome do produto")
    price: SortableField = SortableField(description="Preço")
    created_at: SortableField = SortableField(description="Data de criação")
    
    # Campo com mapeamento para coluna diferente
    updated: SortableField = SortableField(
        description="Data de atualização",
        column="updated_at",  # Mapeia para coluna 'updated_at'
    )

    class Config:
        # Ordenação padrão quando nenhuma é especificada
        default_sorting = ["created_at:desc"]
```

---

### Usando Sorting no Endpoint

#### Com Dependency Injection (Recomendado)

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from fastapi_restkit.sortingset import sorting_as_query

router = APIRouter()


@router.get("/products")
async def list_products(
    session: Session = Depends(get_session),
    sorting: ProductSortingSet = Depends(sorting_as_query(ProductSortingSet)),
):
    """Lista produtos com ordenação via query params."""
    
    query = select(Product)
    
    # Aplica ordenação
    order_by = sorting.to_sqlalchemy(Product)
    if order_by:
        query = query.order_by(*order_by)
    
    # Ou use o método auxiliar
    # query = sorting.apply_to_query(query, Product)
    
    result = session.exec(query)
    return result.all()
```

---

### Parâmetros de URL para Sorting

#### Formato Básico

```bash
# Ordenação ascendente (padrão)
GET /products?sort_by=name

# Ordenação descendente
GET /products?sort_by=name:desc

# Ordenação ascendente explícita
GET /products?sort_by=name:asc
```

#### Múltiplos Campos

```bash
# Ordenar por múltiplos campos
GET /products?sort_by=category:asc&sort_by=name:asc

# Ou
GET /products?sort_by=created_at:desc&sort_by=name:asc

# Resulta em: ORDER BY created_at DESC, name ASC
```

#### Exemplos Práticos

```bash
# Produtos mais recentes primeiro
GET /products?sort_by=created_at:desc

# Produtos mais baratos primeiro
GET /products?sort_by=price:asc

# Por categoria (A-Z) e depois por preço (menor primeiro)
GET /products?sort_by=category:asc&sort_by=price:asc

# Por popularidade (desc) e depois por nome (A-Z)
GET /products?sort_by=views:desc&sort_by=name:asc
```

---

## Combinando Filtros e Sorting

### Exemplo Completo no Endpoint

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from fastapi_restkit.filterset import filter_as_query
from fastapi_restkit.sortingset import sorting_as_query
from fastapi_restkit.pagination import PaginationParams, paginate


router = APIRouter()


@router.get("/products")
async def list_products(
    session: Session = Depends(get_session),
    filters: ProductFilterSet = Depends(filter_as_query(ProductFilterSet)),
    sorting: ProductSortingSet = Depends(sorting_as_query(ProductSortingSet)),
    pagination: PaginationParams = Depends(),
):
    """Lista produtos com filtros, ordenação e paginação."""
    
    # Query base
    query = select(Product)
    
    # Aplica filtros
    query = filters.apply_to_query(query, Product)
    
    # Aplica ordenação
    query = sorting.apply_to_query(query, Product)
    
    # Aplica paginação e retorna
    return await paginate(session, query, pagination)
```

### Exemplo de URL Combinada

```bash
# Buscar produtos ativos, categoria "electronics", 
# preço entre 100 e 500, ordenado por preço ascendente
GET /products?is_active=true&category=electronics&price[min]=100&price[max]=500&sort_by=price:asc

# Buscar usuários com "silva" no nome ou email,
# criados em 2024, ordenados por data de criação desc
GET /users?search=silva&created_at[min]=2024-01-01&created_at[max]=2024-12-31&sort_by=created_at:desc

# Paginação combinada
GET /products?is_active=true&sort_by=created_at:desc&page=1&page_size=20
```

---

## Exemplos Completos

### Modelo SQLModel

```python
from datetime import datetime
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class Product(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: str | None = None
    price: float
    category: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### FilterSet Completo

```python
from typing import Optional
from pydantic import Field
from fastapi_restkit.filterset import FilterSet
from fastapi_restkit.filters import (
    SearchFilter,
    BooleanFilter,
    ListFilter,
    NumericRangeFilter,
    DateRangeFilter,
)


class ProductFilterSet(FilterSet):
    """Filtros completos para produtos."""
    
    # Busca geral (nome + descrição)
    search: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Buscar em nome e descrição"
    )
    
    # Filtro por nome específico
    name: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Buscar por nome"
    )
    
    # Filtro por status
    is_active: Optional[BooleanFilter] = Field(
        default_factory=BooleanFilter,
        description="Produto ativo"
    )
    
    # Filtro por categorias
    category: Optional[ListFilter[str]] = Field(
        default_factory=ListFilter,
        description="Categorias do produto"
    )
    
    # Range de preço
    price: Optional[NumericRangeFilter] = Field(
        default_factory=NumericRangeFilter,
        description="Faixa de preço"
    )
    
    # Range de data de criação
    created_at: Optional[DateRangeFilter] = Field(
        default_factory=DateRangeFilter,
        description="Data de criação"
    )

    class Config:
        field_columns = {
            "search": ["name", "description"],  # Busca OR em múltiplas colunas
        }
```

### SortingSet Completo

```python
from fastapi_restkit.sortingset import SortingSet, SortableField


class ProductSortingSet(SortingSet):
    """Ordenação para produtos."""
    
    id: SortableField = SortableField(description="ID")
    name: SortableField = SortableField(description="Nome")
    price: SortableField = SortableField(description="Preço")
    category: SortableField = SortableField(description="Categoria")
    created_at: SortableField = SortableField(description="Data de criação")
    updated_at: SortableField = SortableField(description="Data de atualização")

    class Config:
        default_sorting = ["created_at:desc"]
```

### Endpoint Completo

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from fastapi_restkit.filterset import filter_as_query
from fastapi_restkit.sortingset import sorting_as_query
from fastapi_restkit.pagination import PaginationParams, paginate, PaginatedResponse


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse[ProductRead])
async def list_products(
    session: Session = Depends(get_session),
    filters: ProductFilterSet = Depends(filter_as_query(ProductFilterSet)),
    sorting: ProductSortingSet = Depends(sorting_as_query(ProductSortingSet)),
    pagination: PaginationParams = Depends(),
):
    """
    Lista produtos com suporte a:
    
    - **Filtros**: name, search, is_active, category, price, created_at
    - **Ordenação**: id, name, price, category, created_at, updated_at
    - **Paginação**: page, page_size
    
    ## Exemplos de URL
    
    - `GET /products?is_active=true&sort_by=price:asc`
    - `GET /products?category=electronics&price[min]=100&price[max]=500`
    - `GET /products?search=laptop&sort_by=created_at:desc&page=1&page_size=10`
    """
    query = select(Product)
    query = filters.apply_to_query(query, Product)
    query = sorting.apply_to_query(query, Product)
    
    return await paginate(session, query, pagination)
```

### URLs de Exemplo

```bash
# Listar todos produtos ativos
GET /products?is_active=true

# Buscar "laptop" em nome ou descrição
GET /products?search=laptop

# Filtrar por categoria
GET /products?category=electronics
GET /products?category=electronics&category=computers

# Filtrar por faixa de preço
GET /products?price[min]=100&price[max]=500

# Filtrar por data de criação
GET /products?created_at[min]=2024-01-01&created_at[max]=2024-06-30

# Ordenar por preço crescente
GET /products?sort_by=price:asc

# Ordenar por múltiplos campos
GET /products?sort_by=category:asc&sort_by=price:desc

# Combinar tudo
GET /products?is_active=true&category=electronics&price[min]=100&sort_by=price:asc&page=1&page_size=20
```

---

## Dicas e Boas Práticas

1. **Use `filter_as_query` e `sorting_as_query`** para gerar automaticamente a documentação OpenAPI dos parâmetros.

2. **Campos auto-mapeados**: Se o nome do campo no FilterSet é igual ao nome da coluna no modelo, não precisa configurar `field_columns`.

3. **Busca em múltiplas colunas**: Use `field_columns` com lista para buscar em várias colunas com OR.

4. **Ordenação padrão**: Configure `default_sorting` no `Config` do SortingSet para ter uma ordenação padrão.

5. **Validação automática**: Os filtros validam automaticamente os tipos e formatos (datas, números, etc.).

6. **Combine com paginação**: Use junto com `PaginationParams` para endpoints completos de listagem.

7. **Tratamento de erros**: Os filtros lançam `InvalidFormatError` para valores inválidos - trate-os adequadamente.
