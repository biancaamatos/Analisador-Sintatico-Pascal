PROGRAM TesteCorreto;
USES CRT;

CONST
  MAX = 100;

VAR
  I, J: INTEGER;
  Nome: STRING;
  Media: REAL;

FUNCTION Dobro(N: INTEGER): INTEGER;
BEGIN
  Dobro := N * 2;
END;

PROCEDURE Saudacao(Texto: STRING);
BEGIN
  WRITELN('Ola, ', Texto);
END;

BEGIN
  CLRSCR;
  I := 10;
  Nome := 'Bianca';

  IF I > 5 THEN
    WRITELN('maior')
  ELSE
    WRITELN('menor');

  FOR J := 1 TO MAX DO
  BEGIN
    I := I + J;
  END;

  WHILE I > 0 DO
    I := I - 1;

  REPEAT
    J := J - 1;
  UNTIL J <= 0;

  Saudacao(Nome);
  WRITELN(Dobro(21));
END.
