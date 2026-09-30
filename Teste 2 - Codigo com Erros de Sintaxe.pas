PROGRAM TesteErros;

VAR
  M INTEGER;
  N: ;

BEGIN
  M = 10;

  IF M > 5
    WRITELN('faltou o THEN');

  FOR M 1 TO 10 DO
    WRITELN(M);

  WHILE M > 0
    M := M - 1;

  WRITELN('faltou fechar o parenteses';

  REPEAT
    M := M + 1;
END.
