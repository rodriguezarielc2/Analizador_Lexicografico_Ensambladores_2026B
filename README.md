# Analizador lexicográfico de ensamblador — Fase 1

Proyecto del **Equipo 2**, actualizado el 20 de octubre de 2026 para separar e identificar elementos de archivos `.ens`.

## Abrir

Ejecuta `run.bat` o `dist/AnalizadorFase1.exe`. Conserva `dist/instrucciones_equipo.txt` junto al ejecutable. El selector muestra todos los archivos y solo abre archivos existentes con extensión `.ens`, sin restringir la carpeta.

El código fuente y la lista de elementos se muestran simultáneamente, con paginación independiente y numeración continua. El zoom ajusta ambos paneles. Si una línea ocupa más que la pantalla, el panel de fuente permite recorrerla dentro de su página.

Para usar la entrega, extrae `dist/Entrega_Fase1.zip` y ejecuta `AnalizadorFase1.exe`. El ZIP contiene el ejecutable, los dos archivos fuente de C# y `instrucciones_equipo.txt`, que debe permanecer junto al ejecutable. Las pruebas y los ejemplos se conservan en el proyecto para compilar y revisar; no se agregan a la entrega.

## Criterios aplicados

La consigna de Moodle de Fase 1 y las aclaraciones de la **clase 17** definen la actividad. La presentación **Aspectos generales del lenguaje ensamblador** completa las reglas del lenguaje. Cuando un ejemplo de la presentación difiere de una corrección de clase, se aplica la corrección de clase. La compatibilidad con EMU8086 no es un requisito de aceptación; el nombre de esta carpeta es histórico.

| Elemento | Regla aplicada y ejemplo |
| --- | --- |
| Separadores | Espacio, tabulador, salto de línea, coma y dos puntos. Los separadores internos se conservan en los compuestos cerrados. |
| Comentarios | Desde `;` hasta el fin de línea, excepto dentro de una constante con comillas cerradas. Se eliminan también cuando hay un compuesto incompleto antes del comentario. |
| Segmentos | Solo `.code segment`, `.data segment` y `.stack segment`, completos y en una misma línea. No se reconoce el prefijo de `segment$`, ni `.stacks segment`. |
| Pseudoinstrucciones simples | `DB DW EQU DUP ENDS MACRO ENDM PROC ENDP LOCAL`. `BYTE PTR` y `WORD PTR` se reconocen como frases completas. `.model` no pertenece al catálogo. |
| Instrucciones | Solo las veinte asignadas al Equipo 2. `MOV`, `JE` y otros mnemónicos no asignados se consideran símbolos cuando cumplen la regla de nombres. |
| Registros | `AX AH AL BX BH BL CX CH CL DX DH DL SI DI SP BP SS CS DS ES`, según la diapositiva 10. |
| Símbolos | Inicio alfabético y máximo de diez caracteres. `7tecla` y `abcdefghijk` son inválidos. Se admiten letras, dígitos y guion bajo interior. |
| Etiquetas | Se conserva `:` y se indica `Etiqueta`. El nombre cumple las reglas de símbolos y no es una palabra reservada. Ejemplo: `lectura:`. |
| Decimal | Dígitos decimales, con signo opcional. Ejemplos: `42`, `-10`. `122d` y `0x20` no corresponden al formato de los materiales. |
| Hexadecimal | Cero inicial de notación, seguido de **dos o cuatro dígitos hexadecimales**, y `H`. Ejemplos: `045H`, `00FH`, `0AF23H`. El cero inicial no se cuenta entre esos dos o cuatro dígitos. |
| Binario | Exactamente **ocho o dieciséis dígitos** `0`/`1`, seguidos de `B`. Ejemplo: `10101010B`. |
| Constante carácter | Texto entre comillas simples o dobles del mismo tipo. Ambas formas tienen la misma categoría, incluyendo cadenas de varios caracteres. No se añaden escapes con barra inversa ni comillas duplicadas. |
| `DUP(...)` | Se mantiene completo, con paréntesis cerrados y contenido. El contador se separa: `10`, `dup(?)`. `dup (0)` se separa como `dup`, `(0)`. |
| Referencias | `[SI]` se identifica como `Referencia a registro`; una expresión cerrada como `[bx + si]`, como `Referencia a memoria`. |
| Elementos pegados | `dupy(0)`, `msg[2]` y `dup(0)resto` permanecen completos y se marcan inválidos. No se inventan espacios ni se rescata un prefijo válido. |
| Compuestos sin cierre | Se aplican los separadores que sí existen. `"presiona key...$ una vez` no se transforma en una cadena válida ni absorbe toda la línea. |

