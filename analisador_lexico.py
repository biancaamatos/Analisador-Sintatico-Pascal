"""
ANALISADOR LEXICO - Object Pascal

Le um arquivo .txt (codigo fonte em Pascal) e gera uma tabela
LINHA | ATOMO | SIMBOLO

É basicamente o automato desenhado em sala, implementado em
codigo: percorremos o texto caractere por caractere, trocando de
"estado" conforme o tipo de caractere, exatamente como nas setas do
desenho.
"""

import sys
import csv
import argparse

# 1) TABELA DE PALAVRAS RESERVADAS

RESERVED_WORDS = {
    # estrutura do programa
    "PROGRAM": "C_PROGRAM", "USES": "C_USES", "UNIT": "C_UNIT",
    "INTERFACE": "C_INTERFACE", "IMPLEMENTATION": "C_IMPLEMENTATION",
    "VAR": "C_VAR", "CONST": "C_CONST", "TYPE": "C_TYPE",
    "BEGIN": "C_BEGIN", "END": "C_END",
    "FUNCTION": "C_FUNCTION", "PROCEDURE": "C_PROCEDURE",
    "RECORD": "C_RECORD", "ARRAY": "C_ARRAY", "OF": "C_OF",

    # tipos
    "INTEGER": "C_INTEGER_TIPO", "REAL": "C_REAL_TIPO",
    "STRING": "C_STRING_TIPO", "BOOLEAN": "C_BOOLEAN_TIPO",
    "CHAR": "C_CHAR_TIPO",

    # controle de fluxo
    "IF": "C_IF", "THEN": "C_THEN", "ELSE": "C_ELSE",
    "FOR": "C_FOR", "TO": "C_TO", "DOWNTO": "C_DOWNTO",
    "WHILE": "C_WHILE", "REPEAT": "C_REPEAT", "UNTIL": "C_UNTIL",
    "DO": "C_DO", "CASE": "C_CASE", "WITH": "C_WITH",
    "EXIT": "C_EXIT", "HALT": "C_HALT",

    # operadores logicos/aritmeticos
    "AND": "C_AND", "OR": "C_OR", "NOT": "C_NOT", "IN": "C_IN",
    "DIV": "C_DIV", "MOD": "C_MOD",

    # literais especiais
    "NIL": "C_NIL", "TRUE": "C_TRUE", "FALSE": "C_FALSE",

    # comandos do Pascal (Diagrama feito em sala)
    "WRITE": "C_WRITE", "WRITELN": "C_WRITELN",
    "READ": "C_READ", "READLN": "C_READLN",
    "CLREOL": "C_CLREOL", "CLRSCR": "C_CLRSCR",
    "DELAY": "C_DELAY", "GOTOXY": "C_GOTOXY", "GOTO": "C_GOTO",
    "INLINE": "C_INLINE", "KEYPRESSED": "C_KEYPRESSED",
    "LENGTH": "C_LENGTH", "RANDOM": "C_RANDOM",
    "RANDOMIZE": "C_RANDOMIZE", "WHEREX": "C_WHEREX",
    "WHEREY": "C_WHEREY", "HI": "C_HI", "LO": "C_LO",
    "PARAMCOUNT": "C_PARAMCOUNT", "PARAMSTR": "C_PARAMSTR",
    "SIZEOF": "C_SIZEOF", "MAXAVAIL": "C_MAXAVAIL",
    "MEMAVAIL": "C_MEMAVAIL", "GETMEM": "C_GETMEM",
    "FREEMEM": "C_FREEMEM", "MOVE": "C_MOVE", "FILLCHAR": "C_FILLCHAR",
}

# 2) TABELA DE SIMBOLOS/PONTUACAO
# (ordem importa: primeiro os de 2 caracteres, senao ':=' vira ':'+'=')

SYMBOLS_2CHAR = {
    ":=": "C_ATRIBUICAO",
    "<=": "C_MENOR_IGUAL",
    ">=": "C_MAIOR_IGUAL",
    "<>": "C_DIFERENTE",
    "..": "C_DOIS_PONTOS_DUPLO",
}

SYMBOLS_1CHAR = {
    ";": "C_PONTO_E_VIRGULA",
    ":": "C_DOIS_PONTOS",
    ",": "C_VIRGULA",
    ".": "C_PONTO",
    "(": "C_ABRE_PARENTESES",
    ")": "C_FECHA_PARENTESES",
    "[": "C_ABRE_COLCHETE",
    "]": "C_FECHA_COLCHETE",
    "=": "C_IGUAL",
    "+": "C_MAIS",
    "-": "C_MENOS",
    "*": "C_MULTIPLICACAO",
    "/": "C_DIVISAO",
    "<": "C_MENOR",
    ">": "C_MAIOR",
    "^": "C_PONTEIRO",
    "@": "C_ARROBA",
}


