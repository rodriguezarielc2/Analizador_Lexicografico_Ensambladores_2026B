# Analizador de ensamblador EMU8086

Aplicación de escritorio local en Python/Tkinter para revisar un programa `.asm` en una sola ventana. Presenta los tokens, los diagnósticos de sintaxis y semántica, la tabla de símbolos y el listado hexadecimal por segmento.

## Iniciar

Requiere Python 3.11 o posterior con Tkinter disponible. No instala paquetes para ejecutar la aplicación.

En Windows, abre `run.bat`. También puedes iniciarla desde PowerShell en esta carpeta:

```powershell
python main.py
```

Usa **Abrir .asm** para cargar un archivo. **Analizar** vuelve a procesar el contenido actual. Los `INCLUDE` se buscan primero en la carpeta del archivo principal.

## Qué muestra

- **Etapa 1:** lexemas, categoría y valor; los separadores de coma internos se ocultan en la tabla.
- **Etapa 2:** errores con línea, fase, código y mensaje. Si hay un error que impida ensamblar, no aparece código máquina parcial.
- **Etapa 3:** símbolos con segmento y offset, y bytes en hexadecimal. Las reservas `?` aparecen como `??`.
- Direcciones independientes para `.data`, `.code`, `.stack` y segmentos con nombre; los saltos relativos entre segmentos se diagnostican.
- Preprocesamiento básico de macros e `INCLUDE`, datos `DB/DW/DD`, `DUP`, `EQU`, `ORG`, etiquetas y procedimientos.
- Codificación de formas 8086 incluidas en `tests/fixtures/emu8086_supported_forms.json`: transferencia, aritmética/lógica, pila, saltos, cadenas, interrupciones, puertos, banderas, segmentos, ModR/M y prefijos `REP`/`LOCK`.

## Límites de esta primera versión

El objetivo de sintaxis es EMU8086 4.08, pero esta entrega **no es un reemplazo completo del compilador EMU8086**. El entorno de construcción no incluye el ejecutable de EMU8086, así que los bytes de la aplicación se verifican contra casos dorados propios y no mediante una comparación automática con la versión 4.08.

La tabla JSON es el catálogo verificable de formas codificadas. Una forma que no esté implementada produce un diagnóstico y no bytes inventados. Las directivas `.startup` y `.exit` se reconocen, pero su expansión no está implementada y bloquea la salida máquina. `INCLUDE` funciona para archivos presentes; no se distribuye la biblioteca `emu8086.inc`. Las directivas `#make_*` y de configuración `#CS=...`/`#MEM=...` se reconocen, pero no generan `.com`, `.bin`, `.exe`, `.binf` ni aplican estado inicial del emulador.

No ejecuta instrucciones. No guarda archivos objeto ni binarios: el hexadecimal solo se muestra en pantalla.

## Pruebas

Desde esta carpeta:

```powershell
python -m unittest discover -s tests -v
```

## Crear un ejecutable opcional

Si quieres crear un `.exe`, instala PyInstaller y ejecuta `build.ps1`:

```powershell
python -m pip install pyinstaller
./build.ps1
```

El ejecutable se crea en `dist/Analizador_EMU8086.exe`. PyInstaller no está incluido ni se instala automáticamente.

## Referencia de EMU8086

- [Ayuda del compilador EMU8086: formatos de salida y directivas `#make_*`](https://surendrajat.github.io/emu8086/documentation/compiler.html)
