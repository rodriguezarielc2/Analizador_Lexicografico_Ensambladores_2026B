using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
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
            Assert(grids[0].ScrollBars == ScrollBars.None, "la lista se muestra paginada sin barras de desplazamiento");
            Assert(textBoxes.Count == 1 && textBoxes[0].ReadOnly, "el archivo fuente debe mostrarse en un panel de solo lectura");
            Assert(textBoxes[0].ScrollBars == ScrollBars.None && textBoxes[0].WordWrap,
                "las instrucciones se muestran paginadas sin barras de desplazamiento");

            VerifyZoom(form, grids[0], textBoxes[0]);
            VerifyIndependentPagination(form, grids[0], textBoxes[0]);
            VerifySourceReflowsOnZoom(form, textBoxes[0]);
        }
        Console.WriteLine("OK: inicio, controles y paginacion independiente de la ventana");
    }

    private static void VerifyTeamTwoInstructions(MainForm form)
    {
        string[] expected = new string[] {
            "CBW", "CLC", "LODSB", "LODSW", "STOSB", "AAA", "POP", "IDIV", "INT", "AND",
            "ADC", "LEA", "LES", "JNZ", "JZ", "LOOPNZ", "JGE", "JNA", "JNL", "JB"
        };
        FieldInfo field = typeof(MainForm).GetField("_assignedInstructions", BindingFlags.Instance | BindingFlags.NonPublic);
        List<string> actual = field.GetValue(form) as List<string>;
        Assert(actual != null && actual.Count == expected.Length, "se cargan las 20 instrucciones del equipo 2");
        foreach (string instruction in expected)
            Assert(actual.Exists(value => String.Equals(value, instruction, StringComparison.OrdinalIgnoreCase)),
                "configuración del equipo 2 contiene " + instruction);

        List<Lexeme> analyzed = AnalysisCore.Analyze(String.Join(" ", expected) + " JE MOV", actual);
        for (int i = 0; i < expected.Length; i++)
            Assert(analyzed[i].Type == "Instrucci\u00f3n", expected[i] + " se identifica como instruccion asignada");
        Assert(analyzed[expected.Length].Text == "JE" && analyzed[expected.Length].Type == "S\u00edmbolo",
            "JE queda como simbolo porque esta asignada a otro equipo");
        Assert(analyzed[expected.Length + 1].Text == "MOV" && analyzed[expected.Length + 1].Type == "S\u00edmbolo",
            "MOV queda como simbolo porque no esta asignada al equipo 2");
    }

    private static void VerifyZoom(MainForm form, DataGridView grid, TextBox sourceView)
    {
        List<Button> buttons = Find<Button>(form);
        Button zoomOut = buttons.Find(button => button.Name == "zoomOutButton");
        Button zoomReset = buttons.Find(button => button.Name == "zoomResetButton");
        Button zoomIn = buttons.Find(button => button.Name == "zoomInButton");
        Assert(zoomOut != null && zoomReset != null && zoomIn != null,
            "la barra debe mostrar controles de zoom");
        Assert(zoomReset.Text == "100%", "el zoom inicia en 100 por ciento");

        float sourceSize = sourceView.Font.Size;
        float elementSize = grid.DefaultCellStyle.Font.Size;
        MethodInfo changeZoom = typeof(MainForm).GetMethod("ChangeZoom", BindingFlags.Instance | BindingFlags.NonPublic);
        MethodInfo setZoom = typeof(MainForm).GetMethod("SetZoom", BindingFlags.Instance | BindingFlags.NonPublic);
        changeZoom.Invoke(form, new object[] { 10 });
        Assert(sourceView.Font.Size > sourceSize && grid.DefaultCellStyle.Font.Size > elementSize,
            "A+ amplía el código y la lista");
        Assert(zoomReset.Text == "110%", "el indicador refleja el zoom aplicado");

        setZoom.Invoke(form, new object[] { 100 });
        Assert(sourceView.Font.Size == sourceSize && grid.DefaultCellStyle.Font.Size == elementSize,
            "100 por ciento restaura el tamaño inicial");
        changeZoom.Invoke(form, new object[] { -10 });
        Assert(sourceView.Font.Size < sourceSize && grid.DefaultCellStyle.Font.Size < elementSize,
            "A- reduce el código y la lista");
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
            Assert(elementsPage.Text.StartsWith("P\u00e1gina 1 de ", StringComparison.Ordinal), "la lista indica su pagina actual y total");
            int firstPageSize = grid.Rows.Count;
            Assert(firstPageSize > 0 && firstPageSize <= 50, "la pagina de elementos se ajusta al espacio visible");
            Assert(Convert.ToString(grid.Rows[0].Cells[0].Value) == "1" &&
                Convert.ToString(grid.Rows[firstPageSize - 1].Cells[0].Value) == Convert.ToString(firstPageSize),
                "numeracion global de la primera pagina");
            Assert(sourceView.Lines.Length == 25, "primera pagina de fuente contiene 25 lineas");

            Assert(sourceNext.Enabled, "el boton siguiente de fuente debe habilitarse");
            changeSource.Invoke(form, new object[] { 1 });
            Assert(sourcePage.Text.StartsWith("P\u00e1gina 2 de 3", StringComparison.Ordinal), "navega la fuente");
            Assert(elementsPage.Text.StartsWith("P\u00e1gina 1 de ", StringComparison.Ordinal), "la fuente no cambia la pagina de la lista");

            Assert(elementsNext.Enabled, "el boton siguiente de elementos debe habilitarse");
            changeElements.Invoke(form, new object[] { 1 });
            Assert(sourcePage.Text.StartsWith("P\u00e1gina 2 de 3", StringComparison.Ordinal), "la lista no cambia la pagina de fuente");
            Assert(elementsPage.Text.StartsWith("P\u00e1gina 2 de ", StringComparison.Ordinal), "navega la lista de elementos");
            Assert(Convert.ToString(grid.Rows[0].Cells[0].Value) == Convert.ToString(firstPageSize + 1),
                "la numeracion continua en la siguiente pagina");

            MethodInfo setZoom = typeof(MainForm).GetMethod("SetZoom", BindingFlags.Instance | BindingFlags.NonPublic);
            int rowsAtCurrentZoom = grid.Rows.Count;
            setZoom.Invoke(form, new object[] { 150 });
            Assert(grid.ScrollBars == ScrollBars.None && grid.Rows.Count > 0 && grid.Rows.Count <= rowsAtCurrentZoom,
                "la paginacion de resultados se reajusta al zoom sin scroll");
        }
        finally
        {
            File.Delete(path);
            Directory.Delete(directory);
        }
    }

    private static void VerifySourceReflowsOnZoom(MainForm form, TextBox sourceView)
    {
        List<string> lines = new List<string>();
        StringBuilder longLine = new StringBuilder();
        for (int i = 0; i < 40; i++) longLine.Append(" MOV");
        for (int i = 0; i < 51; i++) lines.Add(longLine.ToString());

        FieldInfo sourceLines = typeof(MainForm).GetField("_sourceLines", BindingFlags.Instance | BindingFlags.NonPublic);
        FieldInfo sourcePage = typeof(MainForm).GetField("_sourcePage", BindingFlags.Instance | BindingFlags.NonPublic);
        sourceLines.SetValue(form, lines.ToArray());
        sourcePage.SetValue(form, 0);
        MethodInfo setZoom = typeof(MainForm).GetMethod("SetZoom", BindingFlags.Instance | BindingFlags.NonPublic);
        MethodInfo buildPageStarts = typeof(MainForm).GetMethod("BuildSourcePageStarts", BindingFlags.Instance | BindingFlags.NonPublic);

        setZoom.Invoke(form, new object[] { 100 });
        int pagesAt100 = ((List<int>)buildPageStarts.Invoke(form, null)).Count;
        setZoom.Invoke(form, new object[] { 150 });
        int pagesAt150 = ((List<int>)buildPageStarts.Invoke(form, null)).Count;
        Assert(sourceView.ScrollBars == ScrollBars.None && sourceView.WordWrap,
            "el codigo se envuelve sin barras de desplazamiento");
        Assert(pagesAt150 > pagesAt100, "las paginas de instrucciones se reajustan cuando aumenta el zoom");
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
