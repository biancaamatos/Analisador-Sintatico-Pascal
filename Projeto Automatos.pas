PROGRAM EXEMPLO5;
VAR
  M: INTEGER;
  NOME: STRING;

FUNCTION F(N: INTEGER): INTEGER;
BEGIN
  IF N > 123A THEN
    WRITELN('erro proposital acima')
  ELSE
    F := N * 2;
END;

BEGIN
  M := 10;
  WRITELN('Resultado: ', F(M));
END.
