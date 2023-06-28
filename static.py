# TODO: license

import argparse
from collections import Counter
import html
import os
from pprint import pprint
from pathlib import Path
import sys
import time
import shutil

import pygments.lexers
import pygments.styles
import pygments.formatters

from optrecord import TranslationUnit, Record, Expr, Stmt, SymtabNode
from utils import find_records, log, get_effective_result

class Location:
    def __init__(self, file, line):
        self.file = file
        self.line = line

def srcfile_to_html(file_name):
    return html.escape("%s.html" % file_name.replace('/', '|'))

def url_from_location(loc):
    return '%s#line-%i' % (srcfile_to_html(loc.file), loc.line)

def srcfile_to_html(src_file):
    """
    Generate a .html filename for src_file
    """
    file_name = os.path.basename(src_file)
    html_file_name = html.escape(file_name)
    return html_file_name

def function_to_html(function):
    """
    Generate a .html filename for function
    """
    return html.escape("%s.html" % function.replace('/', '|'))

def record_sort_key(record):
    if not record.count:
        return 0
    return -record.count.value

def get_summary_text(record):
    if record.kind == 'scope':
        if record.children:
            return get_summary_text(record.children[-1])
    return get_html_for_message(record)

def write_td_with_color(f, record, html_text):
    result = get_effective_result(record)
    if result == 'success':
        bgcolor = 'lightgreen'
    elif result == 'failure':
        bgcolor = 'lightcoral'
    else:
        bgcolor = ''
    f.write('    <td bgcolor="%s">%s</td>\n' % (bgcolor, html_text))

def write_td_pass(f, record):
    html_text = ''
    impl_url = None
    impl_file = record.impl_location.file
    impl_line = record.impl_location.line
    # FIXME: something of a hack:
    PREFIX = '../../src/'
    if impl_file.startswith(PREFIX):
        relative_file = impl_file[len(PREFIX):]
        impl_url = ('https://github.com/gcc-mirror/gcc/tree/master/%s#L%i'
                    % (relative_file, impl_line))
    if impl_url:
        html_text += '<a href="%s">\n' % impl_url

    # FIXME: link to GCC source code
    if record.pass_:
        html_text += html.escape(record.pass_.name)

    if impl_url:
        html_text += '</a>'

    write_td_with_color(f, record, html_text)

def write_td_count(f, record, highest_count):
    f.write('    <td style="text-align:right">\n')
    if record.count:
        if 1:
            if highest_count == 0:
                highest_count = 1
            hotness = 100. * record.count.value / highest_count
            f.write(html.escape('%.2f' % hotness))
        else:
            f.write(html.escape(str(int(record.count.value))))
        if 0:
            f.write(html.escape(' (%s)' % record.count.quality))
    f.write('    </td>\n')

def write_inlining_chain(f, record):
    f.write('    <td><ul class="list-group">\n')
    first = True
    if record.inlining_chain:
        for inline in record.inlining_chain:
            f.write('  <li class="list-group-item">')
            if not first:
                f.write ('inlined from ')
            f.write('<code>%s</code>' % html.escape(inline.fndecl))
            site = inline.site
            if site:
                f.write(' at <a href="%s">%s</a>'
                        % (url_from_location(site),
                           html.escape(str(site))))
            f.write('</li>\n')
            first = False
    f.write('    </ul></td>\n')

def remove_file_extension(filename):
    base_name = os.path.splitext(filename)[0]
    return base_name

def url_from_location(loc):
    return '%s.html#line-%i' % (srcfile_to_html(remove_file_extension(loc.file)), loc.line)

def write_html_header(f, title, head_content):
    """
    Write initial part of HTML file using Bootstrap, up to and including
    opening of the <body> element.
    """
    f.write('<!doctype html>\n'
            '<html lang="en">\n'
            '  <head>\n'
            '    <!-- Required meta tags -->\n'
            '    <meta charset="utf-8">\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">\n'
            '\n'
            '    <!-- Bootstrap CSS -->\n'
            '    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" integrity="sha384-WskhaSGFgHYWDcbwN70/dfYBj47jz9qbsMId/iRN3ewGhXQFZCSftd1LZCfmhktB" crossorigin="anonymous">\n'
            '\n')
    f.write(head_content)
    f.write('    <title>%s</title>\n' % title)
    f.write('  </head>\n'
            '  <body>\n')

