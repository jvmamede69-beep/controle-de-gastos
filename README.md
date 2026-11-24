# Controle de Gastos

Programa de linha de comando em Python para controlar receitas e despesas pessoais, com os dados guardados em um banco de dados **SQLite**. Não precisa instalar nada além do Python.

## Funcionalidades

- Registrar despesas e receitas, com categoria e data
- Listar os lançamentos, filtrando por mês e por categoria
- Resumo com receitas, despesas, saldo e gasto por categoria
- Remover lançamentos pelo id
- Os dados ficam salvos no arquivo `gastos.db` e continuam lá na próxima vez que você abrir o programa

## Detalhes técnicos

- **Banco de dados SQLite** com a tabela `lancamentos` e regras `CHECK` que impedem valores inválidos direto no banco
- **Valores guardados em centavos** (números inteiros), para evitar erros de arredondamento de números decimais
- **Consultas parametrizadas**, que protegem contra SQL injection (existe teste para isso)
- Validação de valor, data (`AAAA-MM-DD`) e mês (`AAAA-MM`), com mensagens de erro claras
- Código separado em camadas: `banco.py` (dados e regras) e `cli.py` (interface)
- 48 testes automatizados com pytest, rodando também no GitHub Actions

## Como usar

Precisa do Python 3.9 ou mais novo. Dentro da pasta do projeto:

```bash
python -m gastos adicionar 3000 "Salário" --receita --categoria trabalho
python -m gastos adicionar 25,90 "Almoço" --categoria alimentacao
python -m gastos adicionar 250 "Gasolina" --categoria transporte --data 2026-11-14
python -m gastos listar
python -m gastos listar --mes 2026-11
python -m gastos resumo --mes 2026-11
python -m gastos remover 2
```

No Windows, se `python` não funcionar, use `py` no lugar.

Exemplo de saída do `resumo`:

```
Resumo de 2026-11
Receitas: R$ 3.000,00
Despesas: R$ 1.095,90
Saldo:    R$ 1.904,10

Despesas por categoria:
  alimentacao     R$ 800,00
  transporte      R$ 250,00
  lazer           R$ 45,90
```

Para usar outro arquivo de banco, passe `--banco meu.db` antes do comando ou defina a variável de ambiente `GASTOS_DB`.

## Rodando os testes

```bash
pip install -r requirements-dev.txt
pytest
```

## Estrutura

```
gastos/
  banco.py     banco de dados SQLite e regras de negócio
  cli.py       comandos e formatação da saída
  __main__.py  permite rodar com "python -m gastos"
tests/
  test_banco.py   testes do banco e das regras
  test_cli.py     testes dos comandos
```

## Tecnologias

Python, SQLite (`sqlite3`), argparse e pytest.

## Autor

João Vitor Mamede de Araújo – [GitHub](https://github.com/jvmamede69-beep)
