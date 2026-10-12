using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

namespace AnalizadorFase1
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    internal sealed class MainForm : Form
    {
        private const int SourceLinesPerPage = 25;
        private const int ElementsPerPage = 50;

        private readonly Label _fileLabel;
        private readonly Label _statusLabel;
        private readonly Label _sourcePageLabel;
        private readonly Label _elementsPageLabel;
        private readonly TextBox _sourceView;
        private readonly DataGridView _elementsGrid;
        private readonly Button _sourcePrevious;
        private readonly Button _sourceNext;
        private readonly Button _elementsPrevious;
        private readonly Button _elementsNext;
        private readonly ToolTip _toolTip;

        private readonly List<string> _assignedInstructions;
        private List<Lexeme> _elements = new List<Lexeme>();
        private string[] _sourceLines = new string[0];
        private string _source = String.Empty;
        private string _filePath;
        private int _sourcePage;
        private int _elementsPage;

        public MainForm()
        {
            Text = "Analizador lexicogr\u00e1fico de ensamblador | Fase 1";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(920, 620);
            Size = new Size(1320, 820);
            BackColor = Color.FromArgb(239, 243, 247);
            Font = new Font("Segoe UI", 9F, FontStyle.Regular, GraphicsUnit.Point);

            _assignedInstructions = LoadAssignedInstructions();
            _toolTip = new ToolTip();
            _fileLabel = new Label();
            _statusLabel = new Label();
            _sourcePageLabel = new Label();
            _elementsPageLabel = new Label();
            _sourceView = new TextBox();
            _elementsGrid = new DataGridView();
            _sourcePrevious = new Button();
            _sourceNext = new Button();
            _elementsPrevious = new Button();
            _elementsNext = new Button();

            BuildWindow();
            ShowSourcePage();
            ShowElementsPage();
            UpdateStatus();
        }

        private void BuildWindow()
        {
            TableLayoutPanel root = new TableLayoutPanel();
            root.Dock = DockStyle.Fill;
            root.ColumnCount = 1;
            root.RowCount = 2;
            root.RowStyles.Add(new RowStyle(SizeType.Absolute, 58F));
            root.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            Controls.Add(root);

            Panel toolbar = BuildToolbar();
            root.Controls.Add(toolbar, 0, 0);

            SplitContainer split = new SplitContainer();
            split.Dock = DockStyle.Fill;
            split.Orientation = Orientation.Vertical;
            split.Size = new Size(1200, 700);
            split.Panel1MinSize = 300;
            split.Panel2MinSize = 360;
            split.BackColor = Color.FromArgb(213, 222, 231);
            root.Controls.Add(split, 0, 1);

            GroupBox sourceGroup = new GroupBox();
            sourceGroup.Text = "1. Archivo fuente";
            sourceGroup.Dock = DockStyle.Fill;
            sourceGroup.Padding = new Padding(10);
            sourceGroup.ForeColor = Color.FromArgb(23, 50, 77);
            sourceGroup.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            split.Panel1.Controls.Add(sourceGroup);

            GroupBox elementsGroup = new GroupBox();
            elementsGroup.Text = "2 y 3. Separaci\u00f3n e identificaci\u00f3n";
            elementsGroup.Dock = DockStyle.Fill;
            elementsGroup.Padding = new Padding(10);
            elementsGroup.ForeColor = Color.FromArgb(23, 50, 77);
            elementsGroup.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            split.Panel2.Controls.Add(elementsGroup);

            BuildSourcePanel(sourceGroup);
            BuildElementsPanel(elementsGroup);
        }

        private Panel BuildToolbar()
        {
            Panel toolbar = new Panel();
            toolbar.Dock = DockStyle.Fill;
            toolbar.BackColor = Color.FromArgb(23, 50, 77);
            toolbar.Padding = new Padding(12, 8, 12, 8);

            FlowLayoutPanel row = new FlowLayoutPanel();
            row.Dock = DockStyle.Fill;
            row.WrapContents = false;
            row.FlowDirection = FlowDirection.LeftToRight;
            row.BackColor = toolbar.BackColor;
            toolbar.Controls.Add(row);

            Label title = new Label();
            title.Text = "ANALIZADOR LEXICOGR\u00c1FICO";
            title.ForeColor = Color.White;
            title.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            title.AutoSize = false;
            title.Width = 245;
            title.Height = 38;
            title.TextAlign = ContentAlignment.MiddleLeft;
            row.Controls.Add(title);

            Button openButton = CreateButton("Abrir archivo .ens", Color.FromArgb(25, 165, 138));
            openButton.Width = 145;
            openButton.Click += OpenFile;
            row.Controls.Add(openButton);

            Button analyzeButton = CreateButton("Analizar", Color.FromArgb(52, 91, 125));
            analyzeButton.Width = 92;
            analyzeButton.Click += AnalyzeCurrentFile;
            row.Controls.Add(analyzeButton);

            _fileLabel.Text = "Selecciona un archivo fuente";
            _fileLabel.ForeColor = Color.White;
            _fileLabel.AutoEllipsis = true;
            _fileLabel.Width = 300;
            _fileLabel.Height = 38;
            _fileLabel.TextAlign = ContentAlignment.MiddleLeft;
            row.Controls.Add(_fileLabel);
            _toolTip.SetToolTip(_fileLabel, "La aplicaci\u00f3n permite abrir archivos .ens desde cualquier carpeta.");

            _statusLabel.ForeColor = Color.FromArgb(217, 229, 239);
            _statusLabel.AutoEllipsis = true;
            _statusLabel.Width = 310;
            _statusLabel.Height = 38;
            _statusLabel.TextAlign = ContentAlignment.MiddleRight;
            row.Controls.Add(_statusLabel);
            return toolbar;
        }

        private void BuildSourcePanel(GroupBox group)
        {
            TableLayoutPanel layout = new TableLayoutPanel();
            layout.Dock = DockStyle.Fill;
            layout.ColumnCount = 1;
            layout.RowCount = 3;
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 30F));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 38F));
            group.Controls.Add(layout);

            ConfigurePageLabel(_sourcePageLabel);
            layout.Controls.Add(_sourcePageLabel, 0, 0);

            _sourceView.Dock = DockStyle.Fill;
            _sourceView.Multiline = true;
            _sourceView.ReadOnly = true;
            _sourceView.WordWrap = false;
            _sourceView.ScrollBars = ScrollBars.Both;
            _sourceView.BackColor = Color.White;
            _sourceView.ForeColor = Color.FromArgb(23, 43, 77);
            _sourceView.Font = new Font("Consolas", 10F, FontStyle.Regular, GraphicsUnit.Point);
            _sourceView.BorderStyle = BorderStyle.FixedSingle;
            layout.Controls.Add(_sourceView, 0, 1);

            FlowLayoutPanel pager = CreatePager(_sourcePrevious, _sourceNext);
            _sourcePrevious.Click += delegate { ChangeSourcePage(-1); };
            _sourceNext.Click += delegate { ChangeSourcePage(1); };
            layout.Controls.Add(pager, 0, 2);
        }

        private void BuildElementsPanel(GroupBox group)
        {
            TableLayoutPanel layout = new TableLayoutPanel();
            layout.Dock = DockStyle.Fill;
            layout.ColumnCount = 1;
            layout.RowCount = 3;
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 30F));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 38F));
            group.Controls.Add(layout);

            ConfigurePageLabel(_elementsPageLabel);
            layout.Controls.Add(_elementsPageLabel, 0, 0);

            _elementsGrid.Dock = DockStyle.Fill;
            _elementsGrid.ReadOnly = true;
            _elementsGrid.AllowUserToAddRows = false;
            _elementsGrid.AllowUserToDeleteRows = false;
            _elementsGrid.AllowUserToResizeRows = false;
            _elementsGrid.MultiSelect = false;
            _elementsGrid.RowHeadersVisible = false;
            _elementsGrid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            _elementsGrid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            _elementsGrid.BackgroundColor = Color.White;
            _elementsGrid.BorderStyle = BorderStyle.FixedSingle;
            _elementsGrid.EnableHeadersVisualStyles = false;
            _elementsGrid.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(220, 230, 239);
            _elementsGrid.ColumnHeadersDefaultCellStyle.ForeColor = Color.FromArgb(23, 50, 77);
            _elementsGrid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            _elementsGrid.DefaultCellStyle.Font = new Font("Consolas", 9.5F, FontStyle.Regular);
            _elementsGrid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(199, 231, 226);
            _elementsGrid.DefaultCellStyle.SelectionForeColor = Color.FromArgb(16, 42, 67);
            _elementsGrid.AlternatingRowsDefaultCellStyle.BackColor = Color.FromArgb(247, 250, 252);
            _elementsGrid.Columns.Add("number", "No.");
            _elementsGrid.Columns.Add("element", "Elemento separado");
            _elementsGrid.Columns.Add("type", "Tipo de elemento");
            _elementsGrid.Columns[0].FillWeight = 13F;
            _elementsGrid.Columns[1].FillWeight = 46F;
            _elementsGrid.Columns[2].FillWeight = 41F;
            layout.Controls.Add(_elementsGrid, 0, 1);

            FlowLayoutPanel pager = CreatePager(_elementsPrevious, _elementsNext);
            _elementsPrevious.Click += delegate { ChangeElementsPage(-1); };
            _elementsNext.Click += delegate { ChangeElementsPage(1); };
            layout.Controls.Add(pager, 0, 2);
        }

        private static void ConfigurePageLabel(Label label)
        {
            label.Dock = DockStyle.Fill;
            label.ForeColor = Color.FromArgb(71, 93, 116);
            label.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            label.TextAlign = ContentAlignment.MiddleLeft;
            label.AutoEllipsis = true;
        }

        private static FlowLayoutPanel CreatePager(Button previous, Button next)
        {
            previous.Text = "\u2039 Anterior";
            previous.Width = 104;
            previous.Height = 30;
            previous.Margin = new Padding(4, 0, 0, 0);
            previous.FlatStyle = FlatStyle.Flat;
            previous.BackColor = Color.FromArgb(220, 230, 239);
            previous.ForeColor = Color.FromArgb(23, 50, 77);
            previous.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            previous.FlatAppearance.BorderColor = Color.FromArgb(190, 203, 216);

            next.Text = "Siguiente \u203a";
            next.Width = 104;
            next.Height = 30;
            next.Margin = new Padding(4, 0, 0, 0);
            next.FlatStyle = FlatStyle.Flat;
            next.BackColor = Color.FromArgb(220, 230, 239);
            next.ForeColor = Color.FromArgb(23, 50, 77);
            next.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            next.FlatAppearance.BorderColor = Color.FromArgb(190, 203, 216);

            FlowLayoutPanel panel = new FlowLayoutPanel();
            panel.Dock = DockStyle.Fill;
            panel.FlowDirection = FlowDirection.RightToLeft;
            panel.WrapContents = false;
            panel.Padding = new Padding(0, 3, 0, 0);
            panel.Controls.Add(next);
            panel.Controls.Add(previous);
            return panel;
        }

        private static Button CreateButton(string text, Color color)
        {
            Button button = new Button();
            button.Text = text;
            button.Height = 36;
            button.Margin = new Padding(0, 1, 8, 1);
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 0;
            button.BackColor = color;
            button.ForeColor = Color.White;
            button.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            button.Cursor = Cursors.Hand;
            return button;
        }

        private void OpenFile(object sender, EventArgs e)
        {
            using (OpenFileDialog dialog = new OpenFileDialog())
            {
                dialog.Title = "Selecciona el programa fuente";
                dialog.Filter = "Todos los archivos (*.*)|*.*";
                dialog.CheckFileExists = true;
                dialog.CheckPathExists = true;
                dialog.ValidateNames = true;
                dialog.Multiselect = false;
                if (dialog.ShowDialog(this) != DialogResult.OK) return;
                LoadFile(dialog.FileName);
            }
        }

        private void LoadFile(string path)
        {
            string error;
            if (!AnalysisCore.ValidateSourcePath(path, out error))
            {
                MessageBox.Show(this, error, "No se puede abrir el archivo", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            try
            {
                string source;
                try
                {
                    source = File.ReadAllText(path, new UTF8Encoding(false, true));
                }
                catch (DecoderFallbackException)
                {
                    source = File.ReadAllText(path, Encoding.Default);
                }

                _filePath = path;
                _source = source;
                _sourceLines = source.Split(new string[] { "\r\n", "\n", "\r" }, StringSplitOptions.None);
                _fileLabel.Text = Path.GetFileName(path);
                _toolTip.SetToolTip(_fileLabel, path);
                _sourcePage = 0;
                _elementsPage = 0;
                AnalyzeCurrentFile(this, EventArgs.Empty);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, "No se pudo leer el archivo: " + ex.Message,
                    "Error de lectura", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void AnalyzeCurrentFile(object sender, EventArgs e)
        {
            if (String.IsNullOrEmpty(_filePath)) return;
            _elements = AnalysisCore.Analyze(_source, _assignedInstructions);
            _elementsPage = 0;
            ShowSourcePage();
            ShowElementsPage();
            UpdateStatus();
        }

        private void ChangeSourcePage(int change)
        {
            int count = AnalysisCore.PageCount(_sourceLines.Length, SourceLinesPerPage);
            _sourcePage = Math.Max(0, Math.Min(_sourcePage + change, Math.Max(0, count - 1)));
            ShowSourcePage();
        }

        private void ChangeElementsPage(int change)
        {
            int count = AnalysisCore.PageCount(_elements.Count, ElementsPerPage);
            _elementsPage = Math.Max(0, Math.Min(_elementsPage + change, Math.Max(0, count - 1)));
            ShowElementsPage();
        }

        private void ShowSourcePage()
        {
            int total = Math.Max(1, AnalysisCore.PageCount(_sourceLines.Length, SourceLinesPerPage));
            _sourcePage = Math.Max(0, Math.Min(_sourcePage, total - 1));
            int start = _sourcePage * SourceLinesPerPage;
            int end = Math.Min(start + SourceLinesPerPage, _sourceLines.Length);
            StringBuilder visible = new StringBuilder();
            for (int i = start; i < end; i++)
            {
                if (visible.Length > 0) visible.AppendLine();
                visible.Append(_sourceLines[i]);
            }
            _sourceView.Text = visible.ToString();

            if (String.IsNullOrEmpty(_filePath))
                _sourcePageLabel.Text = "Abre un archivo .ens para mostrar su contenido.";
            else if (_sourceLines.Length == 0)
                _sourcePageLabel.Text = "P\u00e1gina 1 de 1 | Archivo vac\u00edo";
            else
                _sourcePageLabel.Text = String.Format("P\u00e1gina {0} de {1} | L\u00edneas {2} a {3}",
                    _sourcePage + 1, total, start + 1, end);
            _sourcePrevious.Enabled = _sourcePage > 0;
            _sourceNext.Enabled = _sourcePage + 1 < total;
        }

        private void ShowElementsPage()
        {
            int total = Math.Max(1, AnalysisCore.PageCount(_elements.Count, ElementsPerPage));
            _elementsPage = Math.Max(0, Math.Min(_elementsPage, total - 1));
            _elementsGrid.Rows.Clear();
            List<Lexeme> page = AnalysisCore.GetPage(_elements, _elementsPage, ElementsPerPage);
            foreach (Lexeme item in page)
                _elementsGrid.Rows.Add(item.Number, item.Text, item.Type);

            if (String.IsNullOrEmpty(_filePath))
                _elementsPageLabel.Text = "Los elementos aparecer\u00e1n al abrir un archivo .ens.";
            else
                _elementsPageLabel.Text = String.Format("P\u00e1gina {0} de {1} | {2} elementos numerados",
                    _elementsPage + 1, total, _elements.Count);
            _elementsPrevious.Enabled = _elementsPage > 0;
            _elementsNext.Enabled = _elementsPage + 1 < total;
        }

        private void UpdateStatus()
        {
            if (String.IsNullOrEmpty(_filePath))
            {
                _statusLabel.Text = "Listo para abrir un .ens";
                return;
            }
            string instructionStatus = _assignedInstructions.Count == 0
                ? "Instrucciones del equipo pendientes"
                : String.Format("Instrucciones asignadas: {0}", _assignedInstructions.Count);
            _statusLabel.Text = String.Format("{0} elementos | {1}", _elements.Count, instructionStatus);
        }

        private static List<string> LoadAssignedInstructions()
        {
            List<string> instructions = new List<string>();
            string path = Path.Combine(Application.StartupPath, "instrucciones_equipo.txt");
            if (!File.Exists(path)) return instructions;

            foreach (string line in File.ReadAllLines(path))
            {
                string trimmed = line.Trim();
                if (trimmed.Length == 0 || trimmed.StartsWith(";", StringComparison.Ordinal) ||
                    trimmed.StartsWith("#", StringComparison.Ordinal)) continue;
                string[] values = trimmed.Split(new char[] { ' ', '\t', ',', ';' }, StringSplitOptions.RemoveEmptyEntries);
                foreach (string value in values) instructions.Add(value);
            }
            return instructions;
        }
    }
}