El signo numérico opcional se aplica antes de la notación de base. El guion bajo interior conserva los nombres usados en los ejemplos del proyecto; la diapositiva 8 especifica el inicio y la longitud, sin detallar por separado todos los caracteres intermedios.

Esta fase clasifica elementos. Los rangos dependientes de `DB`/`DW`, la legalidad de direcciones y operandos, las definiciones de símbolos y la generación de código corresponden a los análisis siguientes. El contenido de los compuestos se conserva; su validación sintáctica completa no se incorpora a esta fase.

## Fuentes de las reglas

- **Moodle: Proyecto Fase 1. Análisis lexicográfico (Función 1) 2026B**: selección de archivo, `.ens`, paginación, separación, categorías, compuestos y tabla del Equipo 2.
- **Clases 15, 16 y 17**: alcance de la fase y correcciones de las revisiones de todos los equipos. Clase 17: etiquetas, `[SI]`, `DUP`, segmentos completos, constantes, errores de separación y fuente visible.
- **Aspectos generales del lenguaje ensamblador.ppsx**: diapositivas 6, 8–12 y 27, para pseudoinstrucciones, nombres, constantes, registros, comentarios y separadores. Los ejemplos de `DUP (...)`, `10B`, `.DATA` y `21H` de otras diapositivas se contrastan con las restricciones posteriores de clase.
- **9674a88f-9ed4-493b-b61d-0a421dd547d5.pdf**: tablas de instrucciones y registros del 8086.
- **2f11532a-1d8d-45c0-8e6d-4f214193f8bd.pdf**: Appendix D, referencia de instrucciones y codificación.
- **ab78989c-d779-4e56-aa75-95dfa37e040d.pdf**: Intel Architecture Software Developer's Manual, volumen 2. Es una referencia de instrucciones; sus extensiones de otras arquitecturas no amplían el subconjunto asignado.

## Instrucciones del Equipo 2

`CBW CLC LODSB LODSW STOSB AAA POP IDIV INT AND ADC LEA LES JNZ JZ LOOPNZ JGE JNA JNL JB`

El archivo de la raíz es el catálogo canónico. La compilación copia ese mismo archivo a `dist` y al ZIP.

## Compilar y comprobar

Requiere Windows con .NET Framework 4.x. Desde PowerShell:

```powershell
./build.ps1
```

Compila la aplicación y ejecuta las pruebas de núcleo, la plantilla de clase y las pruebas de interfaz. Si una prueba falla, conserva el ejecutable y el ZIP anteriores. Los archivos de trabajo temporales se eliminan al terminar. Solo después de pasar las pruebas se actualizan `dist/AnalizadorFase1.exe`, el catálogo y `dist/Entrega_Fase1.zip`, cuyo límite es 5 MB.

Para empaquetar un ejecutable existente que ya corresponda a las fuentes actuales:

```powershell
./build.ps1 -SoloEmpaquetar
```

La opción `-SoloEmpaquetar` no compila ni ejecuta las pruebas.

## Comprobaciones realizadas

- 27 grupos de núcleo: clases de elementos, límites de compuestos, recuperación ante errores, comentarios, posiciones, numeración, archivos, plantilla y ejemplos.
- Plantilla original de la clase 17, conservada con sus errores intencionales.
- Familias de longitudes binarias y hexadecimales y los 256 valores hexadecimales de un byte.
- 600 entradas arbitrarias reproducibles: progreso, posiciones exactas, orden y ausencia de solapamientos.
- Compuestos de más de 40,000 caracteres y miles de aperturas incompletas, sin recursión.
- Interfaz: carga del Equipo 2, fuente y resultados simultáneos, zoom, paginación independiente, ventana mínima, líneas extensas, conservación de líneas vacías y codificaciones UTF-8, UTF-16 con BOM y Windows-1252.
- Ensayo de fallo intencional: no reemplaza la entrega anterior cuando una prueba falla.

Estas comprobaciones cubren los casos registrados y las familias descritas; no constituyen una garantía sobre toda entrada posible.

## Archivos

- `AnalysisCore.cs`: separación e identificación.
- `AnalizadorFase1.cs`: interfaz de Windows.
- `verificacion/tests/`: pruebas reproducibles y plantilla original de clase.
- `verificacion/ejemplos/`: entradas de demostración y casos inválidos.
- `dist/`: ejecutable, configuración y entrega ZIP.