def write_html_footer(f):
    """
    Write final part of HTML file using Bootstrap, closing the </body>
    element.
    """
    # jQuery first, then Popper.js, then Bootstrap JS
    f.write('    <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>\n'
            '    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>\n'
            '    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js" integrity="sha384-smHYKdLADwkXOn1EmN1qk/HfnUcbVRZyYmZ4qpPea6sjB/pTJ0euyQp0Mk8ck+5T" crossorigin="anonymous"></script>\n'
            '  </body>\n'
            '</html>\n')
    
    f.close()

def make_index_html(out_dir, tus, highest_count):
    log(' make_index_html')

    # Gather all records
    records = []
    for tu in tus:
        records += tu.iter_all_records()

    # Sort by highest-count down to lowest-count
    records = sorted(records, key=record_sort_key)

    print(records)

    filename = os.path.join(out_dir, "index.html")
    with open(filename, "w") as f:
        write_html_header(f, 'Optimizations', '')
        f.write('<table class="table table-striped table-bordered table-sm">\n')
        f.write('  <tr>\n')
        f.write('    <th>Summary</th>\n')
        f.write('    <th>Source Location</th>\n')
        f.write('    <th>Hotness</th>\n')
        f.write('    <th>Function / Inlining Chain</th>\n')
        f.write('    <th>Pass</th>\n')
        f.write('  </tr>\n')
        for record in records:
            f.write('  <tr>\n')

            # Summary
            write_td_with_color(f, record, get_summary_text(record))

            # Source Location:
            f.write('    <td>\n')
            if record.location:
                loc = record.location
                print(loc)
                f.write('<a href="%s">' % url_from_location (loc))
                f.write(html.escape(str(loc)))
                f.write('</a>')
            f.write('    </td>\n')

            # Hotness:
            write_td_count(f, record, highest_count)

            # Inlining Chain:
            write_inlining_chain(f, record)

            # Pass:
            write_td_pass(f, record)

            f.write('  </tr>\n')
        f.write('</table>\n')
        write_html_footer(f)

def get_html_for_message(record):
    html_for_message = ''
    for item in record.message:
        if isinstance(item, str):
            html_for_message += html.escape(str(item))
        else:
            if isinstance(item, Expr):
                html_for_item = '<code>%s</code>' % html.escape(item.expr)
            elif isinstance(item, Stmt):
                html_for_item = '<code>%s</code>' % html.escape(item.stmt)
            elif isinstance(item, SymtabNode):
                html_for_item = '<code>%s</code>' % html.escape(item.node)
            else:
                raise TypeError('unknown message item: %r' % item)
            if item.location:
                html_for_item = ('<a href="%s">%s</a>'
                                 % (url_from_location (item.location), html_for_item))
            html_for_message += html_for_item

    if record.children:
        for child in record.children:
            for line in get_html_for_message(child).splitlines():
                html_for_message += '\n  ' + line
    return html_for_message

