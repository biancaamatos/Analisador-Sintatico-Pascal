"""
ANALISADOR SINTÁTICO - Object Pascal

Segunda etapa do compilador. O analisador LÉXICO (analisador_lexico.py)
já disse O QUE é cada palavra (reservada, identificador, número...).
Agora o SINTÁTICO verifica se elas estão na ORDEM CERTA, segundo as
regras da gramática do Pascal.

Exemplo:
    VAR M : INTEGER ;     -> ordem correta
    VAR : M INTEGER ;     -> ERRO: esperava identificador, veio ':'

GRAMÁTICA IMPLEMENTADA (subconjunto do Pascal):

    programa      -> PROGRAM ident ';' bloco '.'
    bloco         -> [const] [type] [var] {subrotina} comando_composto
    secao_var     -> VAR {lista_ident ':' tipo ';'}
    subrotina     -> (PROCEDURE|FUNCTION) ident [params] [':' tipo] ';' bloco ';'
    comando_comp  -> BEGIN [comando {';' comando}] END
    comando       -> atribuicao | chamada | if | while | for | repeat | comando_comp
    if            -> IF expressao THEN comando [ELSE comando]
    while         -> WHILE expressao DO comando
    for           -> FOR ident ':=' expressao (TO|DOWNTO) expressao DO comando
    repeat        -> REPEAT comando {';' comando} UNTIL expressao
    expressao     -> simples [op_relacional simples]
    simples       -> [+|-] termo {(+|-|OR) termo}
    termo         -> fator {(*|/|DIV|MOD|AND) fator}
    fator         -> ident[(args)] | numero | string | '(' expressao ')' | NOT fator
"""

import os
import sys
import glob
import argparse
from analisador_lexico import tokenize, ANSI


class ErroSintatico(Exception):
    # Erro de sintaxe encontrado durante a análise.

    def __init__(self, linha, esperado, encontrado):
        self.linha = linha
        self.esperado = esperado
        self.encontrado = encontrado
        super().__init__(f"Linha {linha}: esperava {esperado}, encontrou '{encontrado}'")


# Símbolos que representam um tipo de dado válido
TIPOS = {
    "C_INTEGER_TIPO", "C_REAL_TIPO", "C_STRING_TIPO",
    "C_BOOLEAN_TIPO", "C_CHAR_TIPO", "C_IDENT",
}

# Operadores relacionais (usados em comparações)
OP_RELACIONAL = {
    "C_IGUAL", "C_DIFERENTE", "C_MENOR", "C_MAIOR",
    "C_MENOR_IGUAL", "C_MAIOR_IGUAL",
}

# Operadores de soma (precedência mais baixa)
OP_SOMA = {"C_MAIS", "C_MENOS", "C_OR"}

# Operadores de multiplicação (precedência mais alta)
OP_MULT = {"C_MULTIPLICACAO", "C_DIVISAO", "C_DIV", "C_MOD", "C_AND"}

# Símbolos que podem iniciar um comando
INICIO_COMANDO = {
    "C_IDENT", "C_BEGIN", "C_IF", "C_WHILE", "C_FOR",
    "C_REPEAT", "C_CASE", "C_WRITE", "C_WRITELN", "C_READ",
    "C_READLN", "C_CLRSCR", "C_CLREOL", "C_GOTOXY", "C_DELAY",
    "C_RANDOMIZE", "C_HALT", "C_EXIT", "C_GETMEM", "C_FREEMEM",
    "C_MOVE", "C_FILLCHAR", "C_INLINE",
}

# Rotinas que podem ser chamadas como comando (WRITELN(...), CLRSCR, etc)
ROTINAS = {
    "C_WRITE", "C_WRITELN", "C_READ", "C_READLN", "C_CLRSCR",
    "C_CLREOL", "C_GOTOXY", "C_DELAY", "C_RANDOMIZE", "C_HALT",
    "C_EXIT", "C_GETMEM", "C_FREEMEM", "C_MOVE", "C_FILLCHAR",
    "C_INLINE",
}


