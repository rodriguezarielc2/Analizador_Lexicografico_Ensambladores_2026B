using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using AnalizadorFase1;

internal static class GuiSmokeTests
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        using (MainForm form = new MainForm())
        {
            IntPtr formHandle = form.Handle;
            CreateHandles(form);
            form.PerformLayout();

            VerifyTeamTwoInstructions(form);

            List<GroupBox> groups = Find<GroupBox>(form);
            List<DataGridView> grids = Find<DataGridView>(form);
            List<TextBox> textBoxes = Find<TextBox>(form);
            Assert(formHandle != IntPtr.Zero, "la ventana debe crear su handle");
            Assert(groups.Count == 2, "la ventana debe mostrar fuente y resultados");
            Assert(grids.Count == 1 && grids[0].Columns.Count == 3, "la lista debe mostrar numero, elemento y tipo");
            Assert(textBoxes.Count == 1 && textBoxes[0].ReadOnly, "el archivo fuente debe mostrarse en un panel de solo lectura");

            VerifyIndependentPagination(form, grids[0], textBoxes[0]);
        }
        Console.WriteLine("OK: inicio, controles y paginacion independiente de la ventana");
    }

    private static void VerifyTeamTwoInstructions(MainForm form)
    {
        string[] expected = new string[] {
            "CBW", "CLC", "LODSB", "LODSW", "STOSB", "AAA", "POP", "IDIV", "INT", "AND",
            "ADC", "LEA", "LES", "JNZ", "JZ", "LOOPNZ", "JGE", "JNA", "JNL", "JE"
        };
        FieldInfo field = typeof(MainForm).GetField("_assignedInstructions", BindingFlags.Instance | BindingFlags.NonPublic);
        List<string> actual = field.GetValue(form) as List<string>;
        Assert(actual != null && actual.Count == expected.Length, "se cargan las 20 instrucciones del equipo 2");
        foreach (string instruction in expected)
            Assert(actual.Exists(value => String.Equals(value, instruction, StringComparison.OrdinalIgnoreCase)),
                "configuración del equipo 2 contiene " + instruction);

        List<Lexeme> analyzed = AnalysisCore.Analyze(String.Join(" ", expected) + " MOV", actual);
        for (int i = 0; i < expected.Length; i++)
            Assert(analyzed[i].Type == "Instrucci\u00f3n", expected[i] + " se identifica como instruccion asignada");
        Assert(analyzed[expected.Length].Type == "S\u00edmbolo", "MOV queda como simbolo porque no esta asignada al equipo 2");
    }

    private static void VerifyIndependentPagination(MainForm form, DataGridView grid, TextBox sourceView)
    {
        string directory = Path.Combine(Path.GetTempPath(), "analizador-fase1-gui-tests");
        Directory.CreateDirectory(directory);
        string path = Path.Combine(directory, "paginacion.ens");
        List<string> lines = new List<string>();
        for (int i = 0; i < 51; i++) lines.Add("mov ax, 1 ; comentario");
        File.WriteAllText(path, String.Join(Environment.NewLine, lines));
        try
        {
            MethodInfo load = typeof(MainForm).GetMethod("LoadFile", BindingFlags.Instance | BindingFlags.NonPublic);
            load.Invoke(form, new object[] { path });

            Label sourcePage = GetField<Label>(form, "_sourcePageLabel");
            Label elementsPage = GetField<Label>(form, "_elementsPageLabel");
            Button sourceNext = GetField<Button>(form, "_sourceNext");
            Button elementsNext = GetField<Button>(form, "_elementsNext");
            MethodInfo changeSource = typeof(MainForm).GetMethod("ChangeSourcePage", BindingFlags.Instance | BindingFlags.NonPublic);
            MethodInfo changeElements = typeof(MainForm).GetMethod("ChangeElementsPage", BindingFlags.Instance | BindingFlags.NonPublic);

            Assert(sourcePage.Text.StartsWith("P\u00e1gina 1 de 3", StringComparison.Ordinal), "fuente paginada en grupos de 25 lineas");
            Assert(elementsPage.Text.StartsWith("P\u00e1gina 1 de 4", StringComparison.Ordinal), "lista paginada en grupos de 50 elementos");
            Assert(grid.Rows.Count == 50, "primera pagina de elementos contiene 50 filas");
            Assert(Convert.ToString(grid.Rows[0].Cells[0].Value) == "1" &&
                Convert.ToString(grid.Rows[49].Cells[0].Value) == "50", "numeracion global de la primera pagina");
            Assert(sourceView.Lines.Length == 25, "primera pagina de fuente contiene 25 lineas");

            Assert(sourceNext.Enabled, "el boton siguiente de fuente debe habilitarse");
            changeSource.Invoke(form, new object[] { 1 });
            Assert(sourcePage.Text.StartsWith("P\u00e1gina 2 de 3", StringComparison.Ordinal), "navega la fuente");
            Assert(elementsPage.Text.StartsWith("P\u00e1gina 1 de 4", StringComparison.Ordinal), "la fuente no cambia la pagina de la lista");

            Assert(elementsNext.Enabled, "el boton siguiente de elementos debe habilitarse");
            changeElements.Invoke(form, new object[] { 1 });
            Assert(sourcePage.Text.StartsWith("P\u00e1gina 2 de 3", StringComparison.Ordinal), "la lista no cambia la pagina de fuente");
            Assert(elementsPage.Text.StartsWith("P\u00e1gina 2 de 4", StringComparison.Ordinal), "navega la lista de elementos");
            Assert(Convert.ToString(grid.Rows[0].Cells[0].Value) == "51", "la numeracion continua en la siguiente pagina");
        }
        finally
        {
            File.Delete(path);
            Directory.Delete(directory);
        }
    }

    private static T GetField<T>(MainForm form, string name) where T : class
    {
        FieldInfo field = typeof(MainForm).GetField(name, BindingFlags.Instance | BindingFlags.NonPublic);
        return field.GetValue(form) as T;
    }

    private static void CreateHandles(Control parent)
    {
        parent.CreateControl();
        foreach (Control child in parent.Controls) CreateHandles(child);
    }

    private static List<T> Find<T>(Control parent) where T : Control
    {
        List<T> found = new List<T>();
        if (parent is T) found.Add((T)parent);
        foreach (Control child in parent.Controls) found.AddRange(Find<T>(child));
        return found;
    }

    private static void Assert(bool condition, string message)
    {
        if (!condition) throw new Exception("Fallo: " + message);
    }
}