def make_per_source_file_html(build_dir, out_dir, tus, highest_count):
    log(' make_per_source_file_html')

    # Gather all records
    records = []
    for tu in tus:
        records += tu.iter_all_records()

    # Dict of list of record, grouping by source file
    by_src_file = {}
    for record in records:
        if not record.location:
            continue
        src_file = record.location.file
        if src_file not in by_src_file:
            by_src_file[src_file] = []
        by_src_file[src_file].append(record)

    style = pygments.styles.get_style_by_name('default')
    formatter = pygments.formatters.HtmlFormatter()

    # Write style.css
    with open(os.path.join(out_dir, "style.css"), "w") as f:
        f.write(formatter.get_style_defs())

    for src_file in by_src_file:
        log('  generating HTML for %r' % src_file)

        if 0:
            print(src_file)
            print('*' * 76)
        with open(os.path.join(build_dir, src_file)) as f:
            code = f.read()
        if 0:
            print(code)
            print('*' * 76)

        try:
            lexer = pygments.lexers.guess_lexer_for_filename(src_file, code)
        except Exception as e:
            print(f"Skipped unparsed file {src_file} because exception throw is: {e}\n")

        # Use pygments to convert it all to HTML:
        code_as_html = pygments.highlight(code, lexer, formatter)

        if 0:
            print(code_as_html)
            print('*' * 76)
            print(repr(code_as_html))
            print('*' * 76)

        EXPECTED_START = '<div class="highlight"><pre>'
        assert code_as_html.startswith(EXPECTED_START)
        code_as_html = code_as_html[len(EXPECTED_START):-1]

        EXPECTED_END = '</pre></div>'
        assert code_as_html.endswith(EXPECTED_END)
        code_as_html = code_as_html[0:-len(EXPECTED_END)]

        html_lines = code_as_html.splitlines()
        if 0:
            for html_line in html_lines:
                print(repr(html_line))
            print('*' * 76)

        # Group by line num
        by_line_num = {}
        for record in by_src_file[src_file]:
            line_num = record.location.line
            if line_num not in by_line_num:
                by_line_num[line_num] = []
            by_line_num[line_num].append(record)

        next_id = 0

        with open(os.path.join(out_dir, srcfile_to_html(src_file)), "w") as f:
            write_html_header(f, html.escape(src_file),
                              '<link rel="stylesheet" href="style.css" type="text/css" />\n')
            f.write('<h1>%s</h1>' % html.escape(src_file))
            f.write('<table class="table table-striped table-bordered table-sm">\n')
            f.write('  <tr>\n')
            f.write('    <th>Line</th>\n')
            f.write('    <th>Hotness</th>\n')
            f.write('    <th>Pass</th>\n')
            f.write('    <th>Source</th>\n')
            f.write('    <th>Function / Inlining Chain</th>\n')
            f.write('  </tr>\n')
            for line_num, html_line in enumerate(html_lines, start=1):
                # Add row for the source line itself.

                f.write('  <tr>\n')

                # Line:
                f.write('    <td id="line-%i">%i</td>\n' % (line_num, line_num))

                # Hotness:
                f.write('    <td></td>\n')

                # Pass:
                f.write('    <td></td>\n')

                # Source
                f.write('    <td><div class="highlight"><pre style="margin: 0 0;">')
                f.write(html_line)
                f.write('</pre></div></td>\n')

                # Inlining Chain:
                f.write('    <td></td>\n')

                f.write('  </tr>\n')

                # Add extra rows for any optimization records that apply to
                # this line.
                for record in by_line_num.get(line_num, []):
                    f.write('  <tr>\n')

                    # Line (blank)
                    f.write('    <td></td>\n')

                    # Hotness
                    write_td_count(f, record, highest_count)

                    # Pass:
                    write_td_pass(f, record)

                    # Text
                    column = record.location.column
                    html_for_message = get_html_for_message(record)
                    # Column number is 1-based:
                    indent = ' ' * (column - 1)
                    lines = indent + '<span style="color:green;">^</span>'
                    for line in html_for_message.splitlines():
                        lines += line + '\n' + indent
                    f.write('    <td><pre style="margin: 0 0;">')
                    num_lines = lines.count('\n')
                    collapsed =  num_lines > 7
                    if collapsed:
                        f.write('''<button class="btn btn-primary" type="button" data-toggle="collapse" data-target="#collapse-%i" aria-expanded="false" aria-controls="collapse-%i">
    Toggle messages <span class="badge badge-light">%i</span>
  </button>
                        ''' % (next_id, next_id, num_lines))
                        f.write('<div class="collapse" id="collapse-%i">' % next_id)
                        next_id += 1
                    f.write(lines)
                    if collapsed:
                        f.write('</div">')
                    f.write('</pre></td>\n')

                    # Inlining Chain:
                    write_inlining_chain(f, record)

                    f.write('  </tr>\n')

            f.write('</table>\n')
            write_html_footer(f)

            time.sleep(1.0)

            """
            Rename file
            """
            filename = os.path.basename(src_file)
            print(filename)
            print(src_file)
            currentWorkingDir = out_dir
            print(f"Filename {filename} that skipped are already in HTML and can be renamed to .html, but")
            print("some features will not work!")
            fileInWorkingDir = currentWorkingDir + "\\" + filename
            fs_path = Path(filename)
            if fs_path.suffix:
                # File has an extension
                base_name = fs_path.stem
            else:
                # File does not have an extension
                base_name = fs_path.name

            print(fileInWorkingDir)
            print(currentWorkingDir + "\\" + base_name)

            counter: int = 1
            if os.path.exists(currentWorkingDir + "\\" + base_name + ".html"):
                renamed_based_name = f"{base_name}_{counter}"
                if os.path.exists(currentWorkingDir + "\\" + base_name + "_" + str(counter) + ".html"):
                    counter += 1
                    renamed_based_name = f"{base_name}_{counter}"
                
                shutil.copy(fileInWorkingDir, currentWorkingDir + "\\" + renamed_based_name + ".html")
                print(f"Copied from {fileInWorkingDir} to {currentWorkingDir}\\{renamed_based_name}.html\n")
            else:
                shutil.copy(fileInWorkingDir, currentWorkingDir + "\\" + base_name + ".html")
                print(f"Copied from {fileInWorkingDir} to {currentWorkingDir}\\{base_name}.html\n")