class Parser:
    # Analisador sintático descendente recursivo.
    # Para cada regra da gramática existe uma função, que chama as
    # funções das sub-regras. É o mesmo princípio do autômato, só que
    # em vez de estados de letras, os "estados" são as regras gramaticais.

    def __init__(self, tokens):
        # NAO filtramos os tokens de erro lexico: eles continuam no fluxo,
        # ocupando o lugar exato onde estavam (um numero mal formado ainda
        # esta na posicao de um numero). Se filtrassemos, "abriria um buraco"
        # na expressao e o parser ia reportar erro sintatico em cascata por
        # causa de UM erro lexico so. Quem reporta o problema lexico em si
        # e o analisador lexico (self.erros_lexicos abaixo); o sintatico so
        # "engole" o token quieto pra nao quebrar o resto da analise.
        self.tokens = tokens
        self.erros_lexicos = [t for t in tokens if t[2].startswith("C_ERRO")]
        self.pos = 0
        self.erros = []

    def atual(self):
        # token atual, ou um marcador de fim de arquivo
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        ultima_linha = self.tokens[-1][0] if self.tokens else 0
        return (ultima_linha, "<fim do arquivo>", "C_EOF")

    def simbolo(self):
        # categoria (símbolo) do token atual
        return self.atual()[2]

    def avancar(self):
        # consome o token atual e devolve ele
        tok = self.atual()
        self.pos += 1
        return tok

    def verificar(self, *simbolos):
        return self.simbolo() in simbolos

    def consumir(self, simbolo, descricao):
        # exige que o token atual seja "simbolo"; se não for, registra erro
        if self.simbolo() == simbolo:
            return self.avancar()
        linha, atomo, _ = self.atual()
        erro = ErroSintatico(linha, descricao, atomo)
        self.erros.append(erro)
        raise erro

    def sincronizar(self, *ate):
        # recuperação de erro: pula tokens até um ponto seguro pra
        # continuar a análise (evita um erro virar 50 em cascata)
        alvos = set(ate) | {"C_PONTO_E_VIRGULA", "C_END", "C_EOF"}
        while self.simbolo() not in alvos:
            self.avancar()

    def pular_erro_lexico_solto(self):
        # engole silenciosamente qualquer token que o LEXICO ja marcou
        # como invalido e que sobrou "perdido" entre uma expressao e o
        # que vem depois dela (ex: caractere estranho tipo '#'/'@' onde
        # se esperava um operador ou o fim do comando). O problema ja
        # foi contabilizado como erro lexico; aqui so evitamos que ele
        # derrube o resto da analise sintatica em cascata.
        while self.simbolo().startswith("C_ERRO"):
            self.avancar()

    def programa(self):
        # programa -> PROGRAM ident ';' bloco '.'
        try:
            self.consumir("C_PROGRAM", "a palavra reservada PROGRAM")
            self.consumir("C_IDENT", "o nome do programa")
            self.consumir("C_PONTO_E_VIRGULA", "';' após o nome do programa")
        except ErroSintatico:
            self.sincronizar("C_VAR", "C_BEGIN", "C_CONST", "C_TYPE")

        # USES é opcional
        if self.verificar("C_USES"):
            try:
                self.avancar()
                self.consumir("C_IDENT", "o nome de uma unit")
                while self.verificar("C_VIRGULA"):
                    self.avancar()
                    self.consumir("C_IDENT", "o nome de uma unit")
                self.consumir("C_PONTO_E_VIRGULA", "';' após a lista de units")
            except ErroSintatico:
                self.sincronizar("C_VAR", "C_BEGIN", "C_CONST", "C_TYPE")

        self.bloco()

        try:
            self.consumir("C_PONTO", "'.' no fim do programa")
        except ErroSintatico:
            pass

        if not self.verificar("C_EOF"):
            linha, atomo, _ = self.atual()
            self.erros.append(ErroSintatico(linha, "fim do arquivo após o '.'", atomo))

    def bloco(self):
        # bloco -> [const] [type] [var] {subrotina} comando_composto
        if self.verificar("C_CONST"):
            self.secao_const()
        if self.verificar("C_TYPE"):
            self.secao_type()
        if self.verificar("C_VAR"):
            self.secao_var()
        while self.verificar("C_PROCEDURE", "C_FUNCTION"):
            self.subrotina()
        self.comando_composto()

    def secao_const(self):
        # secao_const -> CONST {ident (':' tipo)? '=' valor ';'}
        self.avancar()  # consome CONST
        while self.verificar("C_IDENT"):
            try:
                self.avancar()
                if self.verificar("C_DOIS_PONTOS"):
                    self.avancar()
                    self.tipo()
                self.consumir("C_IGUAL", "'=' na declaração da constante")
                self.expressao()
                self.consumir("C_PONTO_E_VIRGULA", "';' no fim da constante")
            except ErroSintatico:
                self.sincronizar("C_IDENT", "C_VAR", "C_TYPE", "C_BEGIN")
                if self.verificar("C_PONTO_E_VIRGULA"):
                    self.avancar()

    def secao_type(self):
        # secao_type -> TYPE {ident '=' tipo ';'}
        self.avancar()  # consome TYPE
        while self.verificar("C_IDENT"):
            try:
                self.avancar()
                self.consumir("C_IGUAL", "'=' na declaração do tipo")
                self.tipo()
                self.consumir("C_PONTO_E_VIRGULA", "';' no fim do tipo")
            except ErroSintatico:
                self.sincronizar("C_IDENT", "C_VAR", "C_BEGIN")
                if self.verificar("C_PONTO_E_VIRGULA"):
                    self.avancar()

    def secao_var(self):
        # secao_var -> VAR {lista_ident ':' tipo ';'}
        self.avancar()  # consome VAR
        if not self.verificar("C_IDENT"):
            linha, atomo, _ = self.atual()
            self.erros.append(
                ErroSintatico(linha, "pelo menos uma variável após VAR", atomo)
            )

        while self.verificar("C_IDENT"):
            try:
                # lista de identificadores: A, B, C
                self.avancar()
                while self.verificar("C_VIRGULA"):
                    self.avancar()
                    self.consumir("C_IDENT", "outro nome de variável após a ','")
                self.consumir("C_DOIS_PONTOS", "':' antes do tipo da variável")
                self.tipo()
                self.consumir("C_PONTO_E_VIRGULA", "';' no fim da declaração")
            except ErroSintatico:
                self.sincronizar("C_IDENT", "C_BEGIN", "C_PROCEDURE", "C_FUNCTION")
                if self.verificar("C_PONTO_E_VIRGULA"):
                    self.avancar()

    def tipo(self):
        # tipo -> INTEGER | REAL | STRING | BOOLEAN | CHAR | ident | ARRAY[...] OF tipo
        if self.verificar("C_ARRAY"):
            self.avancar()
            if self.verificar("C_ABRE_COLCHETE"):
                self.avancar()
                self.expressao()
                if self.verificar("C_DOIS_PONTOS_DUPLO"):
                    self.avancar()
                    self.expressao()
                self.consumir("C_FECHA_COLCHETE", "']' fechando o tamanho do array")
            self.consumir("C_OF", "a palavra OF após o array")
            self.tipo()
            return

        if self.simbolo() in TIPOS:
            self.avancar()
            return

        linha, atomo, _ = self.atual()
        erro = ErroSintatico(linha, "um tipo (INTEGER, REAL, STRING...)", atomo)
        self.erros.append(erro)
        raise erro

    def subrotina(self):
        # subrotina -> (PROCEDURE|FUNCTION) ident [params] [':' tipo] ';' bloco ';'
        eh_funcao = self.verificar("C_FUNCTION")
        self.avancar()  # consome PROCEDURE ou FUNCTION
        try:
            self.consumir("C_IDENT", "o nome da função/procedimento")

            # parâmetros (opcionais)
            if self.verificar("C_ABRE_PARENTESES"):
                self.avancar()
                if not self.verificar("C_FECHA_PARENTESES"):
                    while True:
                        if self.verificar("C_VAR"):
                            self.avancar()  # parâmetro por referência
                        self.consumir("C_IDENT", "o nome do parâmetro")
                        while self.verificar("C_VIRGULA"):
                            self.avancar()
                            self.consumir("C_IDENT", "outro nome de parâmetro")
                        self.consumir("C_DOIS_PONTOS", "':' antes do tipo do parâmetro")
                        self.tipo()
                        if self.verificar("C_PONTO_E_VIRGULA"):
                            self.avancar()
                            continue
                        break
                self.consumir("C_FECHA_PARENTESES", "')' fechando os parâmetros")

            # função precisa declarar o tipo de retorno
            if eh_funcao:
                self.consumir("C_DOIS_PONTOS", "':' antes do tipo de retorno da função")
                self.tipo()
            elif self.verificar("C_DOIS_PONTOS"):
                linha, atomo, _ = self.atual()
                self.erros.append(
                    ErroSintatico(linha, "';' (PROCEDURE não tem tipo de retorno)", atomo)
                )
                self.avancar()
                self.tipo()

            self.consumir("C_PONTO_E_VIRGULA", "';' após o cabeçalho da subrotina")
        except ErroSintatico:
            self.sincronizar("C_BEGIN", "C_VAR")

        self.bloco()

        try:
            self.consumir("C_PONTO_E_VIRGULA", "';' após o END da subrotina")
        except ErroSintatico:
            self.sincronizar("C_BEGIN", "C_PROCEDURE", "C_FUNCTION")

    def comando_composto(self):
        # comando_composto -> BEGIN [comando {';' comando}] END
        try:
            self.consumir("C_BEGIN", "a palavra reservada BEGIN")
        except ErroSintatico:
            self.sincronizar("C_END")
            if self.verificar("C_END"):
                self.avancar()
            return

        if not self.verificar("C_END"):
            self.comando()
            self.pular_erro_lexico_solto()
            while True:
                if self.verificar("C_PONTO_E_VIRGULA"):
                    self.avancar()
                    self.pular_erro_lexico_solto()
                    if self.verificar("C_END"):
                        break  # ';' antes do END é permitido em Pascal
                    self.comando()
                    self.pular_erro_lexico_solto()
                elif self.verificar("C_END", "C_PONTO", "C_EOF"):
                    break
                else:
                    # sobrou um token solto depois de um comando completo
                    # (ex: 'Idade := Idade @ 3'): reporta UM erro e pula ate o
                    # proximo ';' ou END, sem derrubar o resto do programa
                    linha, atomo, _ = self.atual()
                    self.erros.append(
                        ErroSintatico(linha, "';' ou END depois do comando", atomo)
                    )
                    self.sincronizar("C_PONTO")

        try:
            self.consumir("C_END", "a palavra reservada END fechando o BEGIN")
        except ErroSintatico:
            self.sincronizar("C_END", "C_PONTO")
            if self.verificar("C_END"):
                self.avancar()

    def comando(self):
        # comando -> atribuição | chamada | if | while | for | repeat | begin...end
        self.pular_erro_lexico_solto()
        try:
            if self.verificar("C_BEGIN"):
                self.comando_composto()
            elif self.verificar("C_IF"):
                self.comando_if()
            elif self.verificar("C_WHILE"):
                self.comando_while()
            elif self.verificar("C_FOR"):
                self.comando_for()
            elif self.verificar("C_REPEAT"):
                self.comando_repeat()
            elif self.verificar("C_CASE"):
                self.comando_case()
            elif self.simbolo() in ROTINAS:
                self.chamada_rotina()
            elif self.verificar("C_IDENT"):
                self.atribuicao_ou_chamada()
            elif self.verificar("C_PONTO_E_VIRGULA", "C_END"):
                pass  # comando vazio, permitido
            else:
                linha, atomo, _ = self.atual()
                erro = ErroSintatico(linha, "um comando", atomo)
                self.erros.append(erro)
                raise erro
        except ErroSintatico:
            self.sincronizar("C_PONTO_E_VIRGULA", "C_END", "C_ELSE", "C_UNTIL")

    def atribuicao_ou_chamada(self):
        # ident ':=' expressao | ident[(args)]
        self.avancar()  # consome o identificador

        # índice de array: A[i]
        while self.verificar("C_ABRE_COLCHETE"):
            self.avancar()
            self.expressao()
            self.consumir("C_FECHA_COLCHETE", "']' fechando o índice")

        # campo de record: A.B
        while self.verificar("C_PONTO"):
            self.avancar()
            self.consumir("C_IDENT", "o nome do campo após o '.'")

        if self.verificar("C_ATRIBUICAO"):
            self.avancar()
            self.expressao()
        elif self.verificar("C_ABRE_PARENTESES"):
            self.avancar()
            if not self.verificar("C_FECHA_PARENTESES"):
                self.expressao()
                while self.verificar("C_VIRGULA"):
                    self.avancar()
                    self.expressao()
            self.consumir("C_FECHA_PARENTESES", "')' fechando os argumentos")
        elif self.verificar("C_IGUAL"):
            # erro clássico: usar '=' onde deveria ser ':='
            linha, atomo, _ = self.atual()
            self.erros.append(
                ErroSintatico(linha, "':=' para atribuir (o '=' é só comparação)", atomo)
            )
            self.avancar()
            self.expressao()
        # ident sozinho também é válido (chamada de procedimento sem argumentos)

    def chamada_rotina(self):
        # WRITELN(...) | CLRSCR | DELAY(500) ...
        self.avancar()  # consome o nome da rotina
        if self.verificar("C_ABRE_PARENTESES"):
            self.avancar()
            if not self.verificar("C_FECHA_PARENTESES"):
                self.expressao()
                while self.verificar("C_VIRGULA"):
                    self.avancar()
                    self.expressao()
            self.consumir("C_FECHA_PARENTESES", "')' fechando a chamada")

    def comando_if(self):
        # if -> IF expressao THEN comando [ELSE comando]
        self.avancar()  # consome IF
        self.expressao()
        self.consumir("C_THEN", "a palavra THEN após a condição do IF")
        self.comando()
        if self.verificar("C_ELSE"):
            self.avancar()
            self.comando()

    def comando_while(self):
        # while -> WHILE expressao DO comando
        self.avancar()  # consome WHILE
        self.expressao()
        self.consumir("C_DO", "a palavra DO após a condição do WHILE")
        self.comando()

    def comando_for(self):
        # for -> FOR ident ':=' expressao (TO|DOWNTO) expressao DO comando
        self.avancar()  # consome FOR
        self.consumir("C_IDENT", "a variável de controle do FOR")
        self.consumir("C_ATRIBUICAO", "':=' após a variável do FOR")
        self.expressao()
        if self.verificar("C_TO", "C_DOWNTO"):
            self.avancar()
        else:
            linha, atomo, _ = self.atual()
            erro = ErroSintatico(linha, "TO ou DOWNTO no FOR", atomo)
            self.erros.append(erro)
            raise erro
        self.expressao()
        self.consumir("C_DO", "a palavra DO após o limite do FOR")
        self.comando()

    def comando_repeat(self):
        # repeat -> REPEAT comando {';' comando} UNTIL expressao
        self.avancar()  # consome REPEAT
        self.comando()
        while self.verificar("C_PONTO_E_VIRGULA"):
            self.avancar()
            if self.verificar("C_UNTIL"):
                break
            self.comando()
        self.consumir("C_UNTIL", "a palavra UNTIL fechando o REPEAT")
        self.expressao()

    def comando_case(self):
        # case -> CASE expressao OF {rotulo ':' comando ';'} END
        self.avancar()  # consome CASE
        self.expressao()
        self.consumir("C_OF", "a palavra OF após a expressão do CASE")
        while not self.verificar("C_END", "C_EOF"):
            try:
                self.expressao()  # rótulo do case
                while self.verificar("C_VIRGULA"):
                    self.avancar()
                    self.expressao()
                self.consumir("C_DOIS_PONTOS", "':' após o rótulo do CASE")
                self.comando()
                if self.verificar("C_PONTO_E_VIRGULA"):
                    self.avancar()
                else:
                    break
            except ErroSintatico:
                self.sincronizar("C_PONTO_E_VIRGULA", "C_END")
                if self.verificar("C_PONTO_E_VIRGULA"):
                    self.avancar()
        self.consumir("C_END", "a palavra END fechando o CASE")

    def expressao(self):
        # expressao -> simples [op_relacional simples]
        self.expressao_simples()
        if self.simbolo() in OP_RELACIONAL:
            self.avancar()
            self.expressao_simples()

    def pode_iniciar_fator(self):
        # true se o token atual e um dos que podem comecar um fator
        # (usado pra saber se, depois de pular um caractere invalido no
        # meio de uma conta, ainda sobrou "mais uma coisa" pra consumir
        # como se um operador estivesse implicito ali)
        s = self.simbolo()
        if s in ("C_IDENT", "C_INTEGER", "C_REAL", "C_STRING",
                  "C_TRUE", "C_FALSE", "C_NIL", "C_ABRE_PARENTESES", "C_NOT"):
            return True
        if s in ROTINAS:
            return True
        return s in ("C_KEYPRESSED", "C_LENGTH", "C_RANDOM", "C_SIZEOF",
                      "C_WHEREX", "C_WHEREY", "C_PARAMCOUNT", "C_PARAMSTR",
                      "C_MAXAVAIL", "C_MEMAVAIL", "C_HI", "C_LO")

    def expressao_simples(self):
        # simples -> [+|-] termo {(+|-|OR) termo}
        if self.verificar("C_MAIS", "C_MENOS"):
            self.avancar()  # sinal unário
        self.termo()
        while True:
            pulou_erro = self.simbolo().startswith("C_ERRO")
            self.pular_erro_lexico_solto()
            if self.simbolo() in OP_SOMA:
                self.avancar()
                self.termo()
                continue
            if pulou_erro and self.pode_iniciar_fator():
                # caractere invalido no meio da conta: trata como se
                # fosse um operador implicito, pra nao perder o proximo termo
                self.termo()
                continue
            break

    def termo(self):
        # termo -> fator {(*|/|DIV|MOD|AND) fator}
        self.fator()
        while True:
            pulou_erro = self.simbolo().startswith("C_ERRO")
            self.pular_erro_lexico_solto()
            if self.simbolo() in OP_MULT:
                self.avancar()
                self.fator()
                continue
            if pulou_erro and self.pode_iniciar_fator():
                self.fator()
                continue
            break

    def fator(self):
        # fator -> ident[(args)] | número | string | '(' expressao ')' | NOT fator
        # (+ token de erro lexico, absorvido quieto pra nao gerar erro em cascata)
        if self.verificar("C_IDENT"):
            self.avancar()
            while self.verificar("C_ABRE_COLCHETE"):
                self.avancar()
                self.expressao()
                self.consumir("C_FECHA_COLCHETE", "']' fechando o índice")
            while self.verificar("C_PONTO"):
                self.avancar()
                self.consumir("C_IDENT", "o nome do campo após o '.'")
            if self.verificar("C_ABRE_PARENTESES"):
                self.avancar()
                if not self.verificar("C_FECHA_PARENTESES"):
                    self.expressao()
                    while self.verificar("C_VIRGULA"):
                        self.avancar()
                        self.expressao()
                self.consumir("C_FECHA_PARENTESES", "')' fechando os argumentos")
            return

        if self.verificar("C_INTEGER", "C_REAL", "C_STRING", "C_TRUE", "C_FALSE", "C_NIL"):
            self.avancar()
            return

        # funções que podem aparecer dentro de expressão: LENGTH(x), RANDOM(10)...
        if self.simbolo() in ROTINAS or self.verificar("C_KEYPRESSED", "C_LENGTH",
                                                       "C_RANDOM", "C_SIZEOF",
                                                       "C_WHEREX", "C_WHEREY",
                                                       "C_PARAMCOUNT", "C_PARAMSTR",
                                                       "C_MAXAVAIL", "C_MEMAVAIL",
                                                       "C_HI", "C_LO"):
            self.avancar()
            if self.verificar("C_ABRE_PARENTESES"):
                self.avancar()
                if not self.verificar("C_FECHA_PARENTESES"):
                    self.expressao()
                    while self.verificar("C_VIRGULA"):
                        self.avancar()
                        self.expressao()
                self.consumir("C_FECHA_PARENTESES", "')' fechando os argumentos")
            return

        if self.verificar("C_ABRE_PARENTESES"):
            self.avancar()
            self.expressao()
            self.consumir("C_FECHA_PARENTESES", "')' fechando a expressão")
            return

        if self.verificar("C_NOT"):
            self.avancar()
            self.fator()
            return

        # token que o LEXICO ja marcou como invalido (numero colado com
        # letra, string nao fechada...): absorve no lugar de valor, sem
        # levantar erro sintatico - o erro ja foi contabilizado no lexico.
        if self.simbolo().startswith("C_ERRO"):
            self.avancar()
            return

        linha, atomo, _ = self.atual()
        erro = ErroSintatico(linha, "um valor (variável, número, string ou '(')", atomo)
        self.erros.append(erro)
        raise erro


    def analisar(self):
        # roda a análise completa e devolve a lista de erros encontrados
        try:
            self.programa()
        except ErroSintatico:
            pass  # já foi registrado em self.erros
        except RecursionError:
            self.erros.append(
                ErroSintatico(self.atual()[0], "estrutura válida", "(análise interrompida)")
            )
        return self.erros

