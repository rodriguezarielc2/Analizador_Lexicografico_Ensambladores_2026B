using System;
using System.Collections.Generic;
using System.IO;
using AnalizadorFase1;

internal static class AnalysisCoreTests
{
    private static int _passed;

    private static void Main()
    {
        Run("separadores y numeracion", SeparatorsAndNumbering);
        Run("instrucciones asignadas y no asignadas", AssignedInstructionsOnly);
        Run("constantes numericas y literales", Constants);
        Run("comentarios fuera de literales", Comments);
        Run("lexemas compuestos", CompoundElements);
        Run("elementos invalidos", InvalidElements);
        Run("paginacion", Pagination);
        Run("validacion de archivo", FileValidation);
        Console.WriteLine("Pruebas correctas: " + _passed);
    }

    private static void Run(string name, Action test)
    {
        test();
        _passed++;
        Console.WriteLine("OK: " + name);
    }

    private static void SeparatorsAndNumbering()
    {
        List<Lexeme> items = AnalysisCore.Analyze("inicio: mov ax, 1", new string[] { "mov" });
        Equal(4, items.Count, "cantidad de elementos");
        Equal("inicio", items[0].Text, "etiqueta sin dos puntos");
        Equal("mov", items[1].Text, "instruccion");
        Equal("ax", items[2].Text, "registro");
        Equal("1", items[3].Text, "constante decimal");
        for (int i = 0; i < items.Count; i++)
            Equal(i + 1, items[i].Number, "numero global");
    }

    private static void AssignedInstructionsOnly()
    {
        List<Lexeme> items = AnalysisCore.Analyze("mov ax, add bx", new string[] { "MOV" });
        Equal("Instrucci\u00f3n", items[0].Type, "instruccion asignada");
        Equal("Registro", items[1].Type, "registro");
        Equal("S\u00edmbolo", items[2].Type, "instruccion no asignada como simbolo");
        Equal("Registro", items[3].Type, "registro");

        List<Lexeme> none = AnalysisCore.Analyze("mov", new string[0]);
        Equal("S\u00edmbolo", none[0].Type, "sin lista no se reconoce ninguna instruccion");

        List<Lexeme> registers = AnalysisCore.Analyze("al ah bl bh cl ch dl dh ax bx cx dx si di bp sp ip cs ds es ss flags", new string[0]);
        Equal(22, registers.Count, "registros EMU8086 comunes");
        foreach (Lexeme register in registers) Equal("Registro", register.Type, "categoria de registro " + register.Text);
    }

    private static void Constants()
    {
        List<Lexeme> items = AnalysisCore.Analyze("db 42, 0FFh, 101b, 0x20, 'A', \"texto\"", new string[0]);
        Equal(7, items.Count, "cantidad de constantes y pseudoinstruccion");
        Equal("Pseudoinstrucci\u00f3n", items[0].Type, "db");
        Equal("Constante decimal", items[1].Type, "decimal");
        Equal("Constante hexadecimal", items[2].Type, "hexadecimal sufijo");
        Equal("Constante binaria", items[3].Type, "binaria sufijo");
        Equal("Constante hexadecimal", items[4].Type, "hexadecimal prefijo");
        Equal("Constante car\u00e1cter", items[5].Type, "caracter");
        Equal("Constante de cadena", items[6].Type, "cadena");

        List<Lexeme> signed = AnalysisCore.Analyze("db -12, +0FFh, -101b", new string[0]);
        Equal("Constante decimal", signed[1].Type, "decimal con signo");
        Equal("Constante hexadecimal", signed[2].Type, "hexadecimal con signo");
        Equal("Constante binaria", signed[3].Type, "binaria con signo");
    }

    private static void Comments()
    {
        List<Lexeme> items = AnalysisCore.Analyze("db \"A;B\", 'C' ; comentario\nmov ax, 2;fin", new string[] { "mov" });
        Equal(6, items.Count, "comentarios no producen elementos");
        Equal("\"A;B\"", items[1].Text, "punto y coma dentro de cadena");
        Equal("'C'", items[2].Text, "caracter antes del comentario");
        Equal("mov", items[3].Text, "segunda linea");
    }

    private static void CompoundElements()
    {
        List<Lexeme> items = AnalysisCore.Analyze(
            ".code segment\n.data segment\n.stack segment\nbyte ptr [bx + si]\nword ptr [bp]\n2 dup(1, 2 dup(0))",
            new string[0]);
        Equal(8, items.Count, "frases y expresiones compuestas");
        Equal(".code segment", items[0].Text, "segmento code");
        Equal(".data segment", items[1].Text, "segmento data");
        Equal(".stack segment", items[2].Text, "segmento stack");
        Equal("byte ptr", items[3].Text, "calificador byte");
        Equal("[bx + si]", items[4].Text, "direccion entre corchetes");
        Equal("word ptr", items[5].Text, "calificador word");
        Equal("[bp]", items[6].Text, "direccion entre corchetes");
        Equal("2 dup(1, 2 dup(0))", items[7].Text, "DUP anidado");
        Equal("Pseudoinstrucci\u00f3n", items[7].Type, "DUP como pseudoinstruccion");
    }

    private static void InvalidElements()
    {
        List<Lexeme> items = AnalysisCore.Analyze("123XYZ 'sin cierre", new string[0]);
        Equal("Elemento inv\u00e1lido", items[0].Type, "numero mal formado");
        Equal("Elemento inv\u00e1lido", items[1].Type, "literal sin cierre");
        List<Lexeme> unknown = AnalysisCore.Analyze("^", new string[0]);
        Equal("Elemento no identificado", unknown[0].Type, "puntuacion no identificada");
    }

    private static void Pagination()
    {
        List<int> values = new List<int>();
        for (int i = 1; i <= 55; i++) values.Add(i);
        Equal(2, AnalysisCore.PageCount(values.Count, 50), "paginas de lista");
        List<int> second = AnalysisCore.GetPage(values, 1, 50);
        Equal(5, second.Count, "cantidad en ultima pagina");
        Equal(51, second[0], "el contenido de pagina no reinicia numeracion");
        Equal(3, AnalysisCore.PageCount(51, 25), "paginas de fuente");
    }

    private static void FileValidation()
    {
        string directory = Path.Combine(Path.GetTempPath(), "analizador-fase1-tests");
        Directory.CreateDirectory(directory);
        string ens = Path.Combine(directory, "prueba.ENS");
        string asm = Path.Combine(directory, "prueba.asm");
        File.WriteAllText(ens, "mov ax, 1");
        File.WriteAllText(asm, "mov ax, 1");
        try
        {
            string error;
            True(AnalysisCore.ValidateSourcePath(ens, out error), "acepta .ENS fuera de la app");
            True(!AnalysisCore.ValidateSourcePath(asm, out error), "rechaza .asm");
            True(error.IndexOf(".ens", StringComparison.OrdinalIgnoreCase) >= 0, "mensaje de extension");
            True(!AnalysisCore.ValidateSourcePath(Path.Combine(directory, "no-existe.ens"), out error), "rechaza inexistente");
            True(error.IndexOf("existe", StringComparison.OrdinalIgnoreCase) >= 0, "mensaje de existencia");
        }
        finally
        {
            File.Delete(ens);
            File.Delete(asm);
            Directory.Delete(directory);
        }
    }

    private static void True(bool condition, string message)
    {
        if (!condition) throw new Exception("Fallo: " + message);
    }

    private static void Equal<T>(T expected, T actual, string message)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new Exception("Fallo: " + message + ". Esperado=" + expected + ", actual=" + actual);
    }
}