def write_cfg_view(f, view_id, cfg):
    # see http://visjs.org/docs/network/
    f.write('<div id="%s"></div>' % view_id)
    f.write('<script type="text/javascript">\n')
    f.write('  var nodes = new vis.DataSet([\n')
    for block in cfg.blocks:
        if block.stmts:
            label = block.get_nondebug_stmts()
        elif block.index == 0:
            label = 'ENTRY'
        elif block.index == 1:
            label = 'EXIT'
        else:
            label = 'Block %i' % block.index
        f.write("    {id: %i, label: %r},\n"
                % (block.index, label)) # FIXME: Python vs JS escaping?
    f.write('    ]);\n')
    f.write('  var edges = new vis.DataSet([\n')
    for edge in cfg.edges:
        label = ' '. join(str(flag) for flag in edge.flags)
        f.write('    {from: %i, to: %i, label: %r},\n'
                % (edge.src.index, edge.dest.index, label))
    f.write(' ]);\n')
    f.write("  var container = document.getElementById('%s');"
            % view_id)
    f.write("""
  var data = {
    nodes: nodes,
    edges: edges
  };
  var options = {
    nodes:{
      shape: 'box',
      font: {'face': 'monospace', 'align': 'left'},
      scaling: {
        label:true
      },
      shadow: true
    },
    edges:{
      arrows: 'to',
    },
    layout:{
      hierarchical: true
    }
  };
  var network = new vis.Network(container, data, options);
</script>
""")

def have_any_precise_counts(tus):
    for tu in tus:
        for record in tu.records:
            if isinstance(record, Record):
                if record.count:
                    if record.count.is_precise():
                        return True

def filter_non_precise_counts(tus):
    precise_records = []
    num_filtered = 0
    for tu in tus:
        for record in tu.records:
            if isinstance(record, Record):
                if record.count:
                    if not record.count.is_precise():
                        num_filtered += 1
                        continue
            precise_records.append(record)
    log('  purged %i non-precise records' % num_filtered)
    return precise_records

def analyze_counts(tus):
    """
    Get the highest count, purging any non-precise counts
    if we have any precise counts.
    """
    log(' analyze_counts')

    if have_any_precise_counts(tus):
        records = filter_non_precise_counts(tus)

    highest_count = 0
    for tu in tus:
        for record in tu.records:
            if isinstance(record, Record):
                if record.count:
                    value = record.count.value
                    if value > highest_count:
                        highest_count = value

    return highest_count