def classify_word(word: str) -> str:
    """Decide se 'word' e palavra reservada ou identificador."""
    if word.upper() in RESERVED_WORDS:
        return RESERVED_WORDS[word.upper()]
    return "C_IDENT"


def tokenize(source: str):
    """
    O 'automato' em si.
    Percorre o texto caractere por caractere trocando de estado:
    ESTADO INICIAL -> IDENTIFICADOR / NUMERO / STRING / SIMBOLO / COMENTARIO
    Retorna uma lista de tuplas (linha, atomo, simbolo).
    """
    tokens = []
    i = 0
    n = len(source)
    linha = 1

    while i < n:
        ch = source[i]

        # quebra de linha: só o atualiza contador
        if ch == "\n":
            linha += 1
            i += 1
            continue

        # espaco em branco: ignora
        if ch in " \t\r":
            i += 1
            continue

        # comentario {...}
        if ch == "{":
            j = i + 1
            while j < n and source[j] != "}":
                if source[j] == "\n":
                    linha += 1
                j += 1
            i = j + 1
            continue

        # comentario (*...*)
        if ch == "(" and i + 1 < n and source[i + 1] == "*":
            j = i + 2
            while j + 1 < n and not (source[j] == "*" and source[j + 1] == ")"):
                if source[j] == "\n":
                    linha += 1
                j += 1
            i = j + 2
            continue

        # string entre aspas simples 'texto'
        if ch == "'":
            j = i + 1
            buf = "'"
            fechou = False
            while j < n:
                buf += source[j]
                if source[j] == "'":
                    # dentro de string = aspas literal, Pascal padrao
                    if j + 1 < n and source[j + 1] == "'":
                        buf += source[j + 1]
                        j += 2
                        continue
                    fechou = True
                    j += 1
                    break
                if source[j] == "\n":
                    linha += 1
                j += 1
            tokens.append((linha, buf, "C_STRING" if fechou else "C_ERRO_STRING_NAO_FECHADA"))
            i = j
            continue

        # identificador / palavra reservada
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (source[j].isalnum() or source[j] == "_"):
                j += 1
            word = source[i:j]
            tokens.append((linha, word, classify_word(word)))
            i = j
            continue

        # numero (inteiro ou real)
        if ch.isdigit():
            j = i
            while j < n and source[j].isdigit():
                j += 1
            is_real = False
            if j < n and source[j] == "." and j + 1 < n and source[j + 1].isdigit():
                is_real = True
                j += 1
                while j < n and source[j].isdigit():
                    j += 1
            number = source[i:j]

            # possíveis erros --> numero colado com letra (ex: 123A)
            if j < n and (source[j].isalpha() or source[j] == "_"):
                k = j
                while k < n and (source[k].isalnum() or source[k] == "_"):
                    k += 1
                atomo_invalido = source[i:k]
                tokens.append((linha, atomo_invalido, "C_ERRO_NUMERO_COM_LETRA"))
                i = k
                continue

            tokens.append((linha, number, "C_REAL" if is_real else "C_INTEGER"))
            i = j
            continue

        # simbolos de 2 caracteres
        two = source[i:i + 2]
        if two in SYMBOLS_2CHAR:
            tokens.append((linha, two, SYMBOLS_2CHAR[two]))
            i += 2
            continue

        # simbolos de 1 caractere
        if ch in SYMBOLS_1CHAR:
            tokens.append((linha, ch, SYMBOLS_1CHAR[ch]))
            i += 1
            continue

        # caractere nao reconhecido pelo automato
        tokens.append((linha, ch, "C_ERRO_CARACTERE_INVALIDO"))
        i += 1

    return tokens

# 3) CORES E FORMATAÇÃO PARA DEIXAR VIZUALMENTE MAIS BONITO

ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "azul": "\033[34m",      # palavras reservadas
    "verde": "\033[32m",     # identificadores
    "amarelo": "\033[33m",   # numeros
    "magenta": "\033[35m",   # strings
    "ciano": "\033[36m",     # simbolos/pontuacao
    "vermelho": "\033[91m",  # erros
}


def cor_do_simbolo(simbolo: str) -> str:
    if simbolo.startswith("C_ERRO"):
        return ANSI["vermelho"]
    if simbolo == "C_IDENT":
        return ANSI["verde"]
    if simbolo in ("C_INTEGER", "C_REAL"):
        return ANSI["amarelo"]
    if simbolo == "C_STRING":
        return ANSI["magenta"]
    if simbolo in SYMBOLS_1CHAR.values() or simbolo in SYMBOLS_2CHAR.values():
        return ANSI["ciano"]
    return ANSI["azul"]  # sobrou = palavra reservada


