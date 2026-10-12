# Analizador lexicográfico - Fase 1

Aplicación local de Windows para la **separación** e **identificación** de elementos de un programa fuente de ensamblador.

## Abrir

Ejecuta `run.bat` o `dist/AnalizadorFase1.exe`. Para la entrega, descomprime `dist/Entrega_Fase1.zip` y ejecuta `AnalizadorFase1.exe` en la carpeta extraída. Selecciona el archivo fuente. El selector muestra todos los tipos de archivo; la aplicación solo acepta archivos existentes con extensión `.ens` (también acepta `.ENS`). Se puede abrir un archivo desde cualquier carpeta.

La ventana presenta el código fuente y la lista de elementos. El código se muestra en páginas de 25 líneas y la lista en páginas de 50 elementos. La navegación de ambos paneles es independiente. Cada elemento conserva su número global, su lexema y el tipo identificado.

## Instrucciones del equipo 2

El analizador reconoce como **Instrucción** únicamente los 20 mnemónicos asignados al equipo 2, definidos en `instrucciones_equipo.txt`:

`CBW`, `CLC`, `LODSB`, `LODSW`, `STOSB`, `AAA`, `POP`, `IDIV`, `INT`, `AND`, `ADC`, `LEA`, `LES`, `JNZ`, `JZ`, `LOOPNZ`, `JGE`, `JNA`, `JNL`, `JE`.

La comparación ignora mayúsculas/minúsculas. Los mnemónicos no incluidos se clasifican como **Símbolo**, como pide la actividad.

## Criterios implementados

- Elimina comentarios que empiezan con punto y coma, excepto los caracteres dentro de literales.
- Omite espacio, coma y dos puntos como separadores.
- Conserva juntos `.code segment`, `.data segment`, `.stack segment`, `byte ptr`, `word ptr`, `DUP(...)`, `[xxx]`, cadenas y literales de carácter.
- Identifica pseudoinstrucciones, registros 8086, solo las instrucciones asignadas, símbolos y constantes decimales, hexadecimales, binarias, de carácter y de cadena.
- Muestra **Elemento no identificado** o **Elemento inválido** para los lexemas que no reconoce.

## Compilar y probar

Requiere Windows con .NET Framework 4.x. Para compilar el ejecutable y correr las pruebas desde PowerShell:

```powershell
./build.ps1
```

El script genera `dist/Entrega_Fase1.zip` con código fuente, pruebas, instrucciones de compilación y ejecutable. Verifica que el ZIP no exceda 5 MB.

La aplicación cubre la Función 1 de la Fase 1. No ejecuta ni ensambla el programa.