def make_html(build_dir, out_dir, tus):
    log('make_html')

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    highest_count = analyze_counts(tus)
    log(' highest_count=%r' % highest_count)

    make_index_html(out_dir, tus, highest_count)
    make_per_source_file_html(build_dir, out_dir, tus, highest_count)

############################################################################

def write_record_to_outline(f, record, level):
    f.write('%s ' % ('*' * level))
    if record.location:
        f.write('%s: ' % record.location)
    for item in record.message:
        if isinstance(item, str):
            f.write(item)
        elif isinstance(item, (Expr, Stmt, SymtabNode)):
            f.write(str(item))
        else:
            raise TypeError('unknown message item: %r' % item)
    if record.pass_:
        f.write(' [' + ('pass=%s' % record.pass_.name) + ']')
    if record.count:
        f.write(' [' + ('count(%s)=%i'
                        % (record.count.quality, record.count.value))
                + ']')
    f.write('\n')
    for child in record.children:
        write_record_to_outline(f, child, level + 1)

def make_outline(build_dir, out_dir, tus):
    log('make_outline')

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    with open(os.path.join(out_dir, 'outline.txt'), 'w') as f:
        for tu in tus:
            f.write('* %s\n' % tu.filename)
            # FIXME: metadata?
            for record in tu.iter_all_records():
                write_record_to_outline(f, record, 2)
            # FIXME: show passes?

############################################################################

SGR_START = "\33["
SGR_END   = "m\33[K"

def SGR_SEQ(str):
    return SGR_START + str + SGR_END

SGR_RESET = SGR_SEQ("")

COLOR_SEPARATOR  = ";"
COLOR_BOLD       = "01"
COLOR_FG_GREEN   = "32"
COLOR_FG_CYAN    = "36"

def with_color(color, text):
    if os.isatty(sys.stdout.fileno()):
        return SGR_SEQ(color) + text + SGR_RESET
    else:
        return text

def remark(text):
    return with_color(COLOR_FG_GREEN + COLOR_SEPARATOR  + COLOR_BOLD, text)

def note(text):
    return with_color(COLOR_BOLD + COLOR_SEPARATOR + COLOR_FG_CYAN, text)

def bold(text):
    return with_color(COLOR_BOLD, text)

def print_as_remark(record):
    msg = ''
    loc = record.location
    if loc:
        msg += bold('%s: ' % loc)
        msg += remark('remark: ')
    for item in record.message:
        if isinstance(item, str):
            msg += item
        elif isinstance(item, (Expr, Stmt, SymtabNode)):
            msg += "'" + bold(str(item)) + "'"
        else:
            raise TypeError('unknown message item: %r' % item)
    if record.pass_:
        msg += ' [' + remark('pass=%s' % record.pass_.name) + ']'
    if record.count:
        msg += (' ['
                + note('count(%s)=%i'
                       % (record.count.quality, record.count.value))
                + ']')
    print(msg)

############################################################################

def filter_records(tus):
    def criteria(record):
        # Hack to filter things a bit:
        if record.location:
            src_file = record.location.file
            if 'pgen.c' in src_file:
                return False
        if record.pass_:
            if record.pass_.name in ('slp', 'fre', 'pre', 'profile',
                                     'cunroll', 'cunrolli', 'ivcanon'):
                return False
        return True
    for tu in tus:
        tu.records = list(filter(criteria, tu.records))

def summarize_records(tus):
    log('records by pass:')
    num_records_by_pass = Counter()
    for tu in tus:
        for record in tu.iter_all_records():
            #print(record)
            if record.pass_:
                num_records_by_pass[record.pass_.name] += 1
    for pass_,count in num_records_by_pass.most_common():
        log(' %s: %i' % (pass_, count))

def generate_static_report(build_dir, out_dir):
    tus = find_records(build_dir)

    summarize_records(tus)

    filter_records(tus)

    summarize_records(tus)
    if 0:
        for tu in tus:
            for record in tu.records:
                print_as_remark(record)
    if 0:
        for tu in tus:
            for record in tu.records:
                print(record)
    make_html(build_dir, out_dir, tus)
    make_outline(build_dir, out_dir, tus)