# Saída: terminal colorido e relatório HTML

def print_resultado(erros_sint, erros_lex, nome_arquivo):
    print(ANSI["bold"] + f"ANÁLISE SINTÁTICA - {nome_arquivo}" + ANSI["reset"])
    print(ANSI["dim"] + "-" * 70 + ANSI["reset"])

    if erros_lex:
        print(ANSI["amarelo"] + f"\nErros LÉXICOS encontrados ({len(erros_lex)}):" + ANSI["reset"])
        for linha, atomo, simbolo in erros_lex:
            atomo_curto = atomo if len(atomo) <= 30 else atomo[:27] + "..."
            print(f"  {ANSI['vermelho']}Linha {linha}: '{atomo_curto}' -> {simbolo}{ANSI['reset']}")

    if not erros_sint:
        print(ANSI["verde"] + "\nNenhum erro de sintaxe. Estrutura do programa está correta!" + ANSI["reset"])
    else:
        print(ANSI["vermelho"] + f"\nErros SINTÁTICOS encontrados ({len(erros_sint)}):" + ANSI["reset"])
        for e in erros_sint:
            print(f"  {ANSI['vermelho']}Linha {e.linha}:{ANSI['reset']} esperava "
                  f"{ANSI['bold']}{e.esperado}{ANSI['reset']}, "
                  f"encontrou '{ANSI['amarelo']}{e.encontrado}{ANSI['reset']}'")

    print()


