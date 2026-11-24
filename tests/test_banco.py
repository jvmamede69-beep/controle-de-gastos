import sqlite3

import pytest

from gastos import banco


@pytest.fixture
def conexao(tmp_path):
    con = banco.conectar(str(tmp_path / "teste.db"))
    yield con
    con.close()


# ---------- conversão e formatação de valores ----------


@pytest.mark.parametrize(
    "texto, esperado",
    [("10", 1000), ("10,50", 1050), ("10.5", 1050), ("0,01", 1), (" 25,90 ", 2590), (3, 300)],
)
def test_reais_para_centavos_valido(texto, esperado):
    assert banco.reais_para_centavos(texto) == esperado


@pytest.mark.parametrize("texto", ["0", "-5", "abc", "", "10,505", "NaN", "Infinity"])
def test_reais_para_centavos_invalido(texto):
    with pytest.raises(ValueError):
        banco.reais_para_centavos(texto)


def test_sem_erro_de_arredondamento_de_float():
    # com float, 0.1 + 0.2 != 0.3; em centavos a conta é exata
    assert banco.reais_para_centavos("0,10") + banco.reais_para_centavos("0,20") == banco.reais_para_centavos("0,30")


@pytest.mark.parametrize(
    "centavos, esperado",
    [(5, "R$ 0,05"), (100, "R$ 1,00"), (123456, "R$ 1.234,56"), (100000000, "R$ 1.000.000,00")],
)
def test_formatar_reais(centavos, esperado):
    assert banco.formatar_reais(centavos) == esperado


def test_validar_data_e_mes():
    assert banco.validar_data("2026-11-24") == "2026-11-24"
    for ruim in ["24/11/2026", "2026-13-01", "2026-02-30", "", None]:
        with pytest.raises(ValueError):
            banco.validar_data(ruim)

    assert banco.validar_mes("2026-11") == "2026-11"
    for ruim in ["2026-13", "2026-1", "11/2026", "", None]:
        with pytest.raises(ValueError):
            banco.validar_mes(ruim)


# ---------- adicionar e listar ----------


def test_adicionar_e_listar(conexao):
    id1 = banco.adicionar(conexao, "25,90", "Almoço", "Alimentacao", data="2026-11-02")
    id2 = banco.adicionar(conexao, "3000", "Salário", "trabalho", tipo="receita", data="2026-11-01")
    assert (id1, id2) == (1, 2)

    linhas = banco.listar(conexao)
    assert [l["descricao"] for l in linhas] == ["Salário", "Almoço"]  # ordenado por data
    assert linhas[1]["valor_centavos"] == 2590
    assert linhas[1]["categoria"] == "alimentacao"  # categoria sempre em minúsculas
    assert linhas[0]["tipo"] == "receita"


def test_adicionar_usa_a_data_de_hoje_por_padrao(conexao):
    from datetime import date

    banco.adicionar(conexao, "10", "Café")
    assert banco.listar(conexao)[0]["data"] == date.today().isoformat()


@pytest.mark.parametrize(
    "dados",
    [
        {"valor": "0", "descricao": "x"},
        {"valor": "abc", "descricao": "x"},
        {"valor": "10", "descricao": "   "},
        {"valor": "10", "descricao": "x", "categoria": " "},
        {"valor": "10", "descricao": "x", "tipo": "outro"},
        {"valor": "10", "descricao": "x", "data": "ontem"},
    ],
)
def test_adicionar_rejeita_dados_invalidos(conexao, dados):
    with pytest.raises(ValueError):
        banco.adicionar(conexao, **dados)
    assert banco.listar(conexao) == []  # nada foi gravado


def test_listar_filtra_por_mes_e_categoria(conexao):
    banco.adicionar(conexao, "10", "a", "mercado", data="2026-10-30")
    banco.adicionar(conexao, "20", "b", "mercado", data="2026-11-02")
    banco.adicionar(conexao, "30", "c", "lazer", data="2026-11-15")

    assert [l["descricao"] for l in banco.listar(conexao, mes="2026-11")] == ["b", "c"]
    assert [l["descricao"] for l in banco.listar(conexao, categoria="MERCADO")] == ["a", "b"]
    assert [l["descricao"] for l in banco.listar(conexao, mes="2026-11", categoria="lazer")] == ["c"]
    assert banco.listar(conexao, mes="2025-01") == []
    with pytest.raises(ValueError):
        banco.listar(conexao, mes="novembro")


def test_sql_injection_nao_funciona(conexao):
    banco.adicionar(conexao, "10", "teste", "mercado")
    assert banco.listar(conexao, categoria="x' OR '1'='1") == []
    banco.adicionar(conexao, "5", "'); DROP TABLE lancamentos; --", "mercado")
    assert len(banco.listar(conexao)) == 2  # a tabela continua existindo


# ---------- remover ----------


def test_remover(conexao):
    novo = banco.adicionar(conexao, "10", "teste")
    assert banco.remover(conexao, novo) is True
    assert banco.remover(conexao, novo) is False
    assert banco.listar(conexao) == []


# ---------- resumo ----------


def test_resumo_calcula_totais_e_categorias(conexao):
    banco.adicionar(conexao, "3000", "Salário", "trabalho", "receita", "2026-11-01")
    banco.adicionar(conexao, "800", "Mercado", "alimentacao", data="2026-11-05")
    banco.adicionar(conexao, "200,50", "Pizza", "alimentacao", data="2026-11-10")
    banco.adicionar(conexao, "250", "Ônibus", "transporte", data="2026-11-11")
    banco.adicionar(conexao, "99", "Outro mês", "lazer", data="2026-10-20")

    r = banco.resumo(conexao, mes="2026-11")
    assert r["receitas"] == 300000
    assert r["despesas"] == 125050
    assert r["saldo"] == 174950
    assert r["por_categoria"] == {"alimentacao": 100050, "transporte": 25000}
    assert list(r["por_categoria"]) == ["alimentacao", "transporte"]  # maior gasto primeiro

    geral = banco.resumo(conexao)
    assert geral["despesas"] == 125050 + 9900


def test_resumo_vazio(conexao):
    assert banco.resumo(conexao) == {"receitas": 0, "despesas": 0, "saldo": 0, "por_categoria": {}}


def test_saldo_pode_ser_negativo(conexao):
    banco.adicionar(conexao, "100", "Compra")
    assert banco.resumo(conexao)["saldo"] == -10000


# ---------- banco de dados ----------


def test_dados_persistem_entre_conexoes(tmp_path):
    caminho = str(tmp_path / "persistente.db")
    con = banco.conectar(caminho)
    banco.adicionar(con, "10", "teste")
    con.close()

    con2 = banco.conectar(caminho)
    assert len(banco.listar(con2)) == 1
    con2.close()


def test_o_banco_recusa_valores_invalidos_mesmo_fora_do_codigo(conexao):
    # As regras CHECK da tabela protegem o banco mesmo se alguém ignorar a validação do Python.
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "INSERT INTO lancamentos (tipo, valor_centavos, descricao, categoria, data) "
            "VALUES ('despesa', -5, 'x', 'y', '2026-01-01')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "INSERT INTO lancamentos (tipo, valor_centavos, descricao, categoria, data) "
            "VALUES ('doacao', 5, 'x', 'y', '2026-01-01')"
        )
