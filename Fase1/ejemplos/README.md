# Ejemplos para la demostración

Abre estos archivos desde el analizador. La actividad y la aplicación usan la extensión **`.ens`**.

## Orden sugerido

1. `01_basico.ens`: muestra segmentos, etiquetas, separadores, comentarios, registros y constantes.
2. `02_compuestos_y_constantes.ens`: muestra los elementos compuestos que deben conservarse juntos.
3. `03_equipo2.ens`: contrasta los 20 mnemónicos asignados al equipo 2 con mnemónicos no asignados.
4. `04_elementos_invalidos.ens`: contiene errores intencionales para mostrar los resultados de identificación negativa.
5. `05_paginacion.ens`: tiene más de 25 líneas y más de 50 elementos para recorrer las páginas de ambos paneles.

## Qué señalar

- Los comentarios con `;` no aparecen en la lista de elementos.
- Espacios, comas y dos puntos separan los elementos y no aparecen como lexemas.
- `.data segment`, `.code segment`, `byte ptr`, `word ptr`, `dup(...)`, `[xxx]` y los literales entre comillas se conservan como un elemento.
- En el ejemplo del equipo 2, `MOV`, `ADD` y `RET` deben clasificarse como **Símbolo** porque no forman parte de los 20 mnemónicos asignados. `JZ`, en cambio, sí está asignado.
- En el ejemplo de errores, las entradas inválidas son deliberadas; usa los primeros tres archivos para mostrar el análisis normal.
- El ejemplo de paginación es una fuente de demostración lexicográfica; no pretende ser un programa ejecutable en EMU8086.
