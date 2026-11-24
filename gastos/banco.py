"""Acesso ao banco de dados SQLite e regras de negócio.

Os valores são guardados em centavos (número inteiro) para evitar os erros de
arredondamento que acontecem com números decimais (float).
"""

import re
import sqlite3
from datetime import date
from decimal import Decimal, InvalidOperation

TIPOS = ("despesa", "receita")

_PADRAO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def conectar(caminho: str = "gastos.db") -> sqlite3.Connection:
    """Abre (ou cria) o banco e garante que a tabela existe."""
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS lancamentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT    NOT NULL CHECK (tipo IN ('despesa', 'receita')),
            valor_centavos  INTEGER NOT NULL CHECK (valor_centavos > 0),
            descricao       TEXT    NOT NULL,
            categoria       TEXT    NOT NULL,
            data            TEXT    NOT NULL
        )
        """
    )
    conexao.commit()
    return conexao


def reais_para_centavos(texto) -> int:
    """Converte '10', '10,50' ou '10.5' em centavos. Lança ValueError se inválido."""
    try:
        valor = Decimal(str(texto).strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"Valor inválido: {texto!r}.") from None

    if not valor.is_finite() or valor <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    centavos = valor * 100
    if centavos != centavos.to_integral_value():
        raise ValueError("O valor deve ter no máximo 2 casas decimais.")
    return int(centavos)


def formatar_reais(centavos: int) -> str:
    """Formata centavos no padrão brasileiro: 123456 -> 'R$ 1.234,56'."""
    reais, resto = divmod(centavos, 100)
    return f"R$ {reais:,}".replace(",", ".") + f",{resto:02d}"


def validar_data(texto: str) -> str:
    """Confere se a data está no formato AAAA-MM-DD e devolve o texto padronizado."""
    try:
        return date.fromisoformat(texto).isoformat()
    except (ValueError, TypeError):
        raise ValueError(f"Data inválida: {texto!r}. Use o formato AAAA-MM-DD.") from None


def validar_mes(mes: str) -> str:
    if not isinstance(mes, str) or not _PADRAO_MES.match(mes):
        raise ValueError(f"Mês inválido: {mes!r}. Use o formato AAAA-MM.")
    return mes


def adicionar(conexao, valor, descricao, categoria="geral", tipo="despesa", data=None) -> int:
    """Registra um lançamento e devolve o id dele."""
    if tipo not in TIPOS:
        raise ValueError(f"Tipo inválido: {tipo!r}. Use 'despesa' ou 'receita'.")
    descricao = (descricao or "").strip()
    categoria = (categoria or "").strip().lower()
    if not descricao:
        raise ValueError("A descrição não pode ficar vazia.")
    if not categoria:
        raise ValueError("A categoria não pode ficar vazia.")

    centavos = reais_para_centavos(valor)
    data = validar_data(data) if data else date.today().isoformat()

    cursor = conexao.execute(
        "INSERT INTO lancamentos (tipo, valor_centavos, descricao, categoria, data) "
        "VALUES (?, ?, ?, ?, ?)",
        (tipo, centavos, descricao, categoria, data),
    )
    conexao.commit()
    return cursor.lastrowid


def listar(conexao, mes=None, categoria=None) -> list:
    """Lista os lançamentos, do mais antigo para o mais novo, com filtros opcionais."""
    consulta = "SELECT * FROM lancamentos WHERE 1 = 1"
    parametros = []
    if mes:
        consulta += " AND substr(data, 1, 7) = ?"
        parametros.append(validar_mes(mes))
    if categoria:
        consulta += " AND categoria = ?"
        parametros.append(categoria.strip().lower())
    consulta += " ORDER BY data, id"
    return conexao.execute(consulta, parametros).fetchall()


def remover(conexao, id_lancamento: int) -> bool:
    """Apaga um lançamento. Devolve False se o id não existe."""
    cursor = conexao.execute("DELETE FROM lancamentos WHERE id = ?", (id_lancamento,))
    conexao.commit()
    return cursor.rowcount > 0


def resumo(conexao, mes=None) -> dict:
    """Totais de receitas, despesas e saldo, além das despesas por categoria."""
    filtro = ""
    parametros = []
    if mes:
        filtro = " AND substr(data, 1, 7) = ?"
        parametros.append(validar_mes(mes))

    totais = {"receita": 0, "despesa": 0}
    for linha in conexao.execute(
        f"SELECT tipo, SUM(valor_centavos) AS total FROM lancamentos WHERE 1 = 1{filtro} GROUP BY tipo",
        parametros,
    ):
        totais[linha["tipo"]] = linha["total"]

    por_categoria = {
        linha["categoria"]: linha["total"]
        for linha in conexao.execute(
            "SELECT categoria, SUM(valor_centavos) AS total FROM lancamentos "
            f"WHERE tipo = 'despesa'{filtro} GROUP BY categoria ORDER BY total DESC, categoria",
            parametros,
        )
    }

    return {
        "receitas": totais["receita"],
        "despesas": totais["despesa"],
        "saldo": totais["receita"] - totais["despesa"],
        "por_categoria": por_categoria,
    }
