#!/usr/bin/env python
import os.path
import subprocess
import tempfile

import jinja2
from jinja2.ext import Extension
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers.web import JavascriptLexer


class CodeExampleExtension(Extension):
    """Insert a code example.

    My plan for the docs is side-by-side code and live widgets. I plan to make
    this extension fancier in the future, since I would like one file to serve
    as the source of both the pretty code we display to the user and the
    widget. I have a vague idea of how that will work - I think there will have
    to be a header/footer that will be inserted for any given example, then
    this command will strip that out, put it where it needs to go, and format
    the code nicely.

    http://jinja.pocoo.org/docs/extensions/#adding-extensions
    """

    tags = set(["code_example"])

    def __init__(self, environment):
        super(CodeExampleExtension, self).__init__(environment)

    # {% code_example "filename" %}
    #    ^------------------ first token, call next() to advance past it
    #                 ^----- generate self._insert("filename")
    def parse(self, parser):
        lineno = parser.stream.next().lineno
        filename = parser.parse_expression()
        return (jinja2.nodes
            .CallBlock(self.call_method('_insert', [filename]), [], [], [])
            .set_lineno(lineno))


    def _insert(self, filename, caller):
        formatter = HtmlFormatter() # linenos='table')
        lexer = JavascriptLexer()
        path = os.path.join('examples', filename)

        # prelude - this code sets up the sample, includes react, etc
        PRELUDE = '// PRELUDE\n'
        # the meat of the sample - we show this to the reader
        POSTSCRIPT = '// POSTSCRIPT\n'
        # postscript - React.renderComponent, etc

        # find the meat
        with open(path, 'r') as f:
            lines = [line for line in f]
            start = lines.index(PRELUDE)
            end = lines.index(POSTSCRIPT)
            fragment = ''.join(lines[start+1 : end])

        self.environment.scripts.append(''.join(lines))

        return highlight(fragment, lexer, formatter)


if __name__ == '__main__':
    loader = jinja2.FileSystemLoader('.')
    env = jinja2.Environment(loader=loader, extensions=[CodeExampleExtension])
    # *tiny* hack here - we're going to need this header at the top of our
    # final concatenated script
    env.scripts = ["/** @jsx React.DOM */"]
    template = env.get_template('template.html')

    with open('index.html', 'w') as f:
        f.seek(0)
        f.write(template.render())

    with tempfile.NamedTemporaryFile(dir='.') as f:
        f.write('\n'.join(env.scripts))
        f.seek(0)

        command = [
            # bundle the concatenation of all our samples
            "./node_modules/.bin/browserify", f.name,

            # with the react transform
            "-t", "[", "reactify", "--es6", "]", "-d",

            "-o", "./docs-output/bundle.js"
        ]
        print subprocess.check_output(command, stderr=subprocess.STDOUT)
