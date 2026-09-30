PROGRAM TesteGrande;

USES CRT;

CONST
  PI: REAL = 3.14;

TYPE
  TVetor = ARRAY[1..10] OF INTEGER;

VAR
  Idade: INTEGER;
  Nome: STRING;
  Ativo: BOOLEAN;
  Letra: CHAR;
  Vetor: TVetor;
  I, J: INTEGER;

PROCEDURE Saudacao(Nome: STRING);
BEGIN
  WRITELN('Ola, ', Nome);
END;

FUNCTION Dobro(N: INTEGER): INTEGER;
BEGIN
  Dobro := N * 2;
END;

BEGIN
  CLRSCR;
  Idade := 25;
  Nome := 'Fulano';
  Ativo := TRUE;

  { erro proposital: numero colado com letra }
  Idade := 42B;

  { erro proposital: outro numero colado com letra, no meio de uma conta }
  IF Idade > 18X THEN
    WRITELN('Maior de idade')
  ELSE
    WRITELN('Menor de idade');

  { erro proposital: caractere invalido / nao reconhecido pelo automato }
  Idade := Idade # 2;
  Idade := Idade @ 3;

  FOR I := 1 TO 10 DO
  BEGIN
    Vetor[I] := I * I;
  END;

  WHILE Idade > 0 DO
  BEGIN
    Idade := Idade - 1;
  END;

  REPEAT
    J := J + 1;
  UNTIL J >= 5;

  CASE Letra OF
    'A': WRITELN('Letra A');
    'B': WRITELN('Letra B');
  END;

  GOTOXY(10, 5);
  DELAY(500);
  RANDOMIZE;
  Idade := RANDOM(100);
  WRITELN('Random: ', Idade);
  WRITELN('Tamanho do nome: ', LENGTH(Nome));

  IF KEYPRESSED THEN
    HALT;

  Saudacao(Nome);
  WRITELN('Dobro de 21: ', Dobro(21));

  { erro proposital: string sem fechar aspas -- fica por ultimo, pois "engole"
    tudo que vem depois ate o fim do arquivo (comportamento correto de lexer) }
  Nome := 'esqueci de fechar;
END.
