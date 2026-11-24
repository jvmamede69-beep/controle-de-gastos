import pytest

from gastos.cli import main


@pytest.fixture
def banco_arquivo(tmp_path):
    return str(tmp_path / "cli.db")


def rodar(banco_arquivo, *args):
    return main(["--banco", banco_arquivo, *args])


def test_adicionar_mostra_confirmacao(banco_arquivo, capsys):
    codigo = rodar(banco_arquivo, "adicionar", "25,90", "Almoço", "--categoria", "alimentacao", "--data", "2026-11-02")
    saida = capsys.readouterr().out
    assert codigo == 0
    assert "id 1" in saida
    assert "despesa" in saida
    assert "R$ 25,90" in saida


def test_adicionar_receita(banco_arquivo, capsys):
    assert rodar(banco_arquivo, "adicionar", "3000", "Salário", "--receita") == 0
    assert "receita de R$ 3.000,00" in capsys.readouterr().out


def test_listar_mostra_tabela(banco_arquivo, capsys):
    rodar(banco_arquivo, "adicionar", "25,90", "Almoço", "--categoria", "alimentacao", "--data", "2026-11-02")
    rodar(banco_arquivo, "adicionar", "1500", "Aluguel", "--categoria", "casa", "--data", "2026-10-05")
    capsys.readouterr()

    assert rodar(banco_arquivo, "listar") == 0
    saida = capsys.readouterr().out
    assert "ID" in saida and "VALOR" in saida
    assert "Almoço" in saida and "R$ 25,90" in saida
    assert "R$ 1.500,00" in saida

    rodar(banco_arquivo, "listar", "--mes", "2026-11")
    filtrada = capsys.readouterr().out
    assert "Almoço" in filtrada
    assert "Aluguel" not in filtrada


def test_listar_vazio(banco_arquivo, capsys):
    assert rodar(banco_arquivo, "listar") == 0
    assert "Nenhum lançamento" in capsys.readouterr().out


def test_resumo(banco_arquivo, capsys):
    rodar(banco_arquivo, "adicionar", "3000", "Salário", "--receita", "--data", "2026-11-01")
    rodar(banco_arquivo, "adicionar", "800", "Mercado", "--categoria", "alimentacao", "--data", "2026-11-05")
    capsys.readouterr()

    assert rodar(banco_arquivo, "resumo", "--mes", "2026-11") == 0
    saida = capsys.readouterr().out
    assert "Resumo de 2026-11" in saida
    assert "Receitas: R$ 3.000,00" in saida
    assert "Despesas: R$ 800,00" in saida
    assert "Saldo:    R$ 2.200,00" in saida
    assert "alimentacao" in saida


def test_resumo_com_saldo_negativo(banco_arquivo, capsys):
    rodar(banco_arquivo, "adicionar", "100", "Compra")
    capsys.readouterr()
    rodar(banco_arquivo, "resumo")
    assert "Saldo:    -R$ 100,00" in capsys.readouterr().out


def test_remover(banco_arquivo, capsys):
    rodar(banco_arquivo, "adicionar", "10", "Café")
    capsys.readouterr()
    assert rodar(banco_arquivo, "remover", "1") == 0
    assert "removido" in capsys.readouterr().out


def test_remover_inexistente_da_erro(banco_arquivo, capsys):
    assert rodar(banco_arquivo, "remover", "99") == 1
    assert "Não existe lançamento com id 99" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        ["adicionar", "abc", "x"],
        ["adicionar", "0", "x"],
        ["adicionar", "10", "x", "--data", "ontem"],
        ["listar", "--mes", "novembro"],
    ],
)
def test_entradas_invalidas_mostram_erro_e_retornam_1(banco_arquivo, capsys, args):
    assert rodar(banco_arquivo, *args) == 1
    assert capsys.readouterr().err.startswith("Erro:")


def test_comando_desconhecido_sai_com_codigo_2(banco_arquivo):
    with pytest.raises(SystemExit) as saida:
        rodar(banco_arquivo, "voar")
    assert saida.value.code == 2
