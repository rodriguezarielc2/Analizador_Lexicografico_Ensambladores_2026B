using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace AnalizadorFase1
{
    public sealed class Lexeme
    {
        public int Number { get; private set; }
        public int Line { get; private set; }
        public int Column { get; private set; }
        public string Text { get; private set; }
        public string Type { get; private set; }

        public Lexeme(int number, int line, int column, string text, string type)
        {
            Number = number;
            Line = line;
            Column = column;
            Text = text;
            Type = type;
        }
    }

    public static class AnalysisCore
    {
        private static readonly HashSet<string> Registers = new HashSet<string>(
            "al ah bl bh cl ch dl dh ax bx cx dx si di bp sp ip cs ds es ss flags".Split(' '),
            StringComparer.OrdinalIgnoreCase);

        private static readonly HashSet<string> Pseudoinstructions = new HashSet<string>(
            ("db dw dd dq dt dup end endm endp ends equ include label macro model " +
             "org proc segment assume byte word dword qword ptr short near far offset " +
             "type length lengthof size sizeof high low seg this public extrn extern " +
             "group record struc struct union local endw endc align even title subtitle " +
             "name purge option comm common irp irpc rept while exitm .code .data " +
             ".stack code data stack dosseg .model .startup .exit")
                .Split(' '), StringComparer.OrdinalIgnoreCase);

        private static readonly Regex SegmentPhrase = new Regex(
            @"^\.(?:code|data|stack)\s+segment\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex PointerPhrase = new Regex(
            @"^(?:byte|word|dword)\s+ptr\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex HexSuffix = new Regex(
            @"^[+-]?[0-9][0-9a-f]*h$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex HexPrefix = new Regex(
            @"^[+-]?0x[0-9a-f]+$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex BinarySuffix = new Regex(
            @"^[+-]?[01]+b$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex BinaryPrefix = new Regex(
            @"^[+-]?0b[01]+$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        private static readonly Regex Decimal = new Regex(
            @"^[+-]?[0-9]+d?$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        public static List<Lexeme> Analyze(string source, IEnumerable<string> assignedInstructions)
        {
            HashSet<string> assigned = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (assignedInstructions != null)
            {
                foreach (string instruction in assignedInstructions)
                {
                    if (!String.IsNullOrWhiteSpace(instruction))
                        assigned.Add(instruction.Trim());
                }
            }

            List<Lexeme> items = new List<Lexeme>();
            string[] lines = (source ?? String.Empty).Split(new string[] { "\r\n", "\n", "\r" }, StringSplitOptions.None);
            for (int lineIndex = 0; lineIndex < lines.Length; lineIndex++)
                AnalyzeLine(lines[lineIndex], lineIndex + 1, items, assigned);
            return items;
        }

        public static int PageCount(int itemCount, int pageSize)
        {
            if (pageSize <= 0) throw new ArgumentOutOfRangeException("pageSize");
            if (itemCount <= 0) return 0;
            return (itemCount + pageSize - 1) / pageSize;
        }

        public static List<T> GetPage<T>(IList<T> items, int pageIndex, int pageSize)
        {
            if (items == null) throw new ArgumentNullException("items");
            if (pageSize <= 0) throw new ArgumentOutOfRangeException("pageSize");
            List<T> page = new List<T>();
            int start = pageIndex * pageSize;
            if (pageIndex < 0 || start >= items.Count) return page;
            int end = Math.Min(start + pageSize, items.Count);
            for (int i = start; i < end; i++) page.Add(items[i]);
            return page;
        }

        public static bool ValidateSourcePath(string path, out string error)
        {
            error = String.Empty;
            if (String.IsNullOrWhiteSpace(path))
            {
                error = "Selecciona un archivo .ens.";
                return false;
            }
            if (!File.Exists(path))
            {
                error = "El archivo seleccionado no existe.";
                return false;
            }
            if (!String.Equals(Path.GetExtension(path), ".ens", StringComparison.OrdinalIgnoreCase))
            {
                error = "Solo se pueden abrir archivos con extensi\u00f3n .ens.";
                return false;
            }
            return true;
        }

        private static void AnalyzeLine(string line, int lineNumber, List<Lexeme> items, HashSet<string> assigned)
        {
            int index = 0;
            while (index < line.Length)
            {
                char current = line[index];
                if (Char.IsWhiteSpace(current))
                {
                    index++;
                    continue;
                }
                if (current == ';') break;
                if (current == ',' || current == ':')
                {
                    index++;
                    continue;
                }

                string compound = MatchCompound(line, index, SegmentPhrase);
                if (compound == null) compound = MatchCompound(line, index, PointerPhrase);
                if (compound != null)
                {
                    Add(items, lineNumber, index + 1, compound, "Pseudoinstrucci\u00f3n");
                    index += compound.Length;
                    continue;
                }

                int compoundEnd;
                string compoundText;
                bool compoundValid;
                if (TryReadDup(line, index, out compoundText, out compoundEnd, out compoundValid))
                {
                    Add(items, lineNumber, index + 1, compoundText,
                        compoundValid ? "Pseudoinstrucci\u00f3n" : "Elemento inv\u00e1lido");
                    index = compoundEnd;
                    continue;
                }

                if (current == '[')
                {
                    int bracketEnd;
                    bool valid = TryReadBracket(line, index, out bracketEnd);
                    string text = line.Substring(index, bracketEnd - index);
                    Add(items, lineNumber, index + 1, text,
                        valid ? "S\u00edmbolo" : "Elemento inv\u00e1lido");
                    index = bracketEnd;
                    continue;
                }

                if (current == '\'' || current == '"')
                {
                    int quoteEnd = FindClosingQuote(line, index);
                    if (quoteEnd < 0)
                    {
                        Add(items, lineNumber, index + 1, line.Substring(index), "Elemento inv\u00e1lido");
                        break;
                    }
                    string text = line.Substring(index, quoteEnd - index + 1);
                    string type = current == '\''
                        ? "Constante car\u00e1cter"
                        : "Constante de cadena";
                    Add(items, lineNumber, index + 1, text, type);
                    index = quoteEnd + 1;
                    continue;
                }

                if (current == '#')
                {
                    int close = line.IndexOf('#', index + 1);
                    if (close < 0)
                    {
                        Add(items, lineNumber, index + 1, line.Substring(index), "Elemento inv\u00e1lido");
                        break;
                    }
                    string text = line.Substring(index, close - index + 1);
                    Add(items, lineNumber, index + 1, text, "Pseudoinstrucci\u00f3n");
                    index = close + 1;
                    continue;
                }

                if ((current == '+' || current == '-') && index + 1 < line.Length && Char.IsDigit(line[index + 1]))
                {
                    int start = index++;
                    while (index < line.Length && IsAtomCharacter(line[index])) index++;
                    string text = line.Substring(start, index - start);
                    Add(items, lineNumber, start + 1, text, Classify(text, assigned));
                    continue;
                }

                if (IsAtomCharacter(current))
                {
                    int start = index;
                    while (index < line.Length && IsAtomCharacter(line[index])) index++;
                    string text = line.Substring(start, index - start);
                    Add(items, lineNumber, start + 1, text, Classify(text, assigned));
                    continue;
                }

                Add(items, lineNumber, index + 1, current.ToString(), "Elemento no identificado");
                index++;
            }
        }

        private static string MatchCompound(string line, int index, Regex expression)
        {
            Match match = expression.Match(line.Substring(index));
            return match.Success ? match.Value : null;
        }

        private static bool TryReadDup(string line, int start, out string text, out int end, out bool valid)
        {
            text = null;
            end = start;
            valid = false;
            int position = start;

            if (position < line.Length && Char.IsDigit(line[position]))
            {
                while (position < line.Length && Char.IsDigit(line[position])) position++;
                int whitespaceStart = position;
                while (position < line.Length && Char.IsWhiteSpace(line[position])) position++;
                if (position == whitespaceStart) return false;
            }

            if (position + 3 > line.Length ||
                String.Compare(line, position, "dup", 0, 3, StringComparison.OrdinalIgnoreCase) != 0)
                return false;
            int afterWord = position + 3;
            if (afterWord < line.Length && IsAtomCharacter(line[afterWord])) return false;
            position = afterWord;
            while (position < line.Length && Char.IsWhiteSpace(line[position])) position++;
            if (position >= line.Length || line[position] != '(') return false;

            int opening = position;
            int depth = 0;
            while (position < line.Length)
            {
                char c = line[position];
                if (c == '\'' || c == '"')
                {
                    int quotedEnd = FindClosingQuote(line, position);
                    if (quotedEnd < 0)
                    {
                        text = line.Substring(start);
                        end = line.Length;
                        return true;
                    }
                    position = quotedEnd + 1;
                    continue;
                }
                if (c == ';') break;
                if (c == '(') depth++;
                if (c == ')')
                {
                    depth--;
                    if (depth == 0)
                    {
                        text = line.Substring(start, position - start + 1).Trim();
                        end = position + 1;
                        valid = true;
                        return true;
                    }
                }
                position++;
            }
            text = line.Substring(start).TrimEnd();
            end = line.Length;
            return true;
        }

        private static bool TryReadBracket(string line, int start, out int end)
        {
            int depth = 0;
            int position = start;
            while (position < line.Length)
            {
                char c = line[position];
                if (c == '\'' || c == '"')
                {
                    int quotedEnd = FindClosingQuote(line, position);
                    if (quotedEnd < 0)
                    {
                        end = line.Length;
                        return false;
                    }
                    position = quotedEnd + 1;
                    continue;
                }
                if (c == ';') break;
                if (c == '[') depth++;
                if (c == ']')
                {
                    depth--;
                    if (depth == 0)
                    {
                        end = position + 1;
                        return true;
                    }
                }
                position++;
            }
            end = line.Length;
            return false;
        }

        private static int FindClosingQuote(string line, int start)
        {
            char quote = line[start];
            int position = start + 1;
            while (position < line.Length)
            {
                if (line[position] == '\\' && position + 1 < line.Length)
                {
                    position += 2;
                    continue;
                }
                if (line[position] == quote)
                {
                    if (position + 1 < line.Length && line[position + 1] == quote)
                    {
                        position += 2;
                        continue;
                    }
                    return position;
                }
                position++;
            }
            return -1;
        }

        private static string Classify(string text, HashSet<string> assigned)
        {
            if (assigned.Contains(text)) return "Instrucci\u00f3n";
            if (Registers.Contains(text)) return "Registro";

            string normalized = text.StartsWith(".", StringComparison.Ordinal) ? text.Substring(1) : text;
            if (Pseudoinstructions.Contains(text) || Pseudoinstructions.Contains(normalized))
                return "Pseudoinstrucci\u00f3n";

            if (HexPrefix.IsMatch(text) || HexSuffix.IsMatch(text)) return "Constante hexadecimal";
            if (BinaryPrefix.IsMatch(text) || BinarySuffix.IsMatch(text)) return "Constante binaria";
            if (Decimal.IsMatch(text)) return "Constante decimal";
            if (Char.IsDigit(text[0]) || ((text[0] == '+' || text[0] == '-') && text.Length > 1 && Char.IsDigit(text[1])))
                return "Elemento inv\u00e1lido";
            if (text == "?") return "Constante no inicializada";
            if (IsSymbol(text)) return "S\u00edmbolo";
            return "Elemento no identificado";
        }

        private static bool IsSymbol(string text)
        {
            if (String.IsNullOrEmpty(text) || text == ".") return false;
            if (!(Char.IsLetter(text[0]) || text[0] == '_' || text[0] == '.' || text[0] == '$' || text[0] == '@'))
                return false;
            for (int i = 1; i < text.Length; i++)
            {
                char c = text[i];
                if (!(Char.IsLetterOrDigit(c) || c == '_' || c == '.' || c == '$' || c == '@' || c == '?'))
                    return false;
            }
            return true;
        }

        private static bool IsAtomCharacter(char c)
        {
            return Char.IsLetterOrDigit(c) || c == '_' || c == '.' || c == '$' || c == '@' || c == '?';
        }

        private static void Add(List<Lexeme> items, int line, int column, string text, string type)
        {
            items.Add(new Lexeme(items.Count + 1, line, column, text, type));
        }
    }
}