def print_table(tokens):
    cabecalho = f"{'LINHA':<8}{'ATOMO':<25}{'SIMBOLO':<30}"
    print(ANSI["bold"] + cabecalho + ANSI["reset"])
    print(ANSI["dim"] + "-" * 63 + ANSI["reset"])
    for linha, atomo, simbolo in tokens:
        cor = cor_do_simbolo(simbolo)
        marca = f"{ANSI['bold']}  <<< ERRO{ANSI['reset']}" if simbolo.startswith("C_ERRO") else ""
        linha_txt = f"{linha:<8}{atomo:<25}{simbolo:<30}"
        print(f"{cor}{linha_txt}{ANSI['reset']}{marca}")


def save_csv(tokens, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["LINHA", "ATOMO", "SIMBOLO"])
        w.writerows(tokens)


def save_html(tokens, path, nome_arquivo=""):
    cores_css = {
        "vermelho": "#e5484d", "verde": "#2fb344", "amarelo": "#d4a72c",
        "magenta": "#c33cd0", "ciano": "#2b95c9", "azul": "#3b6fd6",
    }

    def cor_css(simbolo):
        cor = cor_do_simbolo(simbolo)
        nome = {v: k for k, v in ANSI.items()}.get(cor, "azul")
        return cores_css.get(nome, "#333")

    total = len(tokens)
    erros = [t for t in tokens if t[2].startswith("C_ERRO")]
    agora = __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")

    linhas_html = []
    for linha, atomo, simbolo in tokens:
        cor = cor_css(simbolo)
        atomo_escapado = (atomo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        classe_erro = " erro" if simbolo.startswith("C_ERRO") else ""
        linhas_html.append(
            f'<tr class="{classe_erro}">'
            f'<td>{linha}</td>'
            f'<td><code>{atomo_escapado}</code></td>'
            f'<td style="color:{cor}; font-weight:600;">{simbolo}</td>'
            f'</tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Analisador Lexico - {nome_arquivo}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0f1117; color:#e6e6e6; padding: 32px; }}
  h1 {{ margin-bottom: 4px; }}
  .sub {{ color:#9aa0a6; margin-bottom: 24px; }}
  .resumo {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
  .card {{ background:#1a1d27; border-radius:10px; padding:14px 20px; min-width:140px; }}
  .card .num {{ font-size:28px; font-weight:700; }}
  .card .label {{ color:#9aa0a6; font-size:13px; }}
  table {{ border-collapse: collapse; width:100%; background:#1a1d27; border-radius:10px; overflow:hidden; }}
  th, td {{ padding:8px 14px; text-align:left; border-bottom:1px solid #2a2d3a; font-size:14px; }}
  th {{ background:#22263a; position:sticky; top:0; }}
  tr.erro {{ background:#3a1518; }}
  code {{ background:#22263a; padding:2px 6px; border-radius:4px; }}
</style>
</head>
<body>
  <h1>Analisador Lexico &mdash; Turbo Pascal</h1>
  <div class="sub">Arquivo: {nome_arquivo or "(entrada)"} &nbsp;|&nbsp; Gerado em {agora}</div>

  <div class="resumo">
    <div class="card"><div class="num">{total}</div><div class="label">Total de atomos</div></div>
    <div class="card"><div class="num" style="color:#e5484d">{len(erros)}</div><div class="label">Erros encontrados</div></div>
  </div>

  <table>
    <thead><tr><th>LINHA</th><th>ATOMO</th><th>SIMBOLO</th></tr></thead>
    <tbody>
      {''.join(linhas_html)}
    </tbody>
  </table>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="Analisador lexico de Pascal")
    parser.add_argument("arquivo", help="Arquivo .txt/.pas de entrada")
    parser.add_argument("--csv", help="Caminho para salvar a tabela em CSV", default=None)
    parser.add_argument("--html", help="Caminho para salvar um relatorio .html", default=None)
    args = parser.parse_args()

    with open(args.arquivo, "r", encoding="utf-8") as f:
        source = f.read()

    tokens = tokenize(source)
    print_table(tokens)

    erros = [t for t in tokens if t[2].startswith("C_ERRO")]
    cor_total = ANSI["vermelho"] if erros else ANSI["verde"]
    print(f"\nTotal de atomos: {len(tokens)}  |  {cor_total}Erros encontrados: {len(erros)}{ANSI['reset']}")

    if args.csv:
        save_csv(tokens, args.csv)
        print(f"Tabela salva em: {args.csv}")

    if args.html:
        save_html(tokens, args.html, nome_arquivo=args.arquivo)
        print(f"Relatorio HTML salvo em: {args.html}")


if __name__ == "__main__":
    main()
