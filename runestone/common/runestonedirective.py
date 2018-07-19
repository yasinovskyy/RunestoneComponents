# Copyright (C) 2016  Bradley N. Miller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
__author__ = 'bmiller'


import os
from collections import defaultdict
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from docutils.utils import get_source_line

# Provide a class which all Runestone nodes will inherit from.
class RunestoneNode(nodes.Node):
    pass


# Notes
# env = self.state.document.settings.env
# env.config.html_context['course_id']
#if not hasattr(env, 'activecodecounter'):
#    env.activecodecounter = 0
#env.activecodecounter += 1
# similar trick for assessments using getNumber()

# Easily create and initialize an object with named methods from the object's constructor. Taken from http://stackoverflow.com/a/3652937. While a collections.namedtuple could probably be forced to do this, the following approach seems fairly straightforward.
class Struct:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    # Provide a nice printable representation.
    def __repr__(self):
        args = ['{}={}'.format(k, repr(v)) for (k,v) in vars(self).items()]
        return 'Struct({})'.format(', '.join(args))

# Get a data structure which holds Runestone data from the environment. Create one if it doesn't exist.
def _get_runestone_data(
    # The Sphinx environment which (possibly) contains Runestone data.
    env):

    # Create the Runestone data structure if it doesn't yet exist.
    if not hasattr(env, 'runestone_data'):
        # .. _Runestone data:
        env.runestone_data = Struct(
            # Maps from a question's ID to the page containing it:
            #
            # .. code:: Python
            #   :number-lines:
            #
            #   .id_to_page = {
            #       # The ID maps to a Struct(), which contains:
            #       str(id): Struct()
            #           # The path of the file which contains this ID.
            #           .srcpath = str()
            #           # The line in this file which contains this ID.
            #           .line = int()
            #   }
            id_to_page=dict(),
            # Provide the inverse map: from a page to a set of IDs it contains.
            #
            # .. code:: Python
            #   :number-lines:
            #
            #   .page_to_id: = {
            #       # The path to a source file maps to a set:
            #       str(srcpath) : set(
            #           # Which consists of a strings, each of which is an ID on that page.
            #           str(id_), ...
            #       )
            #   }
            page_to_id=defaultdict(set),
        )
    return env.runestone_data

# When a source file is modified, clear all accumulated Runestone data from it.
def _purge_runestone_data(app, env, docname):
    runestone_data = _get_runestone_data(env)

    for id_ in runestone_data.page_to_id[docname]:
        runestone_data.id_to_page.pop(id_)
    runestone_data.page_to_id.pop(docname)

def setup(app):
    # See http://www.sphinx-doc.org/en/stable/extdev/appapi.html#event-env-purge-doc.
    app.connect('env-purge-doc', _purge_runestone_data)


# A base class for all Runestone directives.
class RunestoneDirective(Directive):
    option_spec = {'author': directives.unchanged,
                   'tags': directives.unchanged,
                   'difficulty': directives.positive_int,
                   'autograde': directives.unchanged,
                   'practice': directives.unchanged,
                   'topics': directives.unchanged,
                   }

    def __init__(self, *args, **kwargs):
        super(RunestoneDirective, self).__init__(*args, **kwargs)
        env = self.state.document.settings.env
        self.srcpath = env.docname
        # Rather tha use ``os.sep`` to split ``self.srcpath``, use ``'/'``, because Sphinx internally stores filesnames using this separator, even on Windows.
        split_docname = self.srcpath.split('/')
        if len(split_docname) < 2:
            # TODO: Warn about this? Something like ``self.state.document.settings.env``?
            split_docname.append('')
        self.subchapter = split_docname[-1]
        self.chapter = split_docname[-2]
        self.basecourse = self.state.document.settings.env.config.html_context.get('basecourse', "unknown")
        self.options['basecourse'] = self.basecourse
        self.options['chapter'] = self.chapter
        self.options['subchapter'] = self.subchapter


# This is a base class for all Runestone directives which require a divid as their first parameter.
class RunestoneIdDirective(RunestoneDirective):
    def run(self):
        # Make sure the runestone directive at least requires an ID.
        assert self.required_arguments >= 1
        if 'divid' not in self.options:
            id_ = self.options['divid'] = self.arguments[0]
        else:
            id_ = self.options['divid']

        # Get references to `runestone data`_.
        env = self.state.document.settings.env
        runestone_data = _get_runestone_data(env)
        id_to_page = runestone_data.id_to_page
        page_to_id = runestone_data.page_to_id
        # See if this ID already exists.
        if id_ in id_to_page:
            page = id_to_page[id_]
            # If it's not simply an update to an existing ID, complain.
            if page.docname != env.docname or page.lineno != self.lineno:
                raise self.error('Duplicate ID -- see {}, line {}'.format(page.docname, page.lineno))
            # Make sure our data structure is consistent.
            assert id_ in page_to_id[page.docname]
        else:
            # Add a new entry.
            id_to_page[id_] = Struct(docname=env.docname, lineno=self.lineno)
            page_to_id[env.docname].add(id_)

# returns True when called first time with particular parameters' values
def first_time(app, *keys):
    key = '$'.join(keys)
    if not hasattr(app,'runestone_flags'):
        app.runestone_flags = set()
    if not key in app.runestone_flags:
        app.runestone_flags.add(key)
        return True
    return False

# An internationalized component should call add_i18n_javascript() from its setup() function
def add_i18n_js(app, supported_langs, *i18n_resources):
    if first_time(app, 'add_i18n_js'):
        app.add_javascript('jquery_i18n/CLDRPluralRuleParser.js')
        app.add_javascript('jquery_i18n/jquery.i18n.js')
        app.add_javascript('jquery_i18n/jquery.i18n.messagestore.js')
        app.add_javascript('jquery_i18n/jquery.i18n.fallbacks.js')
        app.add_javascript('jquery_i18n/jquery.i18n.language.js')
        app.add_javascript('jquery_i18n/jquery.i18n.parser.js')
        app.add_javascript('jquery_i18n/jquery.i18n.emitter.js')
        app.add_javascript('jquery_i18n/jquery.i18n.emitter.bidi.js')
    for res in i18n_resources:
        if(first_time(app,'add_i18n_js',res)):
            app.add_javascript(res + ".en.js")
            if app.config.language and app.config.language != "en" and app.config.language in supported_langs:
                app.add_javascript(res + "." + app.config.language + ".js")

# Adds CSS and JavaScript for the CodeMirror text editor
def add_codemirror_css_and_js(app, *mods):
    if first_time(app, 'add_codemirror_css_and_js'):
        app.add_stylesheet('codemirror.css')
        app.add_javascript('codemirror.js')
    for mod in mods:
        if first_time(app, 'add_codemirror_css_and_js',mod):
            app.add_javascript(mod + '.js')

# Adds JavaScript for the Sculpt in-browser implementation of Python
def add_skulpt_js(app):
    if first_time(app, 'add_skulpt_js'):
        app.add_javascript('skulpt.min.js')
        app.add_javascript('skulpt-stdlib.js')
        app.add_javascript("https://cdn.jsdelivr.net/npm/vega@4.0.0-rc.2/build/vega.js")
        app.add_javascript("https://cdn.jsdelivr.net/npm/vega-lite@2.5.0/build/vega-lite.js")
        app.add_javascript("https://cdn.jsdelivr.net/npm/vega-embed@3.14.0/build/vega-embed.js")


# Some nodes have a line number of None. Look through their children to find the node's line number.
def get_node_line(node):
    # This returns source, line. Pick just the line.
    return get_source_line(node)[1]