def save_html(erros_sint, erros_lex, path, nome_arquivo, total_tokens):
    import datetime
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if erros_sint:
        linhas_sint = "".join(
            f"<tr><td>{e.linha}</td><td>{escapar(e.esperado)}</td>"
            f"<td><code>{escapar(e.encontrado)}</code></td></tr>"
            for e in erros_sint
        )
        bloco_sint = f"""
        <h2>Erros sintáticos</h2>
        <table>
          <thead><tr><th>LINHA</th><th>ESPERAVA</th><th>ENCONTROU</th></tr></thead>
          <tbody>{linhas_sint}</tbody>
        </table>"""
    else:
        bloco_sint = ('<div class="ok">Nenhum erro de sintaxe encontrado. '
                      'A estrutura do programa está correta.</div>')

    if erros_lex:
        linhas_lex = "".join(
            f"<tr><td>{linha}</td><td><code>{escapar(atomo[:60])}</code></td>"
            f"<td>{escapar(simbolo)}</td></tr>"
            for linha, atomo, simbolo in erros_lex
        )
        bloco_lex = f"""
        <h2>Erros léxicos</h2>
        <table>
          <thead><tr><th>LINHA</th><th>ÁTOMO</th><th>PROBLEMA</th></tr></thead>
          <tbody>{linhas_lex}</tbody>
        </table>"""
    else:
        bloco_lex = ""

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Analisador Sintatico - {escapar(nome_arquivo)}</title>
<style>
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#0f1117; color:#e6e6e6; padding:32px; }}
  h1 {{ margin-bottom:4px; }}
  h2 {{ margin-top:32px; font-size:18px; color:#c9cdd4; }}
  .sub {{ color:#9aa0a6; margin-bottom:24px; }}
  .resumo {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
  .card {{ background:#1a1d27; border-radius:10px; padding:14px 20px; min-width:150px; }}
  .card .num {{ font-size:28px; font-weight:700; }}
  .card .label {{ color:#9aa0a6; font-size:13px; }}
  table {{ border-collapse:collapse; width:100%; background:#1a1d27;
           border-radius:10px; overflow:hidden; margin-top:12px; }}
  th, td {{ padding:9px 14px; text-align:left; border-bottom:1px solid #2a2d3a; font-size:14px; }}
  th {{ background:#22263a; }}
  code {{ background:#22263a; padding:2px 6px; border-radius:4px; color:#d4a72c; }}
  .ok {{ background:#14331c; border-left:4px solid #2fb344; padding:16px 20px;
         border-radius:8px; margin-top:12px; font-size:15px; }}
</style>
</head>
<body>
  <h1>Analisador Sintatico &mdash; Turbo Pascal</h1>
  <div class="sub">Arquivo: {escapar(nome_arquivo)} &nbsp;|&nbsp; Gerado em {agora}</div>

  <div class="resumo">
    <div class="card"><div class="num">{total_tokens}</div><div class="label">Átomos analisados</div></div>
    <div class="card"><div class="num" style="color:{'#e5484d' if erros_sint else '#2fb344'}">{len(erros_sint)}</div><div class="label">Erros sintáticos</div></div>
    <div class="card"><div class="num" style="color:{'#d4a72c' if erros_lex else '#2fb344'}">{len(erros_lex)}</div><div class="label">Erros léxicos</div></div>
  </div>
  {bloco_sint}
  {bloco_lex}
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def escapar(texto):
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def save_html_todos(resultados, path):
    # Um unico HTML com todos os arquivos analisados, um bloco por arquivo.
    # resultados = lista de (nome_arquivo, erros_sint, erros_lex, total_tokens)
    import datetime
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    total_sint = sum(len(r[1]) for r in resultados)
    total_lex = sum(len(r[2]) for r in resultados)

    linhas_indice = "".join(
        f"<tr><td>{escapar(nome)}</td><td>{ntok}</td>"
        f"<td style=\"color:{'#e5484d' if es else '#2fb344'}\">{len(es)}</td>"
        f"<td style=\"color:{'#d4a72c' if el else '#2fb344'}\">{len(el)}</td></tr>"
        for nome, es, el, ntok in resultados
    )

    secoes = []
    for nome, erros_sint, erros_lex, ntok in resultados:
        if erros_sint:
            linhas = "".join(
                f"<tr><td>{e.linha}</td><td>{escapar(e.esperado)}</td>"
                f"<td><code>{escapar(e.encontrado)}</code></td></tr>"
                for e in erros_sint
            )
            b_sint = f"""
        <h3>Erros sintáticos</h3>
        <table>
          <thead><tr><th>LINHA</th><th>ESPERAVA</th><th>ENCONTROU</th></tr></thead>
          <tbody>{linhas}</tbody>
        </table>"""
        else:
            b_sint = ('<div class="ok">Nenhum erro de sintaxe encontrado. '
                      'A estrutura do programa está correta.</div>')

        if erros_lex:
            linhas = "".join(
                f"<tr><td>{linha}</td><td><code>{escapar(atomo[:60])}</code></td>"
                f"<td>{escapar(simbolo)}</td></tr>"
                for linha, atomo, simbolo in erros_lex
            )
            b_lex = f"""
        <h3>Erros léxicos</h3>
        <table>
          <thead><tr><th>LINHA</th><th>ÁTOMO</th><th>PROBLEMA</th></tr></thead>
          <tbody>{linhas}</tbody>
        </table>"""
        else:
            b_lex = ""

        secoes.append(f"""
  <section>
    <h2>{escapar(nome)}</h2>
    <div class="resumo">
      <div class="card"><div class="num">{ntok}</div><div class="label">Átomos analisados</div></div>
      <div class="card"><div class="num" style="color:{'#e5484d' if erros_sint else '#2fb344'}">{len(erros_sint)}</div><div class="label">Erros sintáticos</div></div>
      <div class="card"><div class="num" style="color:{'#d4a72c' if erros_lex else '#2fb344'}">{len(erros_lex)}</div><div class="label">Erros léxicos</div></div>
    </div>
    {b_sint}
    {b_lex}
  </section>""")

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Analisador Sintatico - Todos os Testes</title>
<style>
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#0f1117; color:#e6e6e6; padding:32px; }}
  h1 {{ margin-bottom:4px; }}
  h2 {{ margin-top:48px; font-size:22px; color:#e6e6e6; border-bottom:1px solid #2a2d3a; padding-bottom:8px; }}
  h3 {{ margin-top:24px; font-size:16px; color:#c9cdd4; }}
  .sub {{ color:#9aa0a6; margin-bottom:24px; }}
  .resumo {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
  .card {{ background:#1a1d27; border-radius:10px; padding:14px 20px; min-width:150px; }}
  .card .num {{ font-size:28px; font-weight:700; }}
  .card .label {{ color:#9aa0a6; font-size:13px; }}
  table {{ border-collapse:collapse; width:100%; background:#1a1d27;
           border-radius:10px; overflow:hidden; margin-top:12px; }}
  th, td {{ padding:9px 14px; text-align:left; border-bottom:1px solid #2a2d3a; font-size:14px; }}
  th {{ background:#22263a; }}
  code {{ background:#22263a; padding:2px 6px; border-radius:4px; color:#d4a72c; }}
  .ok {{ background:#14331c; border-left:4px solid #2fb344; padding:16px 20px;
         border-radius:8px; margin-top:12px; font-size:15px; }}
</style>
</head>
<body>
  <h1>Analisador Sintatico &mdash; Turbo Pascal</h1>
  <div class="sub">{len(resultados)} arquivos analisados &nbsp;|&nbsp; Gerado em {agora}</div>

  <div class="resumo">
    <div class="card"><div class="num">{len(resultados)}</div><div class="label">Arquivos</div></div>
    <div class="card"><div class="num" style="color:{'#e5484d' if total_sint else '#2fb344'}">{total_sint}</div><div class="label">Erros sintáticos (total)</div></div>
    <div class="card"><div class="num" style="color:{'#d4a72c' if total_lex else '#2fb344'}">{total_lex}</div><div class="label">Erros léxicos (total)</div></div>
  </div>

  <table>
    <thead><tr><th>ARQUIVO</th><th>ÁTOMOS</th><th>ERROS SINTÁTICOS</th><th>ERROS LÉXICOS</th></tr></thead>
    <tbody>{linhas_indice}</tbody>
  </table>
  {''.join(secoes)}
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def expandir_arquivos(padroes):
    # o PowerShell nao expande '*.pas' sozinho, entao expandimos aqui
    arquivos = []
    for padrao in padroes:
        if any(c in padrao for c in "*?["):
            arquivos.extend(sorted(glob.glob(padrao)))
        else:
            arquivos.append(padrao)
    return arquivos


def analisar_arquivo(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        source = f.read()
    tokens = tokenize(source)
    p = Parser(tokens)
    erros_sint = p.analisar()
    return erros_sint, p.erros_lexicos, len(tokens)


def main():
    parser_cli = argparse.ArgumentParser(description="Analisador sintático de Pascal")
    parser_cli.add_argument("arquivos", nargs="+",
                            help="Um ou mais arquivos .pas/.txt (aceita *.pas)")
    parser_cli.add_argument("--html", help="Caminho para salvar o relatório .html", default=None)
    args = parser_cli.parse_args()

    arquivos = expandir_arquivos(args.arquivos)
    if not arquivos:
        print("Nenhum arquivo encontrado.")
        sys.exit(1)

    resultados = []
    for caminho in arquivos:
        erros_sint, erros_lex, ntok = analisar_arquivo(caminho)
        print_resultado(erros_sint, erros_lex, caminho)
        resultados.append((os.path.basename(caminho), erros_sint, erros_lex, ntok))

    pasta = os.path.dirname(arquivos[0])
    if len(arquivos) == 1:
        # um arquivo so: "Analisador Sintatico - NomeDoArquivo.html"
        caminho_html = args.html
        if not caminho_html:
            base = os.path.splitext(os.path.basename(arquivos[0]))[0]
            caminho_html = os.path.join(pasta, f"Analisador Sintatico - {base}.html")
        nome, erros_sint, erros_lex, ntok = resultados[0]
        save_html(erros_sint, erros_lex, caminho_html, nome, ntok)
    else:
        # varios arquivos: UM unico HTML com todos juntos
        caminho_html = args.html or os.path.join(pasta, "Analisador Sintatico - Todos os Testes.html")
        save_html_todos(resultados, caminho_html)
    print(f"Relatório HTML salvo em: {caminho_html}")

    # código de saída: 0 = tudo certo, 1 = achou erro (útil pra automatizar)
    tem_erro = any(r[1] or r[2] for r in resultados)
    sys.exit(1 if tem_erro else 0)


if __name__ == "__main__":
    main()