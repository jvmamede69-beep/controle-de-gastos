"""Interface de linha de comando do controle de gastos."""

import argparse
import os
import sys

from . import banco


def _criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gastos", description="Controle de gastos pessoais com SQLite."
    )
    parser.add_argument(
        "--banco",
        default=os.environ.get("GASTOS_DB", "gastos.db"),
        help="arquivo do banco de dados (padrão: gastos.db)",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    add = sub.add_parser("adicionar", help="registra uma despesa ou receita")
    add.add_argument("valor", help='valor em reais, ex.: 25,90')
    add.add_argument("descricao", help="o que foi")
    add.add_argument("--categoria", default="geral", help="ex.: alimentacao, transporte")
    add.add_argument("--receita", action="store_true", help="registra como receita (o padrão é despesa)")
    add.add_argument("--data", help="AAAA-MM-DD (o padrão é hoje)")

    lst = sub.add_parser("listar", help="mostra os lançamentos")
    lst.add_argument("--mes", help="filtra por mês, no formato AAAA-MM")
    lst.add_argument("--categoria", help="filtra por categoria")

    res = sub.add_parser("resumo", help="mostra receitas, despesas e saldo")
    res.add_argument("--mes", help="filtra por mês, no formato AAAA-MM")

    rem = sub.add_parser("remover", help="apaga um lançamento pelo id")
    rem.add_argument("id", type=int)

    return parser


def _mostrar_lista(linhas) -> None:
    if not linhas:
        print("Nenhum lançamento encontrado.")
        return

    cabecalho = ("ID", "DATA", "TIPO", "CATEGORIA", "DESCRIÇÃO", "VALOR")
    tabela = [
        (
            str(l["id"]),
            l["data"],
            l["tipo"],
            l["categoria"],
            l["descricao"],
            banco.formatar_reais(l["valor_centavos"]),
        )
        for l in linhas
    ]
    larguras = [max(len(cabecalho[i]), *(len(linha[i]) for linha in tabela)) for i in range(6)]

    def formatar(linha):
        # o valor (última coluna) fica alinhado à direita
        colunas = [linha[i].ljust(larguras[i]) for i in range(5)]
        colunas.append(linha[5].rjust(larguras[5]))
        return "  ".join(colunas)

    print(formatar(cabecalho))
    print("  ".join("-" * w for w in larguras))
    for linha in tabela:
        print(formatar(linha))


def _mostrar_resumo(dados: dict, mes) -> None:
    print(f"Resumo de {mes}" if mes else "Resumo geral")
    print(f"Receitas: {banco.formatar_reais(dados['receitas'])}")
    print(f"Despesas: {banco.formatar_reais(dados['despesas'])}")
    sinal = "-" if dados["saldo"] < 0 else ""
    print(f"Saldo:    {sinal}{banco.formatar_reais(abs(dados['saldo']))}")

    if dados["por_categoria"]:
        print("\nDespesas por categoria:")
        for categoria, total in dados["por_categoria"].items():
            print(f"  {categoria:<15} {banco.formatar_reais(total)}")


def main(argv=None) -> int:
    args = _criar_parser().parse_args(argv)
    conexao = banco.conectar(args.banco)
    try:
        if args.comando == "adicionar":
            tipo = "receita" if args.receita else "despesa"
            novo_id = banco.adicionar(
                conexao, args.valor, args.descricao, args.categoria, tipo, args.data
            )
            print(f"Registrado (id {novo_id}): {tipo} de {banco.formatar_reais(banco.reais_para_centavos(args.valor))}.")
        elif args.comando == "listar":
            _mostrar_lista(banco.listar(conexao, args.mes, args.categoria))
        elif args.comando == "resumo":
            _mostrar_resumo(banco.resumo(conexao, args.mes), args.mes)
        elif args.comando == "remover":
            if not banco.remover(conexao, args.id):
                raise ValueError(f"Não existe lançamento com id {args.id}.")
            print(f"Lançamento {args.id} removido.")
        return 0
    except ValueError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    finally:
        conexao.close()
